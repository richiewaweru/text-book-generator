"""
composition_planner node -- LLM-powered composition decisions with heuristic fallback.

Reads:
    current_section_id, generated_sections, contract, request,
    current_section_plan, style_context, interaction_usage
Writes:
    composition_plans, interaction_usage, completed_nodes
Slot: FAST
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from core.llm.logging import NodeLogger
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from pipeline.llm_runner import run_llm
from pipeline.prompts.composition import (
    build_composition_system_prompt,
    build_composition_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.state import TextbookPipelineState
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan

logger = logging.getLogger(__name__)

_COMPOSITION_TIMEOUT = 15.0


def diag(tag: str, **fields) -> None:
    sys.stderr.write(f"DIAG::{tag}::{json.dumps(fields, default=str)}\n")
    sys.stderr.flush()


diag("BUILD_MARKER", file="composition_planner", version="diag_v1")


def _has_simulation_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return "simulation-block" in components


_DIAGRAM_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare"}


def _has_diagram_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return bool(_DIAGRAM_COMPONENTS & components)


def _diagram_allowed(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    diag(
        "DIAGRAM_ALLOWED_INPUT",
        section_id=state.current_section_id,
        plan_exists=plan is not None,
        plan_required_components=getattr(plan, "required_components", None),
        plan_diagram_policy=getattr(plan, "diagram_policy", None),
        plan_needs_diagram=getattr(plan, "needs_diagram", None),
        plan_visual_policy=(
            getattr(plan, "visual_policy", None).model_dump()
            if getattr(plan, "visual_policy", None) is not None
            else None
        ),
        contract_required_components=getattr(state.contract, "required_components", None),
        contract_always_present=getattr(state.contract, "always_present", None),
    )
    if plan is None:
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=False,
            reason="plan_none",
        )
        return False

    if getattr(plan, "diagram_policy", None) == "disabled":
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=False,
            reason="diagram_policy_disabled",
        )
        return False

    if not _has_diagram_slot(state.contract):
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=False,
            reason="no_diagram_slot",
        )
        return False

    if _DIAGRAM_COMPONENTS & set(state.contract.required_components):
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=True,
            reason="contract_required_components_contains_diagram",
        )
        return True

    if getattr(plan, "diagram_policy", None) == "required":
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=True,
            reason="diagram_policy_required",
        )
        return True

    if getattr(plan, "needs_diagram", False):
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=True,
            reason="needs_diagram",
        )
        return True

    section_required = set(getattr(plan, "required_components", []))
    if _DIAGRAM_COMPONENTS & section_required:
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=True,
            reason="required_components_contains_diagram",
        )
        return True

    vp = getattr(plan, "visual_policy", None)
    if vp is not None and getattr(vp, "required", False):
        diag(
            "DIAGRAM_ALLOWED_DECISION",
            section_id=state.current_section_id,
            decision=True,
            reason="visual_policy_required",
        )
        return True

    diag(
        "DIAGRAM_ALLOWED_DECISION",
        section_id=state.current_section_id,
        decision=False,
        reason="fell_through_false",
    )
    return False


def _interaction_allowed(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    if plan is None:
        return False
    if plan.interaction_policy == "disabled":
        return False
    if not state.request.interactions_enabled():
        return False
    if state.contract.interaction_level not in {"medium", "high"}:
        return False
    if not _has_simulation_slot(state.contract):
        return False
    return True


def _diagram_type(section) -> str:
    if section.process is not None:
        return "process"
    if section.timeline is not None:
        return "timeline"
    if section.diagram_compare is not None or section.comparison_grid is not None:
        return "comparison"
    return "concept_map"


def _compare_labels(section) -> tuple[str | None, str | None]:
    if section.comparison_grid is not None and len(section.comparison_grid.columns) >= 2:
        before = section.comparison_grid.columns[0].title.strip() or "Before"
        after = section.comparison_grid.columns[1].title.strip() or "After"
        return before, after
    if section.diagram_compare is not None:
        before = section.diagram_compare.before_label.strip() or "Before"
        after = section.diagram_compare.after_label.strip() or "After"
        return before, after
    return None, None


def pick_interaction_type(state: TextbookPipelineState, section) -> str:
    """Canonical interaction type picker -- shared with interaction_decider."""
    subject = state.request.subject.lower()
    if section.timeline is not None or "history" in subject:
        return "timeline_scrubber"
    if section.process is not None:
        return "equation_reveal"
    if section.diagram is not None and ("geometry" in subject or "physics" in subject):
        return "geometry_explorer"
    if "probability" in subject:
        return "probability_tree"
    return "graph_slider"


def _heuristic_fallback(
    state: TextbookPipelineState,
    section,
    *,
    diagram_enabled: bool,
    interaction_enabled: bool,
    visual_mode: str | None = None,
) -> CompositionPlan:
    """Build a CompositionPlan using the original heuristic logic."""
    plan = state.current_section_plan

    key_concepts: list[str] = []
    if section.definition is not None:
        key_concepts.append(section.definition.term)
    key_concepts.extend(section.explanation.emphasis[:3])
    compare_before_label, compare_after_label = _compare_labels(section)

    return CompositionPlan(
        diagram=DiagramPlan(
            enabled=diagram_enabled,
            mode=visual_mode if diagram_enabled else None,
            reasoning=(
                "The reviewed section plan requires or strongly prefers a diagram."
                if diagram_enabled
                else "The reviewed section plan keeps this section text-first."
            ),
            diagram_type=_diagram_type(section) if diagram_enabled else None,
            compare_before_label=compare_before_label if diagram_enabled else None,
            compare_after_label=compare_after_label if diagram_enabled else None,
            focus_area="process" if section.process is not None else "explanation",
            key_concepts=key_concepts[:4],
            visual_guidance=(
                f"{plan.focus}. {plan.continuity_notes}"
                if plan is not None and plan.continuity_notes
                else plan.focus if plan is not None else None
            ),
        ),
        interaction=InteractionPlan(
            enabled=interaction_enabled,
            reasoning=(
                "The reviewed section plan allows an interaction for this section."
                if interaction_enabled
                else "This section should not add an interaction in the current plan."
            ),
            interaction_type=(
                pick_interaction_type(state, section) if interaction_enabled else None
            ),
            anchor_block=(
                "timeline"
                if section.timeline is not None
                else "worked_example"
                if section.worked_example is not None
                else "explanation"
            ),
        ),
    )


class DiagramDecision(BaseModel):
    enabled: bool
    reasoning: str
    diagram_type: str | None = None
    key_concepts: list[str] = Field(default_factory=list)
    visual_guidance: str | None = None
    fallback_from_interaction: bool = False
    interaction_intent: str | None = None
    interaction_elements: list[str] = Field(default_factory=list)


class InteractionDecision(BaseModel):
    enabled: bool
    reasoning: str
    interaction_type: str
    anchor_block: str = "explanation"
    manipulable_element: str = ""
    response_element: str = ""
    pedagogical_payoff: str = ""
    complexity: str = "simple"


class CompositionDecision(BaseModel):
    """Structured output from the composition LLM call."""

    diagram: DiagramDecision
    interactions: list[InteractionDecision] = Field(default_factory=list)
    reasoning: str = ""
    confidence: str = "medium"


def _to_composition_plan(
    decision: CompositionDecision,
    *,
    section,
    diagram_allowed: bool,
    interaction_allowed: bool,
    visual_mode: str | None = None,
) -> CompositionPlan:
    """Convert LLM decision to CompositionPlan, enforcing guard-rail overrides."""

    enabled = decision.diagram.enabled and diagram_allowed
    compare_before_label, compare_after_label = _compare_labels(section)
    diagram = DiagramPlan(
        enabled=enabled,
        mode=visual_mode if enabled else None,
        reasoning=decision.diagram.reasoning,
        diagram_type=decision.diagram.diagram_type,
        compare_before_label=compare_before_label if enabled else None,
        compare_after_label=compare_after_label if enabled else None,
        key_concepts=decision.diagram.key_concepts,
        visual_guidance=decision.diagram.visual_guidance,
        fallback_from_interaction=decision.diagram.fallback_from_interaction,
        interaction_intent=decision.diagram.interaction_intent,
        interaction_elements=decision.diagram.interaction_elements,
    )

    interactions: list[InteractionPlan] = []
    for i_decision in decision.interactions:
        interactions.append(
            InteractionPlan(
                enabled=i_decision.enabled and interaction_allowed,
                reasoning=i_decision.reasoning,
                interaction_type=i_decision.interaction_type,
                anchor_block=i_decision.anchor_block,
                manipulable_element=i_decision.manipulable_element,
                response_element=i_decision.response_element,
                pedagogical_payoff=i_decision.pedagogical_payoff,
                complexity=i_decision.complexity,
            )
        )

    first_enabled = next((i for i in interactions if i.enabled), None)
    singular = first_enabled or InteractionPlan(
        enabled=False,
        reasoning="No interactions selected.",
    )

    return CompositionPlan(
        diagram=diagram,
        interaction=singular,
        interactions=interactions,
        reasoning=decision.reasoning,
        confidence=decision.confidence,
    )


async def composition_planner(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Decide visual and interactive elements using LLM reasoning.

    Falls back to heuristic logic on any LLM failure.
    """

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)
    if sid is None or section is None:
        return {"completed_nodes": ["composition_planner"]}
    node_logger = NodeLogger(
        generation_id=state.request.generation_id or "",
        section_id=sid,
        node_name="composition_planner",
    )

    diagram_ok = _diagram_allowed(state)
    interaction_ok = _interaction_allowed(state)

    plan = state.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    visual_mode = (
        visual_policy.mode
        if visual_policy is not None and getattr(visual_policy, "required", False)
        else None
    )

    if not diagram_ok and not interaction_ok:
        composition = _heuristic_fallback(
            state,
            section,
            diagram_enabled=False,
            interaction_enabled=False,
            visual_mode=visual_mode,
        )
        diag(
            "COMPOSITION_PLAN_DIAGRAM",
            section_id=state.current_section_id,
            enabled=composition.diagram.enabled,
            mode=composition.diagram.mode,
            source="heuristic_skip",
        )
        return {
            "composition_plans": {sid: composition},
            "completed_nodes": ["composition_planner"],
        }

    try:
        system_prompt = build_composition_system_prompt(state.contract)
        user_prompt = build_composition_user_prompt(
            section=section,
            subject=state.request.subject,
            grade_band=state.request.grade_band,
            interaction_usage=state.interaction_usage,
        )

        model = get_node_text_model(
            "composition_planner",
            model_overrides=model_overrides,
            generation_mode=state.request.mode,
        )

        agent = Agent(
            model=model,
            output_type=CompositionDecision,
            system_prompt=system_prompt,
        )

        result = await asyncio.wait_for(
            run_llm(
                generation_id=state.request.generation_id or "",
                node="composition_planner",
                agent=agent,
                model=model,
                user_prompt=user_prompt,
                generation_mode=state.request.mode,
            ),
            timeout=_COMPOSITION_TIMEOUT,
        )

        composition = _to_composition_plan(
            result.output,
            section=section,
            diagram_allowed=diagram_ok,
            interaction_allowed=interaction_ok,
            visual_mode=visual_mode,
        )
        diag(
            "COMPOSITION_PLAN_DIAGRAM",
            section_id=state.current_section_id,
            enabled=composition.diagram.enabled,
            mode=composition.diagram.mode,
            source="llm",
        )

    except Exception:
        node_logger.warning(
            "composition_planner LLM call failed for section %s, using heuristic fallback",
            sid,
            exc_info=True,
        )
        composition = _heuristic_fallback(
            state,
            section,
            diagram_enabled=diagram_ok,
            interaction_enabled=interaction_ok,
            visual_mode=visual_mode,
        )
        diag(
            "COMPOSITION_PLAN_DIAGRAM",
            section_id=state.current_section_id,
            enabled=composition.diagram.enabled,
            mode=composition.diagram.mode,
            source="heuristic_fallback",
        )

    updated_usage = dict(state.interaction_usage)
    for interaction in composition.interactions:
        if interaction.enabled and interaction.interaction_type:
            itype = interaction.interaction_type
            updated_usage[itype] = updated_usage.get(itype, 0) + 1

    return {
        "composition_plans": {sid: composition},
        "interaction_usage": updated_usage,
        "completed_nodes": ["composition_planner"],
    }
