from __future__ import annotations

from typing import Iterable

from pipeline.media.types import (
    MediaPlan,
    ReferenceStyle,
    SlotType,
    VisualFrame,
    VisualRender,
    VisualSlot,
)
from pipeline.state import StyleContext
from pipeline.types.requests import SectionPlan
from pipeline.types.section_content import SectionContent
from pipeline.types.template_contract import TemplateContractSummary

_DIAGRAM_COMPONENTS: dict[str, SlotType] = {
    "diagram-block": SlotType.DIAGRAM,
    "diagram-series": SlotType.DIAGRAM_SERIES,
    "diagram-compare": SlotType.DIAGRAM_COMPARE,
}


def _all_contract_components(contract: TemplateContractSummary) -> set[str]:
    return (
        set(getattr(contract, "required_components", []) or [])
        | set(getattr(contract, "optional_components", []) or [])
        | set(getattr(contract, "always_present", []) or [])
        | set(getattr(contract, "available_components", []) or [])
    )


def _slot_id(slot_type: SlotType) -> str:
    return slot_type.value


def _visual_policy(plan: SectionPlan):
    return getattr(plan, "visual_policy", None)


def _explicit_slot_type(plan: SectionPlan) -> SlotType | None:
    visual_policy = _visual_policy(plan)
    raw_target = getattr(visual_policy, "target", None)
    if raw_target is not None:
        return SlotType(raw_target)
    return None


def _fallback_slot_type(
    plan: SectionPlan,
    *,
    contract: TemplateContractSummary,
) -> SlotType | None:
    visual_policy = _visual_policy(plan)
    raw_target = getattr(visual_policy, "fallback_target", None)
    if raw_target is not None:
        return SlotType(raw_target)

    components = _all_contract_components(contract)
    if visual_policy is not None and getattr(visual_policy, "intent", None) == "compare_variants":
        if "diagram-compare" in components:
            return SlotType.DIAGRAM_COMPARE
    if visual_policy is not None and getattr(visual_policy, "intent", None) == "demonstrate_process":
        if "diagram-series" in components:
            return SlotType.DIAGRAM_SERIES

    if "diagram-block" in components:
        return SlotType.DIAGRAM
    if "diagram-series" in components:
        return SlotType.DIAGRAM_SERIES
    if "diagram-compare" in components:
        return SlotType.DIAGRAM_COMPARE
    return None


def _required_slot_types(
    plan: SectionPlan,
    *,
    contract: TemplateContractSummary,
) -> list[SlotType]:
    if plan.diagram_policy == "disabled":
        return []

    types: list[SlotType] = []
    explicit_slot = _explicit_slot_type(plan)
    if explicit_slot is not None:
        types.append(explicit_slot)

    for component_id in getattr(plan, "required_components", []) or []:
        slot_type = _DIAGRAM_COMPONENTS.get(component_id)
        if slot_type is not None:
            types.append(slot_type)

    for component_id in list(getattr(contract, "required_components", []) or []) + list(
        getattr(contract, "always_present", []) or []
    ):
        slot_type = _DIAGRAM_COMPONENTS.get(component_id)
        if slot_type is not None:
            types.append(slot_type)

    visual_policy = _visual_policy(plan)
    if visual_policy is not None and getattr(visual_policy, "required", False):
        fallback = _fallback_slot_type(plan, contract=contract)
        if fallback is not None:
            types.append(fallback)

    if plan.needs_diagram:
        fallback = _fallback_slot_type(plan, contract=contract)
        if fallback is not None:
            types.append(fallback)

    ordered: list[SlotType] = []
    for slot_type in types:
        if slot_type not in ordered:
            ordered.append(slot_type)
    return ordered


def _simulation_allowed(plan: SectionPlan, contract: TemplateContractSummary) -> bool:
    if plan.interaction_policy == "disabled":
        return False
    return "simulation-block" in _all_contract_components(contract)


def _preferred_render_for_slot(
    plan: SectionPlan,
    slot_type: SlotType,
) -> VisualRender:
    visual_policy = _visual_policy(plan)
    explicit_render = getattr(visual_policy, "preferred_render", None) or getattr(
        visual_policy, "mode", None
    )
    if explicit_render is not None:
        return VisualRender(explicit_render)
    if slot_type == SlotType.SIMULATION:
        return VisualRender.HTML_SIMULATION
    if slot_type in {SlotType.DIAGRAM_COMPARE, SlotType.DIAGRAM_SERIES}:
        return VisualRender.IMAGE
    return VisualRender.SVG


