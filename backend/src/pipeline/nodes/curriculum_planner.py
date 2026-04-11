"""
curriculum_planner node.

STATE CONTRACT
    Reads:  request, contract
    Writes: curriculum_outline, style_context, completed_nodes, errors
    Slot:   FAST (resolved centrally in pipeline.providers.registry)
"""

from __future__ import annotations

import logging

from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from core.config import settings as app_settings
from pipeline.contracts import get_preset, validate_preset_for_template
from pipeline.events import SectionStartedEvent
from pipeline.prompts.curriculum import (
    build_curriculum_enrichment_system_prompt,
    build_curriculum_enrichment_user_prompt,
    build_curriculum_system_prompt,
    build_curriculum_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.runtime_context import retry_policy_for_node
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.runtime_policy import resolve_runtime_policy_bundle
from pipeline.state import PipelineError, StyleContext, TextbookPipelineState
from pipeline.types.requests import SectionPlan
from pipeline.llm_runner import run_llm

logger = logging.getLogger(__name__)


class CurriculumOutput(BaseModel):
    sections: list[SectionPlan]


class SectionPlanEnrichment(BaseModel):
    section_id: str
    terms_to_define: list[str] = Field(default_factory=list)
    terms_assumed: list[str] = Field(default_factory=list)
    practice_target: str | None = None
    visual_commitment: str | None = None


class CurriculumEnrichmentOutput(BaseModel):
    sections: list[SectionPlanEnrichment] = Field(default_factory=list)


def _build_style_context(state: TextbookPipelineState) -> StyleContext:
    preset = get_preset(state.request.preset_id)
    return StyleContext(
        preset_id=preset.id,
        palette=preset.palette,
        surface_style=preset.surface_style,
        density=preset.density,
        typography=preset.typography,
        template_id=state.contract.id,
        template_family=state.contract.family,
        interaction_level=state.contract.interaction_level,
        grade_band=state.request.grade_band,
        learner_fit=state.request.learner_fit,
    )


def _outline_from_request(state: TextbookPipelineState) -> list[SectionPlan]:
    supplied = state.request.section_plans or []
    outline = [SectionPlan.model_validate(plan) for plan in supplied]
    outline.sort(key=lambda item: (item.position, item.section_id))
    return outline


def _publish_section_titles(
    generation_id: str,
    sections: list[SectionPlan],
) -> None:
    """Emit SectionStartedEvent per section so the frontend shows the outline immediately."""
    for plan in sections:
        publish_runtime_event(
            generation_id,
            SectionStartedEvent(
                generation_id=generation_id,
                section_id=plan.section_id,
                title=plan.title,
                position=plan.position,
            ),
        )


def _warn_duplicate_terms(sections: list[SectionPlan], generation_id: str) -> None:
    seen: dict[str, str] = {}
    for plan in sections:
        for term in plan.terms_to_define:
            key = term.lower().strip()
            if not key:
                continue
            if key in seen:
                logger.warning(
                    "Duplicate term assignment in curriculum plan generation_id=%s term=%s first_section=%s duplicate_section=%s",
                    generation_id,
                    term,
                    seen[key],
                    plan.section_id,
                )
            else:
                seen[key] = plan.section_id


def _outline_digest(outline: list[SectionPlan]) -> list[dict[str, object]]:
    return [
        {
            "section_id": plan.section_id,
            "title": plan.title,
            "position": plan.position,
            "focus": plan.focus,
            "role": plan.role,
            "bridges_from": plan.bridges_from,
            "bridges_to": plan.bridges_to,
            "needs_diagram": plan.needs_diagram,
            "needs_worked_example": plan.needs_worked_example,
        }
        for plan in outline
    ]


def _apply_enrichment(
    outline: list[SectionPlan],
    enrichment: list[SectionPlanEnrichment],
) -> list[SectionPlan]:
    enrichment_by_id = {item.section_id: item for item in enrichment}
    return [
        plan.model_copy(
            update={
                "terms_to_define": list(enrichment_by_id[plan.section_id].terms_to_define),
                "terms_assumed": list(enrichment_by_id[plan.section_id].terms_assumed),
                "practice_target": enrichment_by_id[plan.section_id].practice_target,
                "visual_commitment": enrichment_by_id[plan.section_id].visual_commitment,
            }
        )
        if plan.section_id in enrichment_by_id
        else plan
        for plan in outline
    ]


async def _enrich_seeded_outline(
    state: TextbookPipelineState,
    outline: list[SectionPlan],
    *,
    model,
    retry_policy,
) -> list[SectionPlan]:
    agent = Agent(
        model=model,
        output_type=CurriculumEnrichmentOutput,
        system_prompt=build_curriculum_enrichment_system_prompt(
            template_id=state.contract.id,
            template_name=state.contract.name,
            template_family=state.contract.family,
        ),
    )
    try:
        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="curriculum_planner",
            agent=agent,
            model=model,
            user_prompt=build_curriculum_enrichment_user_prompt(
                context=state.request.context,
                subject=state.request.subject,
                grade_band=state.request.grade_band,
                learner_fit=state.request.learner_fit,
                sections=_outline_digest(outline),
            ),
            generation_mode=state.request.mode,
            retry_policy=retry_policy,
        )
        return _apply_enrichment(outline, result.output.sections)
    except Exception as exc:
        logger.warning(
            "Curriculum outline enrichment failed; using supplied outline unchanged generation_id=%s error=%s",
            state.request.generation_id or "",
            exc,
        )
        return outline


