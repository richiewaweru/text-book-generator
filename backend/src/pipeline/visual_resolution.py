from __future__ import annotations

from typing import Literal

from pipeline.console_diagnostics import force_console_log
from pipeline.media.assembly import slot_is_ready
from pipeline.media.planner.media_planner import slot_render, slot_targets
from pipeline.state import TextbookPipelineState

VisualTarget = Literal["diagram", "diagram_series", "diagram_compare", "hook_svg"]
VisualMode = Literal["svg", "image"]

_VISUAL_COMPONENT_TO_TARGET: dict[str, VisualTarget] = {
    "diagram-block": "diagram",
    "diagram-series": "diagram_series",
    "diagram-compare": "diagram_compare",
}
_TARGET_TO_COMPONENT = {value: key for key, value in _VISUAL_COMPONENT_TO_TARGET.items()}
_IMAGE_PREFERRED_TARGETS: set[VisualTarget] = {"diagram_series", "diagram_compare"}


def _all_contract_components(state: TextbookPipelineState) -> set[str]:
    contract = state.contract
    return (
        set(getattr(contract, "required_components", []) or [])
        | set(getattr(contract, "optional_components", []) or [])
        | set(getattr(contract, "always_present", []) or [])
        | set(getattr(contract, "available_components", []) or [])
    )


def _dedupe(values: list[VisualTarget]) -> list[VisualTarget]:
    seen: set[VisualTarget] = set()
    ordered: list[VisualTarget] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _hook_svg_present(state: TextbookPipelineState) -> bool:
    section_id = state.current_section_id
    if section_id is None:
        return False
    section = state.generated_sections.get(section_id)
    if section is None or section.hook is None:
        return False
    return bool((section.hook.svg_content or "").strip())


def _preferred_fallback_target(state: TextbookPipelineState) -> VisualTarget | None:
    plan = state.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    all_components = _all_contract_components(state)

    if visual_policy is not None:
        if visual_policy.intent == "compare_variants" and "diagram-compare" in all_components:
            return "diagram_compare"
        if visual_policy.intent == "demonstrate_process" and "diagram-series" in all_components:
            return "diagram_series"

    if "diagram-block" in all_components:
        return "diagram"
    if "diagram-series" in all_components:
        return "diagram_series"
    if "diagram-compare" in all_components:
        return "diagram_compare"
    return None


def _contract_required_targets(state: TextbookPipelineState) -> list[VisualTarget]:
    contract = state.contract
    required_components = list(getattr(contract, "required_components", []) or [])
    always_present = list(getattr(contract, "always_present", []) or [])
    return _dedupe(
        [
            _VISUAL_COMPONENT_TO_TARGET[component_id]
            for component_id in [*required_components, *always_present]
            if component_id in _VISUAL_COMPONENT_TO_TARGET
        ]
    )