def _fallback_render_for_slot(slot_type: SlotType, preferred_render: VisualRender) -> VisualRender | None:
    if preferred_render == VisualRender.IMAGE:
        return VisualRender.SVG
    if preferred_render == VisualRender.HTML_SIMULATION:
        return VisualRender.SVG
    if preferred_render == VisualRender.SVG and slot_type == SlotType.SIMULATION:
        return VisualRender.HTML_SIMULATION
    return None


def _reference_style(slot_type: SlotType) -> ReferenceStyle:
    if slot_type == SlotType.DIAGRAM_COMPARE:
        return ReferenceStyle.LOCKED_COMPARISON
    if slot_type == SlotType.DIAGRAM_SERIES:
        return ReferenceStyle.CONSISTENT_SEQUENCE
    if slot_type == SlotType.SIMULATION:
        return ReferenceStyle.INTERACTIVE
    return ReferenceStyle.STANDARD


def _key_concepts(section: SectionContent) -> list[str]:
    concepts: list[str] = []
    if section.definition is not None:
        concepts.append(section.definition.term)
    concepts.extend(section.explanation.emphasis[:3])
    if section.process is not None:
        concepts.extend(step.action for step in section.process.steps[:3])
    return [concept for concept in concepts if concept]


def _pedagogical_intent(plan: SectionPlan) -> str:
    visual_policy = _visual_policy(plan)
    return (
        getattr(visual_policy, "goal", None)
        or plan.focus
        or "Make the core concept visually clear."
    )


def _base_avoid_list(preferred_render: VisualRender) -> list[str]:
    avoid = ["text overlays"]
    if preferred_render == VisualRender.IMAGE:
        avoid.append("photoreal clutter")
    return avoid


def _single_caption(section: SectionContent, plan: SectionPlan) -> str:
    if section.diagram is not None:
        return section.diagram.caption
    return f"Visual explanation for {section.header.title}."


def _series_caption(section: SectionContent) -> str:
    if section.diagram_series is not None and section.diagram_series.diagrams:
        return section.diagram_series.diagrams[0].caption
    return f"Step-by-step sequence for {section.header.title}."


def _compare_caption(section: SectionContent) -> str:
    if section.diagram_compare is not None:
        return section.diagram_compare.caption
    return f"Before and after comparison for {section.header.title}."


def _series_labels(section: SectionContent, concepts: list[str]) -> list[str]:
    if section.diagram_series is not None and section.diagram_series.diagrams:
        return [step.step_label for step in section.diagram_series.diagrams]
    if section.process is not None and section.process.steps:
        return [step.action for step in section.process.steps[:4]]
    if concepts:
        return concepts[:4]
    return [section.header.title, "Key step 2", "Key step 3"]


def _compare_labels(section: SectionContent) -> tuple[str, str]:
    if section.comparison_grid is not None and len(section.comparison_grid.columns) >= 2:
        return (
            section.comparison_grid.columns[0].title.strip() or "Before",
            section.comparison_grid.columns[1].title.strip() or "After",
        )
    if section.diagram_compare is not None:
        return (
            section.diagram_compare.before_label.strip() or "Before",
            section.diagram_compare.after_label.strip() or "After",
        )
    return "Before", "After"


def _frame_output_placeholders(preferred_render: VisualRender, slot_type: SlotType) -> dict[str, str | None]:
    if slot_type == SlotType.SIMULATION:
        return {"html_content": None, "fallback_diagram": None}
    if preferred_render == VisualRender.IMAGE:
        return {"image_url": None}
    return {"svg_content": None}


def _simulation_type(section: SectionContent, plan: SectionPlan) -> str:
    visual_policy = _visual_policy(plan)
    intent = getattr(visual_policy, "simulation_intent", None) or plan.practice_target or ""
    lowered = intent.lower()
    if section.timeline is not None or plan.role == "timeline":
        return "timeline_scrubber"
    if "probability" in lowered or "tree" in lowered:
        return "probability_tree"
    if "equation" in lowered or "algebra" in lowered:
        return "equation_reveal"
    if "geometry" in lowered:
        return "geometry_explorer"
    if "molecule" in lowered or "chem" in lowered:
        return "molecule_viewer"
    return "graph_slider"


