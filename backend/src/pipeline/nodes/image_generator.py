from __future__ import annotations

import json
import sys

import asyncio
import logging

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
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.storage.image_store import get_image_store
from pipeline.types.section_content import (
    DiagramContent,
    DiagramCompareContent,
    DiagramSeriesContent,
    DiagramSeriesStep,
    HookImage,
)

logger = logging.getLogger(__name__)

_IMAGE_TIMEOUT_SECONDS = 45.0
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF = (1.0, 2.0)


def diag(tag: str, **fields) -> None:
    sys.stderr.write(f"DIAG::{tag}::{json.dumps(fields, default=str)}\n")
    sys.stderr.flush()


diag("BUILD_MARKER", file="image_generator", version="diag_v1")


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
        logger.error(
            "image_generator: FAIL sid=%s reason=store_failed variant=%s error_type=%s error=%s",
            section_id,
            variant,
            type(exc).__name__,
            exc,
        )
        raise RuntimeError(
            f"Image storage failed for {variant}: {type(exc).__name__}: {exc}"
        ) from exc

    logger.info(
        "image_generator: STORE_SUCCESS sid=%s variant=%s image_url=%s",
        section_id,
        variant,
        image_url,
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
):
    prompt = build_image_generation_prompt(
        section=section,
        diagram_plan=composition_plan.diagram,
        style_context=state.style_context,
    )
    logger.info(
        "image_generator: CALLING_GEMINI sid=%s variant=single prompt_length=%d",
        sid,
        len(prompt),
    )
    image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
    logger.info(
        "image_generator: GEMINI_SUCCESS sid=%s variant=single bytes=%d",
        sid,
        len(image_bytes),
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
            logger.info(
                "image_generator: CALLING_GEMINI sid=%s variant=series step=%d/%d prompt_length=%d",
                sid,
                index + 1,
                len(seed_steps),
                len(prompt),
            )
            image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
            logger.info(
                "image_generator: GEMINI_SUCCESS sid=%s variant=series step=%d/%d bytes=%d",
                sid,
                index + 1,
                len(seed_steps),
                len(image_bytes),
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
            logger.warning(
                "image_generator: series step %d/%d failed for section %s: %s",
                index + 1,
                len(seed_steps),
                sid,
                exc,
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
        logger.info(
            "image_generator: CALLING_GEMINI sid=%s variant=hook prompt_length=%d",
            sid,
            len(prompt),
        )
        image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
        logger.info(
            "image_generator: GEMINI_SUCCESS sid=%s variant=hook bytes=%d",
            sid,
            len(image_bytes),
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
        logger.warning(
            "image_generator: hook image failed for section %s (non-fatal): %s",
            sid,
            exc,
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
        logger.info(
            "image_generator: CALLING_GEMINI sid=%s variant=compare prompts=%d,%d",
            sid,
            len(before_prompt),
            len(after_prompt),
        )
        before_bytes, after_bytes = await asyncio.gather(
            _generate_with_retry(client, before_prompt, _IMAGE_TIMEOUT_SECONDS),
            _generate_with_retry(client, after_prompt, _IMAGE_TIMEOUT_SECONDS),
        )
        logger.info(
            "image_generator: GEMINI_SUCCESS sid=%s variant=compare before_bytes=%d after_bytes=%d",
            sid,
            len(before_bytes),
            len(after_bytes),
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
    _s = state if isinstance(state, dict) else state.model_dump() if hasattr(state, "model_dump") else {}
    _sid = _s.get("current_section_id", "UNKNOWN")
    _plans = _s.get("composition_plans") or {}
    _plan = _plans.get(_sid)
    _mode = _plan.get("diagram", {}).get("mode") if isinstance(_plan, dict) else getattr(getattr(_plan, "diagram", None), "mode", None) if _plan else None
    _enabled = _plan.get("diagram", {}).get("enabled") if isinstance(_plan, dict) else getattr(getattr(_plan, "diagram", None), "enabled", None) if _plan else None
    _current_section_plan = _s.get("current_section_plan")
    if isinstance(_current_section_plan, dict):
        _current_plan_visual_policy = _current_section_plan.get("visual_policy")
    else:
        _current_visual_policy = getattr(_current_section_plan, "visual_policy", None)
        _current_plan_visual_policy = (
            _current_visual_policy.model_dump()
            if _current_visual_policy is not None and hasattr(_current_visual_policy, "model_dump")
            else _current_visual_policy
        )
    diag(
        "IMGGEN_GATE",
        section_id=_sid,
        mode=_mode,
        enabled=_enabled,
        plan_exists=_plan is not None,
        current_plan_visual_policy=_current_plan_visual_policy,
    )
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)
    generation_id = state.request.generation_id or "unknown"

    composition_plan = (state.composition_plans or {}).get(sid)
    if not composition_plan or not composition_plan.diagram.enabled:
        logger.info(
            "image_generator: SKIP sid=%s reason=diagram_not_enabled plan_exists=%s enabled=%s",
            sid,
            composition_plan is not None,
            composition_plan.diagram.enabled if composition_plan is not None else False,
        )
        return {"completed_nodes": ["image_generator"]}
    if composition_plan.diagram.mode != "image":
        logger.info(
            "image_generator: SKIP sid=%s reason=mode_not_image mode=%s",
            sid,
            composition_plan.diagram.mode,
        )
        return {"completed_nodes": ["image_generator"]}

    if section is None:
        logger.error(
            "image_generator: FAIL sid=%s reason=no_section_content available_sections=%s",
            sid,
            list(state.generated_sections.keys()),
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
        }

    if state.style_context is None:
        logger.error(
            "image_generator: FAIL sid=%s reason=no_style_context",
            sid,
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
        }

    visual_slot = _get_visual_slot(state)
    logger.info(
        "image_generator: START sid=%s generation_id=%s slot=%s intent=%s",
        sid,
        generation_id,
        visual_slot,
        _visual_intent(state),
    )

    try:
        store = _store or get_image_store()
        logger.info(
            "image_generator: store_resolved sid=%s store_type=%s source=%s target=%s",
            sid,
            type(store).__name__,
            "injected" if _store is not None else "default",
            store.describe_target(),
        )
    except Exception as exc:
        logger.error(
            "image_generator: FAIL sid=%s reason=store_init_failed error_type=%s error=%s",
            sid,
            type(exc).__name__,
            exc,
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
        }

    api_key = resolve_gemini_image_api_key()
    logger.info(
        "image_generator: api_key_present=%s sid=%s checked_vars=%s",
        bool(api_key),
        sid,
        ",".join(
            ("GOOGLE_CLOUD_NANO_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
        ),
    )
    if _client is None and not api_key:
        logger.error(
            "image_generator: FAIL sid=%s reason=no_api_key",
            sid,
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
        }

    try:
        client = _client or get_gemini_image_client()
        logger.info(
            "image_generator: client_resolved sid=%s client_type=%s source=%s",
            sid,
            type(client).__name__,
            "injected" if _client is not None else "default",
        )
    except Exception as exc:
        logger.error(
            "image_generator: FAIL sid=%s reason=client_init_failed error_type=%s error=%s",
            sid,
            type(exc).__name__,
            exc,
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
        }

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
            )

        if _visual_intent(state) == "show_realism":
            updated_section = await _maybe_generate_hook_image(
                state=state,
                section=updated_section,
                sid=sid,
                store=store,
                client=client,
                generation_id=generation_id,
            )

        generated = dict(state.generated_sections)
        generated[sid] = updated_section
        logger.info(
            "image_generator: SUCCESS sid=%s slot=%s",
            sid,
            visual_slot,
        )
        return {
            "generated_sections": generated,
            "completed_nodes": ["image_generator"],
        }
    except asyncio.TimeoutError:
        logger.error(
            "image_generator: FAIL sid=%s reason=timeout attempts=%d",
            sid,
            _MAX_ATTEMPTS,
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
        }
    except Exception as exc:
        logger.error(
            "image_generator: FAIL sid=%s reason=unexpected error_type=%s error=%s",
            sid,
            type(exc).__name__,
            exc,
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
        }
