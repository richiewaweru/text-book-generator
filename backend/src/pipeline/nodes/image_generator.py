from __future__ import annotations

import asyncio
import logging

from core.dependencies import get_gcs_image_store
from pipeline.providers.gemini_image_client import get_gemini_image_client
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.types.section_content import DiagramContent

logger = logging.getLogger(__name__)

_IMAGE_TIMEOUT_SECONDS = 45.0
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF = (1.0, 2.0)  # seconds before attempt 2, then attempt 3


def _build_prompt(
    section_title: str,
    hook_body: str,
    style_notes: str,
    intent: str,
) -> str:
    intent_instruction = {
        "show_realism": (
            "A realistic educational illustration grounding the topic in the real world."
        ),
        "demonstrate_process": (
            "A clear step-by-step process illustration showing the sequence of steps."
        ),
        "compare_variants": (
            "A clear side-by-side comparison illustration highlighting key differences."
        ),
        "explain_structure": (
            "A clean structural diagram showing the key relationships and components."
        ),
    }.get(intent, "An educational illustration.")

    return (
        f"{intent_instruction} "
        f"Topic: {section_title}. "
        f"Context: {hook_body[:300]}. "
        f"Style: {style_notes or 'Classroom-friendly, accurate, no decorative clutter'}. "
        f"Requirements: white background, clearly labelled, suitable for printing "
        f"in a school textbook, no text overlays beyond necessary labels."
    )


def _is_retryable(exc: Exception) -> bool:
    """Only retry transient infrastructure errors, not content/model errors."""
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "timeout", "connection", "unavailable", "rate", "503", "502", "500",
    ))


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

    raise last_exc  # unreachable


async def image_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    _store=None,   # injectable for tests
    _client=None,  # injectable for tests
) -> dict:
    """
    Generate a raster image for sections where composition_plan.diagram.mode == 'image'.
    Runs in Phase 3 parallel alongside diagram_generator.

    Reads:  current_section_id, generated_sections, composition_plans,
            current_section_plan, request.generation_id
    Writes: generated_sections[sid].diagram.image_url
    """
    _ = model_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)

    # Gate: only run when composition_planner set mode="image"
    composition_plan = (state.composition_plans or {}).get(sid)
    if not composition_plan or not composition_plan.diagram.enabled:
        return {"completed_nodes": ["image_generator"]}
    if composition_plan.diagram.mode != "image":
        return {"completed_nodes": ["image_generator"]}

    if section is None:
        return {
            "errors": [PipelineError(
                node="image_generator",
                section_id=sid,
                message=f"No section content found for {sid}",
                recoverable=True,
            )],
            "completed_nodes": ["image_generator"],
        }

    # GCS guard: skip silently if storage not configured
    store = _store or get_gcs_image_store()
    if not store.enabled:
        return {"completed_nodes": ["image_generator"]}

    # Build prompt from visual_policy intent
    plan = state.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan else None
    intent = visual_policy.intent if visual_policy else "explain_structure"
    style_notes = visual_policy.style_notes if visual_policy else ""

    prompt = _build_prompt(
        section_title=section.header.title,
        hook_body=section.hook.body,
        style_notes=style_notes,
        intent=intent,
    )

    generation_id = state.request.generation_id or "unknown"

    try:
        client = _client or get_gemini_image_client()
        image_bytes = await _generate_with_retry(client, prompt, _IMAGE_TIMEOUT_SECONDS)

        image_url = await store.upload(
            generation_id=generation_id,
            section_id=sid,
            image_bytes=image_bytes,
            content_type="image/png",
        )

        existing = section.diagram or DiagramContent(
            caption=f"Visual illustration for {section.header.title}",
            alt_text=(
                f"Educational image illustrating {section.header.title}. "
                f"{composition_plan.diagram.visual_guidance or ''}"
            ),
        )
        updated_diagram = existing.model_copy(update={"image_url": image_url})
        updated_section = section.model_copy(update={"diagram": updated_diagram})

        generated = dict(state.generated_sections)
        generated[sid] = updated_section

        return {
            "generated_sections": generated,
            "completed_nodes": ["image_generator"],
        }

    except asyncio.TimeoutError:
        return {
            "errors": [PipelineError(
                node="image_generator",
                section_id=sid,
                message=(
                    f"Image generation timed out after {_MAX_ATTEMPTS} attempts. "
                    "Section ships without image."
                ),
                recoverable=True,
            )],
            "completed_nodes": ["image_generator"],
        }
    except Exception as exc:
        return {
            "errors": [PipelineError(
                node="image_generator",
                section_id=sid,
                message=f"Image generation failed after {_MAX_ATTEMPTS} attempts: {exc}",
                recoverable=True,
            )],
            "completed_nodes": ["image_generator"],
        }