def resolve_visual_targets(state: TextbookPipelineState | dict) -> list[VisualTarget]:
    typed = TextbookPipelineState.parse(state)
    plan = typed.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    required_components = list(getattr(plan, "required_components", []) or [])
    diagram_policy = getattr(plan, "diagram_policy", None)

    explicit_targets = _dedupe(
        [
            _VISUAL_COMPONENT_TO_TARGET[component_id]
            for component_id in required_components
            if component_id in _VISUAL_COMPONENT_TO_TARGET and diagram_policy != "disabled"
        ]
    )
    if explicit_targets:
        force_console_log(
            "VISUAL_RESOLVE",
            "TARGETS",
            section_id=typed.current_section_id,
            source="required_components",
            targets=explicit_targets,
            required_components=required_components,
        )
        return explicit_targets

    contract_targets = _contract_required_targets(typed)
    if contract_targets and diagram_policy != "disabled":
        force_console_log(
            "VISUAL_RESOLVE",
            "TARGETS",
            section_id=typed.current_section_id,
            source="contract_required",
            targets=contract_targets,
        )
        return contract_targets

    if visual_policy is not None and visual_policy.required:
        if _hook_svg_present(typed) and getattr(visual_policy, "mode", None) != "image":
            force_console_log(
                "VISUAL_RESOLVE",
                "TARGETS",
                section_id=typed.current_section_id,
                source="hook_svg",
                targets=["hook_svg"],
            )
            return ["hook_svg"]

        fallback_target = _preferred_fallback_target(typed)
        if fallback_target is not None and diagram_policy != "disabled":
            force_console_log(
                "VISUAL_RESOLVE",
                "TARGETS",
                section_id=typed.current_section_id,
                source="visual_policy_required",
                targets=[fallback_target],
                visual_policy=visual_policy.model_dump(),
            )
            return [fallback_target]

    if getattr(plan, "needs_diagram", False) and diagram_policy != "disabled":
        fallback_target = _preferred_fallback_target(typed)
        if fallback_target is not None:
            force_console_log(
                "VISUAL_RESOLVE",
                "TARGETS",
                section_id=typed.current_section_id,
                source="needs_diagram",
                targets=[fallback_target],
            )
            return [fallback_target]

    force_console_log(
        "VISUAL_RESOLVE",
        "TARGETS",
        section_id=typed.current_section_id,
        source="none",
        targets=[],
    )
    return []


def resolve_visual_mode(state: TextbookPipelineState | dict) -> VisualMode | None:
    typed = TextbookPipelineState.parse(state)
    plan = typed.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    explicit_mode = getattr(visual_policy, "mode", None) if visual_policy is not None else None
    targets = resolve_visual_targets(typed)
    if not targets:
        return None
    if explicit_mode in {"svg", "image"}:
        force_console_log(
            "VISUAL_RESOLVE",
            "MODE",
            section_id=typed.current_section_id,
            source="visual_policy",
            mode=explicit_mode,
            targets=targets,
        )
        return explicit_mode
    resolved_mode: VisualMode = (
        "image" if any(target in _IMAGE_PREFERRED_TARGETS for target in targets) else "svg"
    )
    force_console_log(
        "VISUAL_RESOLVE",
        "MODE",
        section_id=typed.current_section_id,
        source="default",
        mode=resolved_mode,
        targets=targets,
    )
    return resolved_mode


def resolve_visual_issue(state: TextbookPipelineState | dict) -> str | None:
    typed = TextbookPipelineState.parse(state)
    plan = typed.current_section_plan
    visual_policy = getattr(plan, "visual_policy", None) if plan is not None else None
    needs_visual = bool(
        (plan is not None and getattr(plan, "needs_diagram", False))
        or (visual_policy is not None and visual_policy.required)
        or any(
            component_id in _VISUAL_COMPONENT_TO_TARGET
            for component_id in getattr(plan, "required_components", []) or []
        )
        or bool(_contract_required_targets(typed))
    )
    if not needs_visual:
        return None
    targets = resolve_visual_targets(typed)
    if targets:
        return None
    return (
        "No supported visual target could be resolved for this section. "
        "The template requires a visual, but no diagram field or inline hook SVG was available."
    )


def resolve_effective_visual_targets(state: TextbookPipelineState | dict) -> list[VisualTarget]:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    if section_id is not None:
        media_plan = typed.media_plans.get(section_id)
        media_targets = [
            target
            for target in slot_targets(media_plan)
            if target in {"diagram", "diagram_series", "diagram_compare"}
        ]
        if media_targets:
            force_console_log(
                "VISUAL_RESOLVE",
                "TARGETS",
                section_id=section_id,
                source="media_plan",
                targets=media_targets,
            )
            return media_targets  # type: ignore[return-value]
    if section_id is not None:
        plan = typed.composition_plans.get(section_id)
        required_targets = getattr(getattr(plan, "diagram", None), "required_targets", []) or []
        if required_targets:
            normalized = [target for target in required_targets if target in _TARGET_TO_COMPONENT or target == "hook_svg"]
            force_console_log(
                "VISUAL_RESOLVE",
                "TARGETS",
                section_id=section_id,
                source="composition_plan",
                targets=normalized,
            )
            return normalized  # type: ignore[return-value]
    return resolve_visual_targets(typed)


