from __future__ import annotations

import json
import os
import sys

import asyncio
import logging
import time

import core.events as core_events

from pipeline.console_diagnostics import force_console_log
from pipeline.events import DiagramOutcomeEvent
from pipeline.prompts.diagram import (
    build_compare_image_prompts,
    build_hook_image_prompt,
    build_image_generation_prompt,
    build_series_step_image_prompt,
)
from pipeline.providers.gemini_image_client import (
    get_gemini_image_client,
    resolve_gemini_image_api_key,
)
from pipeline.events import ImageOutcomeEvent
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.storage.image_store import get_image_store
from pipeline.types.section_content import (
    DiagramContent,
    DiagramCompareContent,
    DiagramSeriesContent,
    DiagramSeriesStep,
    HookImage,
)
from pipeline.visual_resolution import (
    pending_visual_targets,
    resolve_effective_visual_mode,
    resolve_effective_visual_targets,
    target_is_satisfied,
)

logger = logging.getLogger(__name__)

_IMAGE_TIMEOUT_SECONDS = 45.0
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF = (1.0, 2.0)


def diag(tag: str, **fields) -> None:
    sys.stderr.write(f"DIAG::{tag}::{json.dumps(fields, default=str)}\n")
    sys.stderr.flush()


diag("BUILD_MARKER", file="image_generator", version="diag_v1")


def _imggen_diag(event: str, **fields) -> None:
    force_console_log("IMGGEN_AI", event, **fields)


def _publish_image_outcome(
    generation_id: str,
    section_id: str | None,
    outcome: str,
    *,
    attempts: int = 1,
    error_message: str | None = None,
    duration_ms: float | None = None,
) -> None:
    if not generation_id or not section_id:
        return
    core_events.event_bus.publish(
        generation_id,
        ImageOutcomeEvent(
            generation_id=generation_id,
            section_id=section_id,
            outcome=outcome,
            attempts=attempts,
            error_message=error_message,
            duration_ms=duration_ms,
        ),
    )


def _log_image_event(level: int, event: str, **payload) -> None:
    logger.log(
        level,
        "IMG::%s::%s",
        event,
        json.dumps(payload, sort_keys=True, default=str),
    )


def _publish_diagram_outcome(
    generation_id: str,
    section_id: str | None,
    outcome: str,
) -> None:
    if not generation_id or not section_id:
        return
    publish_runtime_event(
        generation_id,
        DiagramOutcomeEvent(
            generation_id=generation_id,
            section_id=section_id,
            outcome=outcome,
        ),
    )


def _with_outcome(state: TextbookPipelineState, section_id: str | None, outcome: str) -> dict:
    if section_id is None:
        return {}

    outcomes = dict(state.diagram_outcomes)
    outcomes[section_id] = outcome
    _publish_diagram_outcome(state.request.generation_id or "", section_id, outcome)
    return {"diagram_outcomes": outcomes}


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        keyword in msg
        for keyword in ("timeout", "connection", "unavailable", "rate", "503", "502", "500")
    )