def _simulation_print_translation(plan: SectionPlan, contract: TemplateContractSummary) -> str:
    visual_policy = _visual_policy(plan)
    if visual_policy is not None and getattr(visual_policy, "fallback_target", None) == "simulation":
        return "hide"
    if "diagram-block" in _all_contract_components(contract):
        return "static_diagram"
    return "hide"


def _build_single_slot(
    *,
    section: SectionContent,
    plan: SectionPlan,
    slot_type: SlotType,
) -> VisualSlot:
    preferred_render = _preferred_render_for_slot(plan, slot_type)
    concepts = _key_concepts(section)
    frame = VisualFrame(
        slot_id=_slot_id(slot_type),
        index=0,
        label=section.header.title,
        generation_goal=f"Show the core idea of {section.header.title} clearly for learners.",
        must_include=concepts[:4],
        avoid=_base_avoid_list(preferred_render),
        output_placeholders=_frame_output_placeholders(preferred_render, slot_type),
    )
    return VisualSlot(
        slot_id=_slot_id(slot_type),
        slot_type=slot_type,
        required=True,
        preferred_render=preferred_render,
        fallback_render=_fallback_render_for_slot(slot_type, preferred_render),
        pedagogical_intent=_pedagogical_intent(plan),
        caption=_single_caption(section, plan),
        reference_style=_reference_style(slot_type),
        frames=[frame],
    )


def _build_series_slot(section: SectionContent, plan: SectionPlan) -> VisualSlot:
    preferred_render = _preferred_render_for_slot(plan, SlotType.DIAGRAM_SERIES)
    concepts = _key_concepts(section)
    labels = _series_labels(section, concepts)
    frames = [
        VisualFrame(
            slot_id=_slot_id(SlotType.DIAGRAM_SERIES),
            index=index,
            label=label,
            generation_goal=f"Show sequence step {index + 1} for {section.header.title}: {label}.",
            must_include=[label] + ([concepts[index]] if index < len(concepts) else []),
            avoid=_base_avoid_list(preferred_render),
            output_placeholders=_frame_output_placeholders(preferred_render, SlotType.DIAGRAM_SERIES),
        )
        for index, label in enumerate(labels)
    ]
    return VisualSlot(
        slot_id=_slot_id(SlotType.DIAGRAM_SERIES),
        slot_type=SlotType.DIAGRAM_SERIES,
        required=True,
        preferred_render=preferred_render,
        fallback_render=_fallback_render_for_slot(SlotType.DIAGRAM_SERIES, preferred_render),
        pedagogical_intent=_pedagogical_intent(plan),
        caption=_series_caption(section),
        reference_style=_reference_style(SlotType.DIAGRAM_SERIES),
        frames=frames,
        series_context=section.header.title,
    )


def _build_compare_slot(section: SectionContent, plan: SectionPlan) -> VisualSlot:
    preferred_render = _preferred_render_for_slot(plan, SlotType.DIAGRAM_COMPARE)
    before_label, after_label = _compare_labels(section)
    frames = [
        VisualFrame(
            slot_id=_slot_id(SlotType.DIAGRAM_COMPARE),
            index=0,
            label=before_label,
            generation_goal=f"Render the before state for {section.header.title}.",
            must_include=[before_label],
            avoid=_base_avoid_list(preferred_render),
            output_placeholders=_frame_output_placeholders(preferred_render, SlotType.DIAGRAM_COMPARE),
        ),
        VisualFrame(
            slot_id=_slot_id(SlotType.DIAGRAM_COMPARE),
            index=1,
            label=after_label,
            generation_goal=f"Render the after state for {section.header.title}.",
            must_include=[after_label],
            avoid=_base_avoid_list(preferred_render),
            output_placeholders=_frame_output_placeholders(preferred_render, SlotType.DIAGRAM_COMPARE),
        ),
    ]
    return VisualSlot(
        slot_id=_slot_id(SlotType.DIAGRAM_COMPARE),
        slot_type=SlotType.DIAGRAM_COMPARE,
        required=True,
        preferred_render=preferred_render,
        fallback_render=_fallback_render_for_slot(SlotType.DIAGRAM_COMPARE, preferred_render),
        pedagogical_intent=_pedagogical_intent(plan),
        caption=_compare_caption(section),
        reference_style=_reference_style(SlotType.DIAGRAM_COMPARE),
        frames=frames,
    )


