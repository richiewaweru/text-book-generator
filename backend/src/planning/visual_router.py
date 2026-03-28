from __future__ import annotations

from planning.models import (
    NormalizedBrief,
    PlanningSectionPlan,
    PlanningTemplateContract,
    PlanningVisualIntent,
    PlanningVisualMode,
    VisualPolicy,
)

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


def _classify_spatial(brief: NormalizedBrief) -> bool:
    return any(keyword in _SPATIAL_HINTS for keyword in brief.keyword_profile)


def _visual_intent(section: PlanningSectionPlan) -> PlanningVisualIntent:
    if section.role == "process":
        return "demonstrate_process"
    if section.role == "compare":
        return "compare_variants"
    if section.role in {"visual", "discover"}:
        return "show_realism"
    return "explain_structure"


def _visual_mode(brief: NormalizedBrief, intent: str) -> PlanningVisualMode:
    if brief.brief.constraints.print_first or brief.resolved_format == "printed-booklet":
        return "svg"
    if intent in {"show_realism", "demonstrate_process", "compare_variants"}:
        return "image"
    return "image" if _classify_spatial(brief) else "svg"


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
        if not should_visualize:
            continue

        intent = _visual_intent(section)
        mode = _visual_mode(brief, intent)
        section.visual_policy = VisualPolicy(
            required=True,
            intent=intent,
            mode=mode,
            goal={
                "demonstrate_process": "Show the sequence or method clearly enough that the learner can follow each step.",
                "compare_variants": "Put the alternatives in view so the learner can spot the difference that matters.",
                "show_realism": "Ground the section in a realistic visual anchor the learner can point at.",
                "explain_structure": "Show the important structure or relationship the section is describing.",
            }[intent],
            style_notes=(
                "Clean structural diagram, labeled nodes, clear arrows."
                if mode == "svg"
                else "Classroom-friendly educational image, accurate labels, no decorative clutter."
            ),
        )

    return sections