async def _generate_with_retry(client, prompt: str, timeout: float) -> tuple[bytes, int]:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            _imggen_diag(
                "ATTEMPT",
                attempt=attempt,
                max_attempts=_MAX_ATTEMPTS,
                prompt_length=len(prompt),
                timeout_seconds=timeout,
            )
            result = await asyncio.wait_for(
                client.generate_image(prompt=prompt, size="1024x1024", format="png"),
                timeout=timeout,
            )
            return result.bytes, attempt
        except Exception as exc:
            is_timeout = isinstance(exc, asyncio.TimeoutError)
            retryable = is_timeout or _is_retryable(exc)
            if not retryable or attempt == _MAX_ATTEMPTS:
                setattr(exc, "image_attempts", attempt)
                raise

            backoff = _RETRY_BACKOFF[attempt - 1]
            logger.warning(
                "image_generator: attempt %d/%d failed (%s), retrying in %.1fs",
                attempt,
                _MAX_ATTEMPTS,
                "timeout" if is_timeout else exc,
                backoff,
            )
            _imggen_diag(
                "RETRY",
                attempt=attempt,
                max_attempts=_MAX_ATTEMPTS,
                retryable=retryable,
                is_timeout=is_timeout,
                backoff_seconds=backoff,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            await asyncio.sleep(backoff)
    raise RuntimeError("image generation retry loop exited unexpectedly")


async def _request_image_bytes(
    *,
    client,
    prompt: str,
    section_id: str,
    variant: str,
    api_key_present: bool,
    prompt_details: dict | None = None,
) -> tuple[bytes, int]:
    payload = {
        "section_id": section_id,
        "variant": variant,
        "client_class": type(client).__name__,
        "api_key_present": api_key_present,
        "prompt_chars": len(prompt),
    }
    if prompt_details:
        payload.update(prompt_details)

    _log_image_event(logging.INFO, "API_REQUEST", **payload)
    try:
        image_bytes, attempts = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
    except Exception as exc:
        _log_image_event(
            logging.ERROR,
            "API_FAILURE",
            section_id=section_id,
            variant=variant,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )
        raise

    _log_image_event(
        logging.INFO,
        "API_SUCCESS",
        section_id=section_id,
        variant=variant,
        bytes=len(image_bytes),
        attempts=attempts,
    )
    return image_bytes, attempts


def _visual_intent(state: TextbookPipelineState) -> str:
    plan = state.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    return getattr(visual_policy, "intent", None) or "explain_structure"


def _image_targets(state: TextbookPipelineState) -> list[str]:
    return [
        target
        for target in resolve_effective_visual_targets(state)
        if target in {"diagram", "diagram_series", "diagram_compare"}
    ]


def _visual_required(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    if plan is None:
        return False

    visual_policy = getattr(plan, "visual_policy", None)
    return bool(
        any(
            component in {"diagram-block", "diagram-series", "diagram-compare"}
            for component in getattr(state.contract, "required_components", []) or []
        )
        or
        getattr(plan, "diagram_policy", None) == "required"
        or getattr(plan, "needs_diagram", False)
        or (
            visual_policy is not None and getattr(visual_policy, "required", False)
        )
    )


def _store_status_payload(store, *, probe_ok: bool, probe_detail: str) -> dict:
    return {
        "store_type": type(store).__name__,
        "store_target": store.describe_target(),
        "probe_ok": probe_ok,
        "probe_detail": probe_detail,
        "bucket_configured": bool(getattr(store, "bucket_name", None)),
        "service_account_json_present": bool(
            os.getenv("GCS_SERVICE_ACCOUNT_JSON", "").strip()
        ),
    }


async def _store_image_with_logging(
    store,
    *,
    image_bytes: bytes,
    generation_id: str,
    section_id: str,
    filename: str,
    format: str,
    variant: str,
) -> str:
    try:
        image_url = await store.store_image(
            image_bytes,
            generation_id=generation_id,
            section_id=section_id,
            filename=filename,
            format=format,
        )
    except Exception as exc:
        _log_image_event(
            logging.ERROR,
            "STORE_WRITE_FAILURE",
            section_id=section_id,
            variant=variant,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )
        raise RuntimeError(
            f"Image storage failed for {variant}: {type(exc).__name__}: {exc}"
        ) from exc

    _log_image_event(
        logging.INFO,
        "STORE_SUCCESS",
        section_id=section_id,
        variant=variant,
        asset_url_present=bool(image_url),
    )
    return image_url


async def _generate_single_image(
    *,
    state: TextbookPipelineState,
    section,
    composition_plan,
    sid: str,
    store,
    client,
    generation_id: str,
    api_key_present: bool,
):
    prompt = build_image_generation_prompt(
        section=section,
        diagram_plan=composition_plan.diagram,
        style_context=state.style_context,
    )
    image_bytes, attempts = await _request_image_bytes(
        client=client,
        prompt=prompt,
        section_id=sid,
        variant="single",
        api_key_present=api_key_present,
    )
    image_url = await _store_image_with_logging(
        store,
        image_bytes=image_bytes,
        generation_id=generation_id,
        section_id=sid,
        filename="diagram.png",
        format="png",
        variant="single",
    )

    existing = section.diagram or DiagramContent(
        caption=f"Visual illustration for {section.header.title}",
        alt_text=(
            f"Educational image illustrating {section.header.title}. "
            f"{composition_plan.diagram.visual_guidance or ''}"
        ),
    )
    return section.model_copy(
        update={"diagram": existing.model_copy(update={"image_url": image_url})}
    ), attempts


def _series_seed_steps(section, composition_plan) -> list[DiagramSeriesStep]:
    existing_series = section.diagram_series
    if existing_series is not None and existing_series.diagrams:
        return [
            step if isinstance(step, DiagramSeriesStep) else DiagramSeriesStep.model_validate(step)
            for step in existing_series.diagrams
        ]

    labels = composition_plan.diagram.key_concepts[:] or [section.header.title]
    step_count = max(len(labels), 3)
    steps: list[DiagramSeriesStep] = []
    for index in range(step_count):
        label = labels[index] if index < len(labels) else f"Stage {index + 1}"
        steps.append(
            DiagramSeriesStep(
                step_label=label,
                caption=f"{section.header.title} - {label}",
            )
        )
    return steps


async def _generate_series_images(
    *,
    state: TextbookPipelineState,
    section,
    composition_plan,
    sid: str,
    store,
    client,
    generation_id: str,
    api_key_present: bool,
):
    seed_steps = _series_seed_steps(section, composition_plan)
    key_concepts = composition_plan.diagram.key_concepts or []
    rendered_steps: list[DiagramSeriesStep] = []
    failures: list[str] = []
    max_attempts = 1

    for index, step in enumerate(seed_steps):
        key_concept = key_concepts[index] if index < len(key_concepts) else step.step_label
        prompt = build_series_step_image_prompt(
            section_title=section.header.title,
            step_label=step.step_label,
            step_index=index,
            total_steps=len(seed_steps),
            key_concept=key_concept,
            style_context=state.style_context,
        )

        try:
            image_bytes, attempts = await _request_image_bytes(
                client=client,
                prompt=prompt,
                section_id=sid,
                variant=f"series-step-{index + 1}",
                api_key_present=api_key_present,
                prompt_details={
                    "step_index": index + 1,
                    "step_total": len(seed_steps),
                },
            )
            max_attempts = max(max_attempts, attempts)
            image_url = await _store_image_with_logging(
                store,
                image_bytes=image_bytes,
                generation_id=generation_id,
                section_id=sid,
                filename=f"series-step-{index + 1}.png",
                format="png",
                variant=f"series-step-{index + 1}",
            )
            rendered_steps.append(step.model_copy(update={"image_url": image_url}))
        except Exception as exc:
            failures.append(str(exc))
            _log_image_event(
                logging.WARNING,
                "SERIES_STEP_FAILURE",
                section_id=sid,
                variant=f"series-step-{index + 1}",
                step_index=index + 1,
                step_total=len(seed_steps),
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )
            rendered_steps.append(step.model_copy(update={"image_url": None}))

    if not any(step.image_url for step in rendered_steps):
        raise RuntimeError(f"All {len(seed_steps)} DiagramSeries images failed: {failures[:2]}")

    title = section.diagram_series.title if section.diagram_series else section.header.title
    return section.model_copy(
        update={"diagram_series": DiagramSeriesContent(title=title, diagrams=rendered_steps)}
    ), max_attempts


async def _maybe_generate_hook_image(
    *,
    state: TextbookPipelineState,
    section,
    sid: str,
    store,
    client,
    generation_id: str,
    api_key_present: bool,
):
    plan = state.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    section_role = getattr(plan, "role", None) if plan is not None else None

    if (
        visual_policy is None
        or getattr(visual_policy, "intent", None) != "show_realism"
        or section_role not in {"intro", "visual", "discover"}
        or section.hook.image is not None
    ):
        return section

    prompt = build_hook_image_prompt(
        section_title=section.header.title,
        hook_headline=section.hook.headline,
        hook_body=section.hook.body,
        style_context=state.style_context,
    )

    try:
        image_bytes, _attempts = await _request_image_bytes(
            client=client,
            prompt=prompt,
            section_id=sid,
            variant="hook",
            api_key_present=api_key_present,
        )
        image_url = await _store_image_with_logging(
            store,
            image_bytes=image_bytes,
            generation_id=generation_id,
            section_id=sid,
            filename="hook.png",
            format="png",
            variant="hook",
        )
        return section.model_copy(
            update={
                "hook": section.hook.model_copy(
                    update={
                        "image": HookImage(
                            url=image_url,
                            alt=f"Visual anchor for {section.header.title}",
                        )
                    }
                )
            }
        )
    except Exception as exc:
        _log_image_event(
            logging.WARNING,
            "HOOK_FAILURE",
            section_id=sid,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )
        return section


def _seed_compare_content(section, composition_plan) -> DiagramCompareContent:
    if section.diagram_compare is not None:
        return section.diagram_compare
    before_label = composition_plan.diagram.compare_before_label or "Before"
    after_label = composition_plan.diagram.compare_after_label or "After"
    return DiagramCompareContent(
        before_label=before_label,
        after_label=after_label,
        caption=f"Before and after comparison for {section.header.title}",
        alt_text=f"Before and after comparison illustrating changes in {section.header.title}.",
    )


async def _generate_compare_images(
    *,
    state: TextbookPipelineState,
    section,
    composition_plan,
    sid: str,
    store,
    client,
    generation_id: str,
    api_key_present: bool,
):
    compare_content = _seed_compare_content(section, composition_plan)
    prompt_before_label = (
        composition_plan.diagram.compare_before_label or compare_content.before_label or "Before"
    )
    prompt_after_label = (
        composition_plan.diagram.compare_after_label or compare_content.after_label or "After"
    )
    before_prompt, after_prompt = build_compare_image_prompts(
        section=section,
        diagram_plan=composition_plan.diagram,
        style_context=state.style_context,
        before_label=prompt_before_label,
        after_label=prompt_after_label,
    )

    try:
        (before_bytes, before_attempts), (after_bytes, after_attempts) = await asyncio.gather(
            _request_image_bytes(
                client=client,
                prompt=before_prompt,
                section_id=sid,
                variant="compare-before",
                api_key_present=api_key_present,
            ),
            _request_image_bytes(
                client=client,
                prompt=after_prompt,
                section_id=sid,
                variant="compare-after",
                api_key_present=api_key_present,
            ),
        )
        before_url, after_url = await asyncio.gather(
            _store_image_with_logging(
                store,
                image_bytes=before_bytes,
                generation_id=generation_id,
                section_id=sid,
                filename="compare-before.png",
                format="png",
                variant="compare-before",
            ),
            _store_image_with_logging(
                store,
                image_bytes=after_bytes,
                generation_id=generation_id,
                section_id=sid,
                filename="compare-after.png",
                format="png",
                variant="compare-after",
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"DiagramCompare pair failed: {exc}") from exc

    return section.model_copy(
        update={
            "diagram_compare": compare_content.model_copy(
                update={
                    "before_image_url": before_url,
                    "after_image_url": after_url,
                }
            )
        }
    ), max(before_attempts, after_attempts)


async def image_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    _store=None,
    _client=None,
) -> dict:
    _ = model_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)
    generation_id = state.request.generation_id or ""
    started = time.monotonic()
    visual_mode = resolve_effective_visual_mode(state)
    visual_targets = resolve_effective_visual_targets(state)
    image_targets = _image_targets(state)
    pending_before = pending_visual_targets(state)

    composition_plan = (state.composition_plans or {}).get(sid)
    _log_image_event(
        logging.INFO,
        "START",
        section_id=sid,
        generation_id=generation_id or "unknown",
        mode=visual_mode,
        targets=visual_targets,
        image_targets=image_targets,
        pending_before=pending_before,
        required=_visual_required(state),
        plan_exists=composition_plan is not None,
        enabled=(composition_plan.diagram.enabled if composition_plan is not None else None),
    )
    _imggen_diag(
        "START",
        section_id=sid,
        generation_id=generation_id or "unknown",
        mode=visual_mode,
        targets=visual_targets,
        image_targets=image_targets,
        pending_before=pending_before,
    )

    if not image_targets:
        _log_image_event(
            logging.INFO,
            "SKIP_NO_IMAGE_TARGETS",
            section_id=sid,
            targets=visual_targets,
        )
        _imggen_diag(
            "SKIP",
            section_id=sid,
            reason="no_image_targets",
            targets=visual_targets,
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "skipped",
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {"completed_nodes": ["image_generator"]}

    if visual_mode != "image":
        _log_image_event(
            logging.INFO,
            "SKIP_MODE",
            section_id=sid,
            mode=visual_mode,
        )
        _imggen_diag(
            "SKIP",
            section_id=sid,
            reason="mode_not_image",
            mode=visual_mode,
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "skipped",
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {"completed_nodes": ["image_generator"]}

    if section is None:
        error_message = f"No section content found for {sid}"
        _log_image_event(
            logging.ERROR,
            "SECTION_FAILURE",
            section_id=sid,
            available_sections=list(state.generated_sections.keys()),
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="no_section_content",
            available_sections=list(state.generated_sections.keys()),
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=error_message,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=error_message,
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    if composition_plan is None:
        error_message = (
            "Image generation cannot run because no composition plan exists for this section."
        )
        _log_image_event(
            logging.ERROR,
            "PLAN_FAILURE",
            section_id=sid,
            targets=image_targets,
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="no_composition_plan",
            targets=image_targets,
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=error_message,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=error_message,
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    if not composition_plan.diagram.enabled:
        _log_image_event(
            logging.INFO,
            "SKIP_NOT_ENABLED",
            section_id=sid,
            enabled=False,
            mode=visual_mode,
            required=_visual_required(state),
        )
        error_message = (
            "Image generation was required for this section, but the composition plan "
            "did not enable diagram generation."
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="diagram_not_enabled",
            targets=image_targets,
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=error_message,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=error_message,
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    if state.style_context is None:
        error_message = "style_context is None -- curriculum_planner may have failed"
        _log_image_event(
            logging.ERROR,
            "STYLE_CONTEXT_FAILURE",
            section_id=sid,
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="no_style_context",
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=error_message,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=error_message,
                    recoverable=False,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }
    try:
        store = _store or get_image_store()
    except Exception as exc:
        _log_image_event(
            logging.ERROR,
            "STORE_INIT_FAILURE",
            section_id=sid,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="store_init_failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=f"Image store init failed: {type(exc).__name__}: {exc}",
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=f"Image store init failed: {type(exc).__name__}: {exc}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    try:
        probe_ok, probe_detail = await store.probe_write_access()
    except Exception as exc:
        probe_ok = False
        probe_detail = f"{type(exc).__name__}: {exc}"

    _log_image_event(
        logging.INFO,
        "STORE_STATUS",
        section_id=sid,
        source="injected" if _store is not None else "default",
        **_store_status_payload(store, probe_ok=probe_ok, probe_detail=probe_detail),
    )
    _imggen_diag(
        "STORE",
        section_id=sid,
        store_type=type(store).__name__,
        store_source="injected" if _store is not None else "default",
        store_target=store.describe_target(),
        probe_ok=probe_ok,
    )

    api_key = resolve_gemini_image_api_key()
    api_key_present = bool(api_key)
    _log_image_event(
        logging.INFO,
        "API_KEY_STATUS",
        section_id=sid,
        api_key_present=api_key_present,
        checked_vars=[
            "GOOGLE_CLOUD_NANO_API_KEY",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
        ],
    )
    if _client is None and not api_key:
        _log_image_event(
            logging.ERROR,
            "API_KEY_FAILURE",
            section_id=sid,
            reason="missing_api_key",
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="no_api_key",
            provider="gemini",
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=(
                "No Gemini API key found for image generation. "
                "Set GOOGLE_CLOUD_NANO_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY."
            ),
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=(
                        "No Gemini API key found for image generation. "
                        "Set GOOGLE_CLOUD_NANO_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY."
                    ),
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    try:
        client = _client or get_gemini_image_client()
        _log_image_event(
            logging.INFO,
            "CLIENT_STATUS",
            section_id=sid,
            client_class=type(client).__name__,
            source="injected" if _client is not None else "default",
            api_key_present=api_key_present,
        )
        _imggen_diag(
            "PROVIDER",
            section_id=sid,
            provider="gemini",
            client_type=type(client).__name__,
            client_source="injected" if _client is not None else "default",
            target_mode=visual_mode,
            targets=image_targets,
        )
    except Exception as exc:
        _log_image_event(
            logging.ERROR,
            "CLIENT_INIT_FAILURE",
            section_id=sid,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="client_init_failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            error_message=f"Gemini image client init failed: {type(exc).__name__}: {exc}",
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=f"Gemini image client init failed: {type(exc).__name__}: {exc}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    try:
        updated_section = section
        attempts = 1
        for target in image_targets:
            if target_is_satisfied(updated_section, target, mode="image"):
                _imggen_diag(
                    "SKIP",
                    section_id=sid,
                    reason="target_already_satisfied",
                    target=target,
                )
                continue

            _imggen_diag(
                "WRITEBACK",
                section_id=sid,
                target=target,
                status="starting",
            )
            if target == "diagram_series":
                updated_section, target_attempts = await _generate_series_images(
                    state=state,
                    section=updated_section,
                    composition_plan=composition_plan,
                    sid=sid,
                    store=store,
                    client=client,
                    generation_id=generation_id,
                    api_key_present=api_key_present,
                )
            elif target == "diagram_compare":
                updated_section, target_attempts = await _generate_compare_images(
                    state=state,
                    section=updated_section,
                    composition_plan=composition_plan,
                    sid=sid,
                    store=store,
                    client=client,
                    generation_id=generation_id,
                    api_key_present=api_key_present,
                )
            else:
                updated_section, target_attempts = await _generate_single_image(
                    state=state,
                    section=updated_section,
                    composition_plan=composition_plan,
                    sid=sid,
                    store=store,
                    client=client,
                    generation_id=generation_id,
                    api_key_present=api_key_present,
                )
            attempts = max(attempts, target_attempts)
            _imggen_diag(
                "WRITEBACK",
                section_id=sid,
                target=target,
                status="completed",
                target_satisfied=target_is_satisfied(updated_section, target, mode="image"),
            )

        if _visual_intent(state) == "show_realism":
            updated_section = await _maybe_generate_hook_image(
                state=state,
                section=updated_section,
                sid=sid,
                store=store,
                client=client,
                generation_id=generation_id,
                api_key_present=api_key_present,
            )

        pending_after = [
            target
            for target in image_targets
            if not target_is_satisfied(updated_section, target, mode="image")
        ]
        generated = dict(state.generated_sections)
        generated[sid] = updated_section
        if pending_after:
            error_message = (
                "Image generation wrote visual content, but the section still has unresolved "
                f"required targets: {', '.join(pending_after)}"
            )
            _log_image_event(
                logging.ERROR,
                "WRITEBACK_PENDING_MISMATCH",
                section_id=sid,
                targets=image_targets,
                pending_before=pending_before,
                pending_after=pending_after,
            )
            _imggen_diag(
                "WRITEBACK_PENDING_MISMATCH",
                section_id=sid,
                targets=image_targets,
                pending_before=pending_before,
                pending_after=pending_after,
            )
            _publish_image_outcome(
                generation_id,
                sid,
                "error",
                attempts=attempts,
                error_message=error_message,
                duration_ms=(time.monotonic() - started) * 1000.0,
            )
            return {
                "generated_sections": generated,
                "errors": [
                    PipelineError(
                        node="image_generator",
                        section_id=sid,
                        message=error_message,
                        recoverable=True,
                    )
                ],
                "completed_nodes": ["image_generator"],
                **_with_outcome(state, sid, "error"),
            }

        _log_image_event(
            logging.INFO,
            "SUCCESS",
            section_id=sid,
            targets=image_targets,
            pending_before=pending_before,
            pending_after=pending_after,
            attempts=attempts,
            asset_url_present=True,
        )
        _imggen_diag(
            "SUCCESS",
            section_id=sid,
            targets=image_targets,
            pending_before=pending_before,
            pending_after=pending_after,
            attempts=attempts,
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "success",
            attempts=attempts,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "generated_sections": generated,
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "success"),
        }
    except asyncio.TimeoutError as exc:
        attempts = getattr(exc, "image_attempts", _MAX_ATTEMPTS)
        _log_image_event(
            logging.ERROR,
            "TIMEOUT",
            section_id=sid,
            attempts=attempts,
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="timeout",
            attempts=attempts,
            error_type=type(exc).__name__,
            error_message="Image generation timed out",
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "timeout",
            attempts=attempts,
            error_message="Image generation timed out",
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=(
                        f"Image generation timed out after {attempts} attempts "
                        "while calling Gemini."
                    ),
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "timeout"),
        }
    except Exception as exc:
        attempts = getattr(exc, "image_attempts", 1)
        message = str(exc)
        if not message.startswith(("Image storage failed", "DiagramCompare pair failed")):
            message = f"Image generation failed: {type(exc).__name__}: {exc}"
        _log_image_event(
            logging.ERROR,
            "FAILURE",
            section_id=sid,
            attempts=attempts,
            error_type=type(exc).__name__,
            error_message=message[:500],
        )
        _imggen_diag(
            "FAIL",
            section_id=sid,
            reason="unexpected",
            attempts=attempts,
            error_type=type(exc).__name__,
            error_message=message,
        )
        _publish_image_outcome(
            generation_id,
            sid,
            "error",
            attempts=attempts,
            error_message=message,
            duration_ms=(time.monotonic() - started) * 1000.0,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=message,
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }
