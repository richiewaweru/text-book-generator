from __future__ import annotations

from typing import Literal

from pipeline.console_diagnostics import force_console_log
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


def pending_visual_targets(state: TextbookPipelineState | dict) -> list[VisualTarget]:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    if section_id is None:
        return []
    section = typed.generated_sections.get(section_id)
    if section is None:
        return []
    targets = resolve_effective_visual_targets(typed)
    mode = resolve_effective_visual_mode(typed)
    pending = [target for target in targets if not target_is_satisfied(section, target, mode=mode)]
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
