"""
diagram_generator node -- generates diagrams as images or structured specs.

Routes intelligently: image generation when configured, with auto-fallback
to the existing DiagramSpec (JSON) path on failure.

Reads:
    current_section_id, generated_sections, style_context, contract, composition_plans
Writes:
    generated_sections[current_section_id].diagram, diagram_outcomes, completed_nodes, errors
"""

from __future__ import annotations

import asyncio
import logging

from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel
from pydantic_ai import Agent

from core.config import settings as app_settings
from pipeline.events import DiagramOutcomeEvent
from pipeline.prompts.diagram import (
    build_diagram_system_prompt,
    build_diagram_user_prompt,
    build_image_generation_prompt,
)
from pipeline.providers.registry import get_image_client, get_node_text_model
from pipeline.runtime_context import retry_policy_for_node, timeout_policy_from_config
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.runtime_policy import resolve_runtime_policy_bundle
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.storage.image_store import get_image_store
from pipeline.types.composition import DiagramPlan
from pipeline.types.section_content import (
    DiagramContent,
    DiagramSpec,
    SectionContent,
)
from pipeline.types.template_contract import TemplateContractSummary
from pipeline.llm_runner import run_llm

logger = logging.getLogger(__name__)

_DIAGRAM_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare"}


class DiagramOutput(BaseModel):
    spec: DiagramSpec
    caption: str
    alt_text: str


def _has_diagram_slot(contract) -> bool:
    all_components = set(contract.required_components) | set(contract.optional_components)
    return bool(_DIAGRAM_COMPONENTS & all_components)


def _get_diagram_slot(contract) -> str:
    for slot in ("diagram-block", "diagram-series", "diagram-compare"):
        if slot in contract.required_components or slot in contract.optional_components:
            return slot
    return "diagram-block"


def _publish_outcome(generation_id: str, section_id: str | None, outcome: str) -> None:
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


def should_use_image_generation(
    section: SectionContent,
    contract: TemplateContractSummary,
) -> bool:
    """Decide whether to use image generation vs structured spec."""
    if contract.family == "visual-exploration":
        return True

    science = {"biology", "chemistry", "earth-science", "geography"}
    if any(subject in science for subject in contract.subjects):
        return True

    if section.process is not None:
        return False

    if "mathematics" in contract.subjects:
        title_lower = section.header.title.lower()
        if any(keyword in title_lower for keyword in ["geometry", "triangle", "circle", "angle"]):
            return False

    return True


async def _generate_image_diagram(
    state: TextbookPipelineState,
    section: SectionContent,
    diagram_plan: DiagramPlan,
    section_id: str,
    *,
    model_overrides: dict | None = None,
) -> dict | None:
    """Generate diagram as an image. Returns None when the image path is unavailable."""

    try:
        image_client = get_image_client()
        if image_client is None:
            return None

        prompt = build_image_generation_prompt(
            section=section,
            diagram_plan=diagram_plan,
            style_context=state.style_context,
        )

        result = await image_client.generate_image(
            prompt=prompt,
            size="1024x1024",
            format="png",
        )

        store = get_image_store()
        image_url = await store.store_image(
            result.bytes,
            generation_id=state.request.generation_id or "no-gen-id",
            section_id=section_id,
            filename="diagram.png",
            format="png",
        )

        caption, alt_text = await _generate_image_metadata(
            state,
            section,
            model_overrides=model_overrides,
        )

        diagram = DiagramContent(
            image_url=image_url,
            caption=caption,
            alt_text=alt_text,
        )

        updated = section.model_copy(update={"diagram": diagram})
        return {
            "generated_sections": {section_id: updated},
        }
    except Exception as exc:
        logger.warning(
            "Image generation failed for section %s, falling back to spec: %s",
            section_id,
            exc,
        )
        return None


class _ImageMetadata(BaseModel):
    caption: str
    alt_text: str


async def _generate_image_metadata(
    state: TextbookPipelineState,
    section: SectionContent,
    *,
    model_overrides: dict | None = None,
) -> tuple[str, str]:
    """Generate caption and alt text for an image diagram."""

    try:
        model = get_node_text_model(
            "diagram_generator",
            model_overrides=model_overrides,
            generation_mode=state.request.mode,
        )
        agent = Agent(
            model=model,
            output_type=_ImageMetadata,
            system_prompt=(
                "Generate a concise caption (max 60 words) and alt text (max 80 words) "
                "for an educational diagram image. Output JSON with 'caption' and 'alt_text' fields."
            ),
        )
        result = await asyncio.wait_for(
            run_llm(
                generation_id=state.request.generation_id or "",
                node="diagram_generator",
                agent=agent,
                model=model,
                user_prompt=f"Section: {section.header.title}\nConcept: {section.hook.headline}",
                generation_mode=state.request.mode,
            ),
            timeout=10.0,
        )
        return result.output.caption, result.output.alt_text
    except Exception:
        return (
            f"Diagram for {section.header.title}",
            f"Educational diagram illustrating {section.hook.headline}",
        )