def _build_simulation_slot(section: SectionContent, plan: SectionPlan) -> VisualSlot:
    visual_policy = _visual_policy(plan)
    preferred_render = _preferred_render_for_slot(plan, SlotType.SIMULATION)
    simulation_intent = getattr(visual_policy, "simulation_intent", None) or plan.practice_target
    frame = VisualFrame(
        slot_id=_slot_id(SlotType.SIMULATION),
        index=0,
        label=section.header.title,
        generation_goal=f"Represent an interactive view for {section.header.title}.",
        must_include=_key_concepts(section)[:4],
        avoid=["unexplained controls"],
        output_placeholders=_frame_output_placeholders(preferred_render, SlotType.SIMULATION),
    )
    return VisualSlot(
        slot_id=_slot_id(SlotType.SIMULATION),
        slot_type=SlotType.SIMULATION,
        required=plan.interaction_policy == "required",
        preferred_render=preferred_render,
        fallback_render=_fallback_render_for_slot(SlotType.SIMULATION, preferred_render),
        pedagogical_intent=_pedagogical_intent(plan),
        caption=f"Interactive exploration for {section.header.title}.",
        reference_style=_reference_style(SlotType.SIMULATION),
        frames=[frame],
        simulation_intent=simulation_intent,
        simulation_type=_simulation_type(section, plan),
        simulation_goal=simulation_intent or _pedagogical_intent(plan),
        anchor_block="explanation",
        print_translation="static_diagram",
        expects_static_fallback=False,
    )


def media_planner(
    *,
    section_plan: SectionPlan,
    section_content: SectionContent,
    template_contract: TemplateContractSummary,
    style_context: StyleContext | None,
) -> MediaPlan:
    _ = style_context
    slots: list[VisualSlot] = []
    notes: list[str] = []

    for slot_type in _required_slot_types(section_plan, contract=template_contract):
        if slot_type == SlotType.DIAGRAM_SERIES:
            slots.append(_build_series_slot(section_content, section_plan))
        elif slot_type == SlotType.DIAGRAM_COMPARE:
            slots.append(_build_compare_slot(section_content, section_plan))
        else:
            slots.append(
                _build_single_slot(
                    section=section_content,
                    plan=section_plan,
                    slot_type=slot_type,
                )
            )

    if _simulation_allowed(section_plan, template_contract):
        simulation_slot = _build_simulation_slot(section_content, section_plan)
        simulation_slot.print_translation = _simulation_print_translation(
            section_plan,
            template_contract,
        )
        simulation_slot.expects_static_fallback = simulation_slot.print_translation == "static_diagram"
        slots.append(simulation_slot)
        notes.append("Simulation slot planned for executor-backed HTML generation.")

    if not slots:
        notes.append("No media slots resolved for this section.")

    return MediaPlan(
        section_id=section_plan.section_id,
        slots=slots,
        planner_notes=notes,
    )


def find_slot(media_plan: MediaPlan | None, slot_type: SlotType) -> VisualSlot | None:
    if media_plan is None:
        return None
    return next((slot for slot in media_plan.slots if slot.slot_type == slot_type), None)


def visual_slots(media_plan: MediaPlan | None) -> Iterable[VisualSlot]:
    if media_plan is None:
        return ()
    return (
        slot
        for slot in media_plan.slots
        if slot.slot_type in {SlotType.DIAGRAM, SlotType.DIAGRAM_COMPARE, SlotType.DIAGRAM_SERIES}
    )


def slot_targets(media_plan: MediaPlan | None) -> list[str]:
    if media_plan is None:
        return []
    ordered: list[str] = []
    for slot in visual_slots(media_plan):
        target = slot.slot_type.value
        if target not in ordered and slot.required:
            ordered.append(target)
    return ordered


def slot_render(media_plan: MediaPlan | None) -> str | None:
    if media_plan is None:
        return None
    for slot in visual_slots(media_plan):
        if slot.required:
            render = slot.preferred_render.value
            if render in {"svg", "image"}:
                return render
    return None
