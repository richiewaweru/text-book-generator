from __future__ import annotations

from planning.models import (
    NormalizedBrief,
    PlanningSectionPlan,
    PlanningTemplateContract,
    PlanningVisualIntent,
    PlanningVisualMode,
    VisualPolicy,
)
from pipeline.types.requests import BlockVisualPlacement

_SPATIAL_HINTS = {
    "biology",
    "chemistry",
    "ecosystem",
    "cell",
    "atom",
    "heart",
    "anatomy",
    "river",
    "map",
    "planet",
    "cycle",
    "photosynthesis",
    "geography",
    "architecture",
    "geology",
    "organ",
    "molecule",
    "skeleton",
    "volcano",
    "ocean",
    "continent",
    "mountain",
    "weather",
    "circuit",
    "engine",
    "building",
    "bridge",
    "solar",
    "galaxy",
}

_GRAPH_HINTS = {
    "graph",
    "plot",
    "axes",
    "axis",
    "coordinate",
    "gradient",
    "slope",
    "derivative",
    "integral",
    "function",
    "equation",
    "curve",
    "tangent",
    "linear",
    "quadratic",
    "parabola",
    "intercept",
    "asymptote",
    "vector",
    "force",
    "velocity",
    "acceleration",
    "displacement",
    "distance",
    "frequency",
    "wavelength",
    "amplitude",
    "probability",
    "distribution",
    "histogram",
    "scatter",
    "correlation",
    "regression",
    "demand",
    "supply",
    "elasticity",
    "marginal",
    "revenue",
    "cost",
    "profit",
}


def _classify_spatial(brief: NormalizedBrief) -> bool:
    return any(keyword in _SPATIAL_HINTS for keyword in brief.keyword_profile)


def _classify_graph(brief: NormalizedBrief) -> bool:
    return any(keyword in _GRAPH_HINTS for keyword in brief.keyword_profile)


def _visual_intent(section: PlanningSectionPlan) -> PlanningVisualIntent:
    if section.role == "process":
        return "demonstrate_process"
    if section.role == "compare":
        return "compare_variants"
    if section.role in {"visual", "discover"}:
        return "show_realism"
    return "explain_structure"


def _visual_mode(brief: NormalizedBrief, intent: str) -> PlanningVisualMode:
    if intent in {"show_realism", "demonstrate_process", "compare_variants"}:
        return "image"
    if _classify_spatial(brief):
        return "image"
    if _classify_graph(brief):
        return "image"
    return "svg"


def _derive_visual_placements(
    *,
    section: PlanningSectionPlan,
    contract: PlanningTemplateContract,
    intent: PlanningVisualIntent,
    should_visualize: bool,
) -> list[BlockVisualPlacement]:
    if not should_visualize:
        return []

    available = set(contract.available_components)
    selected = set(section.selected_components)

    if "diagram-compare" in selected or (
        intent == "compare_variants" and "diagram-compare" in available
    ):
        return [
            BlockVisualPlacement(
                block="explanation",
                slot_type="diagram_compare",
                hint="Use an explanation-adjacent comparison visual.",
            )
        ]

    if "diagram-series" in selected or (
        intent == "demonstrate_process" and "diagram-series" in available
    ):
        return [
            BlockVisualPlacement(
                block="explanation",
                slot_type="diagram_series",
                hint="Use an explanation-adjacent sequence visual.",
            )
        ]

    if "diagram-block" in selected or "diagram-block" in available:
        return [
            BlockVisualPlacement(
                block="explanation",
                slot_type="diagram",
                hint="Use an explanation-adjacent diagram.",
            )
        ]

    return []


def route_visuals(
    brief: NormalizedBrief,
    contract: PlanningTemplateContract,
    sections: list[PlanningSectionPlan],
) -> list[PlanningSectionPlan]:
    visual_components = {"diagram-block", "diagram-series", "diagram-compare", "simulation-block"}
    visual_supported = visual_components.intersection(contract.available_components)

    for section in sections:
        should_visualize = bool(
            visual_supported
            and (
                set(section.selected_components).intersection(visual_components)
                or brief.brief.constraints.use_visuals
                or section.role in {"visual", "process", "compare", "discover"}
            )
        )
        intent = _visual_intent(section)
        mode = _visual_mode(brief, intent)
        placements = _derive_visual_placements(
            section=section,
            contract=contract,
            intent=intent,
            should_visualize=should_visualize,
        )
        section.visual_placements = placements
        section.visual_policy = VisualPolicy(
            required=bool(placements),
            intent=intent if placements else None,
            mode=mode if placements else None,
            goal={
                "demonstrate_process": "Show the sequence or method clearly enough that the learner can follow each step.",
                "compare_variants": "Put the alternatives in view so the learner can spot the difference that matters.",
                "show_realism": "Ground the section in a realistic visual anchor the learner can point at.",
                "explain_structure": "Show the important structure or relationship the section is describing.",
            }[intent]
            if placements
            else None,
            style_notes=(
                "Clean structural diagram, labeled nodes, clear arrows."
                if mode == "svg"
                else "Classroom-friendly educational image, accurate labels, no decorative clutter."
            )
            if placements
            else None,
        )

    return sections