def resolve_effective_visual_mode(state: TextbookPipelineState | dict) -> VisualMode | None:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    if section_id is not None:
        media_plan = typed.media_plans.get(section_id)
        render = slot_render(media_plan)
        if render in {"svg", "image"}:
            force_console_log(
                "VISUAL_RESOLVE",
                "MODE",
                section_id=section_id,
                source="media_plan",
                mode=render,
            )
            return render  # type: ignore[return-value]
        plan = typed.composition_plans.get(section_id)
        mode = getattr(getattr(plan, "diagram", None), "mode", None)
        if mode in {"svg", "image"}:
            force_console_log(
                "VISUAL_RESOLVE",
                "MODE",
                section_id=section_id,
                source="composition_plan",
                mode=mode,
            )
            return mode
    return resolve_visual_mode(typed)


def target_is_satisfied(
    section,
    target: VisualTarget,
    *,
    mode: VisualMode | None = None,
) -> bool:
    if target == "hook_svg":
        return bool(section.hook and (section.hook.svg_content or "").strip())
    if target == "diagram":
        diagram = getattr(section, "diagram", None)
        if diagram is None:
            return False
        if mode == "image":
            return bool(diagram.image_url)
        return bool(diagram.spec or diagram.image_url or (diagram.svg_content or "").strip())
    if target == "diagram_series":
        series = getattr(section, "diagram_series", None)
        if series is None or not series.diagrams:
            return False
        if mode == "image":
            return all(bool(step.image_url) for step in series.diagrams)
        return all(bool((step.svg_content or "").strip() or step.image_url) for step in series.diagrams)
    if target == "diagram_compare":
        compare = getattr(section, "diagram_compare", None)
        if compare is None:
            return False
        if mode == "image":
            return bool(compare.before_image_url and compare.after_image_url)
        has_svg = bool((compare.before_svg or "").strip() and (compare.after_svg or "").strip())
        has_images = bool(compare.before_image_url and compare.after_image_url)
        return has_svg or has_images
    return False


def _media_target_ready(
    state: TextbookPipelineState,
    target: VisualTarget,
) -> bool | None:
    section_id = state.current_section_id
    if section_id is None:
        return None
    media_plan = state.media_plans.get(section_id)
    if media_plan is None:
        return None
    slot = next((candidate for candidate in media_plan.slots if candidate.slot_type.value == target), None)
    if slot is None:
        return None
    slot_result = state.media_slot_results.get(section_id, {}).get(slot.slot_id)
    if slot_result is not None:
        return slot_result.ready
    return slot_is_ready(slot, state.media_frame_results.get(section_id, {}).get(slot.slot_id))


def pending_visual_targets(state: TextbookPipelineState | dict) -> list[VisualTarget]:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    if section_id is None:
        return []
    section = typed.generated_sections.get(section_id)
    targets = resolve_effective_visual_targets(typed)
    mode = resolve_effective_visual_mode(typed)
    pending: list[VisualTarget] = []
    for target in targets:
        media_ready = _media_target_ready(typed, target)
        if media_ready is not None:
            if not media_ready:
                pending.append(target)
            continue
        if section is None:
            pending.append(target)
            continue
        if not target_is_satisfied(section, target, mode=mode):
            pending.append(target)
    force_console_log(
        "VISUAL_RESOLVE",
        "PENDING",
        section_id=section_id,
        mode=mode,
        targets=targets,
        pending=pending,
    )
    return pending


def required_visual_fields(state: TextbookPipelineState | dict) -> list[str]:
    return [
        target
        for target in resolve_effective_visual_targets(state)
        if target in {"diagram", "diagram_series", "diagram_compare"}
    ]


def pending_visual_fields(state: TextbookPipelineState | dict) -> list[str]:
    return list(pending_visual_targets(state))
