from __future__ import annotations

import asyncio
import logging

from pipeline.prompts.diagram import (
    build_hook_image_prompt,
    build_image_generation_prompt,
    build_series_step_image_prompt,
)
from pipeline.providers.gemini_image_client import get_gemini_image_client
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.storage.image_store import get_image_store
from pipeline.types.section_content import (
    DiagramContent,
    DiagramSeriesContent,
    DiagramSeriesStep,
    HookImage,
)

logger = logging.getLogger(__name__)

_IMAGE_TIMEOUT_SECONDS = 45.0
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF = (1.0, 2.0)


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
    image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
    image_url = await store.store_image(
        image_bytes,
        generation_id=generation_id,
        section_id=sid,
        filename="diagram.png",
        format="png",
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
            image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
            image_url = await store.store_image(
                image_bytes,
                generation_id=generation_id,
                section_id=sid,
                filename=f"series-step-{index + 1}.png",
                format="png",
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
        image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)
        image_url = await store.store_image(
            image_bytes,
            generation_id=generation_id,
            section_id=sid,
            filename="hook.png",
            format="png",
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

    composition_plan = (state.composition_plans or {}).get(sid)
    if not composition_plan or not composition_plan.diagram.enabled:
        return {"completed_nodes": ["image_generator"]}
    if composition_plan.diagram.mode != "image":
        return {"completed_nodes": ["image_generator"]}

    if section is None:
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
    if visual_slot == "diagram-compare":
        logger.info("image_generator: diagram-compare stays SVG-only, skipping section %s", sid)
        return {"completed_nodes": ["image_generator"]}

    generation_id = state.request.generation_id or "unknown"

    try:
        store = _store or get_image_store()
        client = _client or get_gemini_image_client()

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
        return {
            "generated_sections": generated,
            "completed_nodes": ["image_generator"],
        }
    except asyncio.TimeoutError:
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=(
                        f"Image generation timed out after {_MAX_ATTEMPTS} attempts. "
                        "Section ships without image."
                    ),
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
        }
    except Exception as exc:
        return {
            "errors": [
                PipelineError(
                    node="image_generator",
                    section_id=sid,
                    message=f"Image generation failed after {_MAX_ATTEMPTS} attempts: {exc}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["image_generator"],
        }