async def _generate_spec_diagram(
    state: TextbookPipelineState,
    section: SectionContent,
    section_id: str,
    plan: object | None,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """Generate diagram as structured DiagramSpec (JSON) via LLM."""

    model = get_node_text_model(
        "diagram_generator",
        model_overrides=model_overrides,
        generation_mode=state.request.mode,
    )
    agent = Agent(
        model=model,
        output_type=DiagramOutput,
        system_prompt=build_diagram_system_prompt(state.style_context),
    )
    timeout_policy = timeout_policy_from_config(config)
    retry_policy = retry_policy_for_node(config, "diagram_generator")
    if timeout_policy is None or retry_policy is None:
        policy = resolve_runtime_policy_bundle(app_settings, state.request.mode)
        timeout_policy = timeout_policy or policy.timeouts
        retry_policy = retry_policy or policy.retries.for_node("diagram_generator")

    result = await asyncio.wait_for(
        run_llm(
            generation_id=state.request.generation_id or "",
            node="diagram_generator",
            agent=agent,
            model=model,
            user_prompt=build_diagram_user_prompt(
                section_title=section.header.title,
                hook_body=section.hook.body,
                explanation_excerpt=section.explanation.body,
                diagram_slot=_get_diagram_slot(state.contract),
                diagram_type=plan.diagram.diagram_type if plan is not None else None,
                key_concepts=plan.diagram.key_concepts if plan is not None else None,
                visual_guidance=plan.diagram.visual_guidance if plan is not None else None,
            ),
            generation_mode=state.request.mode,
            retry_policy=retry_policy,
        ),
        timeout=timeout_policy.diagram_node_budget_seconds,
    )

    diagram = DiagramContent(
        spec=result.output.spec,
        caption=result.output.caption,
        alt_text=result.output.alt_text,
    )
    updated = section.model_copy(update={"diagram": diagram})

    return {
        "generated_sections": {section_id: updated},
    }


async def diagram_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """Generate an optional visual explanation for the current section."""

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    outcomes = dict(state.diagram_outcomes)
    plan = state.composition_plans.get(sid)

    if not _has_diagram_slot(state.contract):
        if sid:
            outcomes[sid] = "skipped"
            _publish_outcome(state.request.generation_id or "", sid, "skipped")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    section = state.generated_sections.get(sid)
    if sid is None or section is None:
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if plan is not None and not plan.diagram.enabled:
        outcomes[sid] = "skipped"
        _publish_outcome(state.request.generation_id or "", sid, "skipped")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if plan is None and state.current_section_plan and not state.current_section_plan.needs_diagram:
        outcomes[sid] = "skipped"
        _publish_outcome(state.request.generation_id or "", sid, "skipped")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if state.style_context is None:
        outcomes[sid] = "error"
        _publish_outcome(state.request.generation_id or "", sid, "error")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message="style_context is None -- curriculum_planner may have failed",
                    recoverable=False,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }

    use_image = should_use_image_generation(section, state.contract)
    if use_image and plan is not None:
        image_result = await _generate_image_diagram(
            state,
            section,
            plan.diagram,
            sid,
            model_overrides=model_overrides,
        )
        if image_result is not None:
            outcomes[sid] = "image_success"
            _publish_outcome(state.request.generation_id or "", sid, "image_success")
            return {
                **image_result,
                "diagram_outcomes": outcomes,
                "completed_nodes": ["diagram_generator"],
            }
        logger.info("Image generation unavailable for %s, using spec path", sid)

    try:
        spec_result = await _generate_spec_diagram(
            state,
            section,
            sid,
            plan,
            model_overrides=model_overrides,
            config=config,
        )
        outcome = "image_fallback_to_spec" if use_image else "spec_success"
        outcomes[sid] = outcome
        _publish_outcome(state.request.generation_id or "", sid, outcome)
        return {
            **spec_result,
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
    except asyncio.TimeoutError:
        timeout_policy = timeout_policy_from_config(config)
        if timeout_policy is None:
            timeout_policy = resolve_runtime_policy_bundle(
                app_settings,
                state.request.mode,
            ).timeouts
        outcomes[sid] = "timeout"
        _publish_outcome(state.request.generation_id or "", sid, "timeout")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message=(
                        f"Diagram generation timed out ({int(timeout_policy.diagram_node_budget_seconds)}s) "
                        "and the section will ship without a diagram."
                    ),
                    recoverable=True,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
    except Exception as exc:
        outcomes[sid] = "error"
        _publish_outcome(state.request.generation_id or "", sid, "error")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message=f"Diagram generation failed: {exc}",
                    recoverable=True,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
