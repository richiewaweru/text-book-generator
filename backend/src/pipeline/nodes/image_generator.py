from __future__ import annotations

import asyncio
import json
import logging
import os

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
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.storage.image_store import get_image_store
from pipeline.types.section_content import (
    DiagramCompareContent,
    DiagramContent,
    DiagramSeriesContent,
    DiagramSeriesStep,
    HookImage,
)

logger = logging.getLogger(__name__)

_IMAGE_TIMEOUT_SECONDS = 45.0
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF = (1.0, 2.0)
_DIAGRAM_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare"}


def _log_image_event(level: int, event: str, **payload) -> None:
    logger.log(
        level,
        "IMG::%s::%s",
        event,
        json.dumps(payload, sort_keys=True, default=str),
    )


def _publish_outcome(
    generation_id: str,
    section_id: str | None,
    outcome: str,
) -> None:
    if section_id is None:
        return
    publish_runtime_event(
        generation_id,
        DiagramOutcomeEvent(
            generation_id=generation_id,
            section_id=section_id,
            outcome=outcome,
        ),
    )


def _with_outcome(
    state: TextbookPipelineState,
    section_id: str | None,
    outcome: str,
) -> dict:
    if section_id is None:
        return {}

    outcomes = dict(state.diagram_outcomes)
    outcomes[section_id] = outcome
    _publish_outcome(state.request.generation_id or "", section_id, outcome)
    return {"diagram_outcomes": outcomes}


def _visual_required(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    if plan is None:
        return False

    visual_policy = getattr(plan, "visual_policy", None)
    return bool(
        _DIAGRAM_COMPONENTS & set(state.contract.required_components)
        or getattr(plan, "diagram_policy", None) == "required"
        or getattr(plan, "needs_diagram", False)
        or (
            visual_policy is not None and getattr(visual_policy, "required", False)
        )
    )


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        keyword in msg
        for keyword in ("timeout", "connection", "unavailable", "rate", "503", "502", "500")
    )


async def _generate_with_retry(client, prompt: str, timeout: float) -> bytes:
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            result = await asyncio.wait_for(
                client.generate_image(prompt=prompt, size="1024x1024", format="png"),
                timeout=timeout,
            )
            return result.bytes
        except (asyncio.TimeoutError, Exception) as exc:
            is_timeout = isinstance(exc, asyncio.TimeoutError)
            retryable = is_timeout or _is_retryable(exc)
            if not retryable or attempt == _MAX_ATTEMPTS:
                raise

            backoff = _RETRY_BACKOFF[attempt - 1]
            logger.warning(
                "image_generator: attempt %d/%d failed (%s), retrying in %.1fs",
                attempt,
                _MAX_ATTEMPTS,
                "timeout" if is_timeout else exc,
                backoff,
            )
            last_exc = exc
            await asyncio.sleep(backoff)

    raise last_exc


async def _request_image_bytes(
    *,
    client,
    prompt: str,
    section_id: str,
    variant: str,
    api_key_present: bool,
    prompt_details: dict | None = None,
) -> bytes:
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
        image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
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
    )
    return image_bytes


def _get_visual_slot(state: TextbookPipelineState) -> str:
    components = set(state.contract.required_components) | set(state.contract.optional_components)
    for slot in ("diagram-series", "diagram-compare", "diagram-block"):
        if slot in components:
            return slot
    return "diagram-block"