async def curriculum_planner(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """Generate the curriculum outline or reuse the seeded outline when present."""

    state = TextbookPipelineState.parse(state)

    if not validate_preset_for_template(state.contract.id, state.request.preset_id):
        return {
            "errors": [
                PipelineError(
                    node="curriculum_planner",
                    message=(
                        f"Preset '{state.request.preset_id}' is not allowed "
                        f"for template '{state.contract.id}'"
                    ),
                    recoverable=False,
                )
            ],
            "completed_nodes": ["curriculum_planner"],
        }

    style_context = _build_style_context(state)
    model = get_node_text_model(
        "curriculum_planner",
        model_overrides=model_overrides,
        generation_mode=state.request.mode,
    )
    retry_policy = retry_policy_for_node(config, "curriculum_planner")
    if retry_policy is None:
        retry_policy = resolve_runtime_policy_bundle(
            app_settings,
            state.request.mode,
        ).retries.for_node("curriculum_planner")

    if state.request.section_plans:
        outline = _outline_from_request(state)
        outline = await _enrich_seeded_outline(
            state,
            outline,
            model=model,
            retry_policy=retry_policy,
        )
        _warn_duplicate_terms(outline, state.request.generation_id or "")
        _publish_section_titles(state.request.generation_id or "", outline)
        return {
            "curriculum_outline": outline,
            "style_context": style_context,
            "completed_nodes": ["curriculum_planner"],
        }

    agent = Agent(
        model=model,
        output_type=CurriculumOutput,
        system_prompt=build_curriculum_system_prompt(
            template_id=state.contract.id,
            template_name=state.contract.name,
            template_family=state.contract.family,
        ),
    )

    try:
        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="curriculum_planner",
            agent=agent,
            model=model,
            user_prompt=build_curriculum_user_prompt(
                context=state.request.context,
                subject=state.request.subject,
                grade_band=state.request.grade_band,
                learner_fit=state.request.learner_fit,
                section_count=state.request.section_count,
            ),
            generation_mode=state.request.mode,
            retry_policy=retry_policy,
        )
        _warn_duplicate_terms(result.output.sections, state.request.generation_id or "")
        _publish_section_titles(
            state.request.generation_id or "", result.output.sections
        )
        return {
            "curriculum_outline": result.output.sections,
            "style_context": style_context,
            "completed_nodes": ["curriculum_planner"],
        }
    except Exception as exc:
        return {
            "curriculum_outline": [],
            "style_context": style_context,
            "errors": [
                PipelineError(
                    node="curriculum_planner",
                    message=f"LLM call failed: {exc}",
                    recoverable=False,
                )
            ],
            "completed_nodes": ["curriculum_planner"],
        }
