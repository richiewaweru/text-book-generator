from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from planning.fallback import build_fallback_spec
from planning.models import (
    PlanningGenerationSpec,
    PlanningTemplateContract,
    StudioBriefRequest,
)
from planning.normalizer import normalize_brief
from planning.prompt_builder import refine_plan_text
from planning.section_composer import compose_sections
from planning.template_scorer import choose_template
from planning.visual_router import route_visuals


PlanningEvent = dict[str, object]
PlanningEmitter = Callable[[PlanningEvent], Awaitable[None] | None]


class PlanningService:
    async def plan(
        self,
        brief: StudioBriefRequest,
        *,
        contracts: list[PlanningTemplateContract],
        model: Any,
        run_llm_fn: Callable[..., Awaitable[Any]],
        generation_id: str = "",
        emit: PlanningEmitter | None = None,
        llm_generation_mode: Any = "draft",
    ) -> PlanningGenerationSpec:
        normalized = normalize_brief(brief)
        selected_contract, decision = choose_template(normalized, contracts)
        early_rationale = decision.rationale

        if emit is not None:
            maybe_result = emit(
                {
                    "event": "template_selected",
                    "data": {
                        "template_decision": decision.model_dump(mode="json"),
                        "lesson_rationale": early_rationale,
                        "warning": normalized.scope_warning,
                    },
                }
            )
            if maybe_result is not None:
                await maybe_result

        sections = route_visuals(
            normalized,
            selected_contract,
            compose_sections(normalized, selected_contract),
        )

        if emit is not None:
            for section in sections:
                maybe_result = emit(
                    {
                        "event": "section_planned",
                        "data": {"section": section.model_dump(mode="json")},
                    }
                )
                if maybe_result is not None:
                    await maybe_result

        refined = await refine_plan_text(
            brief=normalized,
            contract=selected_contract,
            sections=sections,
            model=model,
            run_llm_fn=run_llm_fn,
            generation_id=generation_id,
            generation_mode=llm_generation_mode,
        )
        if refined is not None:
            for section, refined_section in zip(sections, refined.sections, strict=True):
                section.title = refined_section.title
                section.rationale = refined_section.rationale
            lesson_rationale = refined.lesson_rationale
            warning = refined.warning or normalized.scope_warning
        else:
            lesson_rationale = early_rationale
            warning = normalized.scope_warning

        return PlanningGenerationSpec(
            id=uuid4().hex,
            template_id=selected_contract.id,
            template_decision=decision,
            lesson_rationale=lesson_rationale,
            directives=normalized.directives,
            committed_budgets=selected_contract.component_budget,
            sections=sections,
            warning=warning,
            source_brief_id=brief.source_brief_id(),
            source_brief=brief,
            status="draft",
        )

    def fallback(
        self,
        brief: StudioBriefRequest,
        *,
        contracts: list[PlanningTemplateContract],
    ) -> PlanningGenerationSpec:
        chosen = next(
            (contract for contract in contracts if contract.id == "guided-concept-path"),
            contracts[0],
        )
        return build_fallback_spec(brief=brief, contract=chosen)