def _visual_intent(state: TextbookPipelineState) -> str:
    plan = state.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    return getattr(visual_policy, "intent", None) or "explain_structure"


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
    image_bytes = await _request_image_bytes(
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
    )


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
            image_bytes = await _request_image_bytes(
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
    )


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
        image_bytes = await _request_image_bytes(
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
        before_bytes, after_bytes = await asyncio.gather(
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
    )


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
    generation_id = state.request.generation_id or "unknown"
    composition_plan = (state.composition_plans or {}).get(sid)
    diagram_plan = composition_plan.diagram if composition_plan is not None else None
    visual_mode = diagram_plan.mode if diagram_plan is not None else None
    visual_enabled = bool(diagram_plan.enabled) if diagram_plan is not None else False
    visual_slot = _get_visual_slot(state)

    _log_image_event(
        logging.INFO,
        "START",
        section_id=sid,
        generation_id=generation_id,
        slot=visual_slot,
        mode=visual_mode,
        enabled=visual_enabled,
        required=_visual_required(state),
        plan_exists=composition_plan is not None,
        intent=_visual_intent(state),
    )

    if not composition_plan or not visual_enabled:
        _log_image_event(
            logging.INFO,
            "SKIP_NOT_ENABLED",
            section_id=sid,
            plan_exists=composition_plan is not None,
            enabled=visual_enabled,
            mode=visual_mode,
        )
        result = {"completed_nodes": ["image_generator"]}
        if composition_plan is not None and visual_mode == "image":
            result.update(_with_outcome(state, sid, "skipped"))
        return result

    if visual_mode != "image":
        _log_image_event(
            logging.INFO,
            "SKIP_MODE",
            section_id=sid,
            mode=visual_mode,
        )
        return {"completed_nodes": ["image_generator"]}

    if section is None:
        _log_image_event(
            logging.ERROR,
            "SECTION_FAILURE",
            section_id=sid,
            reason="no_section_content",
            available_sections=list(state.generated_sections.keys()),
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=f"No section content found for {sid}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "error"),
        }

    if state.style_context is None:
        _log_image_event(
            logging.ERROR,
            "STYLE_CONTEXT_FAILURE",
            section_id=sid,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message="style_context is None -- curriculum_planner may have failed",
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
    except Exception as exc:
        _log_image_event(
            logging.ERROR,
            "CLIENT_INIT_FAILURE",
            section_id=sid,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
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

    _log_image_event(
        logging.INFO,
        "CLIENT_STATUS",
        section_id=sid,
        client_class=type(client).__name__,
        source="injected" if _client is not None else "default",
        api_key_present=api_key_present,
    )

    try:
        if visual_slot == "diagram-series":
            updated_section = await _generate_series_images(
                state=state,
                section=section,
                composition_plan=composition_plan,
                sid=sid,
                store=store,
                client=client,
                generation_id=generation_id,
                api_key_present=api_key_present,
            )
        elif visual_slot == "diagram-compare":
            updated_section = await _generate_compare_images(
                state=state,
                section=section,
                composition_plan=composition_plan,
                sid=sid,
                store=store,
                client=client,
                generation_id=generation_id,
                api_key_present=api_key_present,
            )
        else:
            updated_section = await _generate_single_image(
                state=state,
                section=section,
                composition_plan=composition_plan,
                sid=sid,
                store=store,
                client=client,
                generation_id=generation_id,
                api_key_present=api_key_present,
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

        generated = dict(state.generated_sections)
        generated[sid] = updated_section
        _log_image_event(
            logging.INFO,
            "SUCCESS",
            section_id=sid,
            slot=visual_slot,
            asset_url_present=True,
        )
        return {
            "generated_sections": generated,
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "success"),
        }
    except asyncio.TimeoutError:
        _log_image_event(
            logging.ERROR,
            "TIMEOUT",
            section_id=sid,
            attempts=_MAX_ATTEMPTS,
        )
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=(
                        f"Image generation timed out after {_MAX_ATTEMPTS} attempts "
                        "while calling Gemini."
                    ),
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
            **_with_outcome(state, sid, "timeout"),
        }
    except Exception as exc:
        _log_image_event(
            logging.ERROR,
            "FAILURE",
            section_id=sid,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )
        message = str(exc)
        if not message.startswith(("Image storage failed", "DiagramCompare pair failed")):
            message = f"Image generation failed: {type(exc).__name__}: {exc}"
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
