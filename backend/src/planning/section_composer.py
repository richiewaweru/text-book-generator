from __future__ import annotations

from uuid import uuid4

from planning.models import (
    NormalizedBrief,
    PlanningSectionPlan,
    PlanningSectionRole,
    PlanningTemplateContract,
    SectionGenerationNotes,
)

_ROLE_COMPONENT_FALLBACKS: dict[PlanningSectionRole, tuple[str, ...]] = {
    "intro": ("hook-hero", "callout-block", "key-fact"),
    "explain": ("explanation-block", "definition-card", "worked-example-card"),
    "practice": ("practice-stack", "student-textbox", "short-answer", "fill-in-blank"),
    "summary": ("summary-block", "what-next-bridge", "reflection-prompt"),
    "process": ("process-steps", "worked-example-card", "explanation-block"),
    "compare": ("comparison-grid", "definition-family", "insight-strip", "explanation-block"),
    "timeline": ("timeline-block", "reflection-prompt", "explanation-block"),
    "visual": ("diagram-block", "diagram-series", "diagram-compare", "explanation-block"),
    "discover": ("simulation-block", "diagram-block", "callout-block", "explanation-block"),
}

_ROLE_TITLE_STEMS: dict[PlanningSectionRole, str] = {
    "intro": "Start with the central idea",
    "explain": "Build the explanation",
    "practice": "Put the idea to work",
    "summary": "Close and connect forward",
    "process": "Walk through the method",
    "compare": "Keep the distinctions visible",
    "timeline": "Follow the sequence",
    "visual": "Let the visual lead",
    "discover": "Explore before formalising",
}


def _section_count(brief: NormalizedBrief, contract: PlanningTemplateContract) -> int:
    if brief.brief.constraints.keep_short:
        return 3

    count = 4
    if brief.scope_warning:
        count += 1
    if brief.brief.constraints.more_practice:
        count += 1
    if contract.intent in {"teach-procedure", "teach-sequence", "compare-ideas"}:
        count += 1
    return max(3, min(5, count))


def _role_sequence(
    contract: PlanningTemplateContract,
    count: int,
    more_practice: bool,
) -> list[PlanningSectionRole]:
    if contract.intent == "compare-ideas":
        core_role: PlanningSectionRole = "compare"
    elif contract.intent == "teach-sequence":
        core_role = "timeline"
    elif contract.intent == "teach-procedure":
        core_role = "process"
    elif "discover" in contract.section_role_defaults:
        core_role = "discover"
    elif contract.intent == "explain-visually":
        core_role = "visual"
    else:
        core_role = "explain"

    if count <= 3:
        return ["intro", core_role, "summary"]

    if count == 4:
        if core_role == "explain" or more_practice:
            return ["intro", core_role, "practice", "summary"]
        return ["intro", core_role, "explain", "summary"]

    if core_role == "explain":
        return ["intro", "explain", "explain", "practice", "summary"]
    return ["intro", core_role, "explain", "practice", "summary"]


def _role_components(
    contract: PlanningTemplateContract,
    role: PlanningSectionRole,
) -> list[str]:
    direct = contract.section_role_defaults.get(role)
    if direct:
        return direct[:]
    fallback = _ROLE_COMPONENT_FALLBACKS.get(role, ())
    pool = {*(contract.always_present or []), *(contract.available_components or [])}
    return [component for component in fallback if component in pool]


def _remaining_budget(contract: PlanningTemplateContract) -> dict[str, int | None]:
    available = {*(contract.always_present or []), *(contract.available_components or [])}
    return {
        component: contract.component_budget.get(component)
        for component in available
    }


def _select_components_for_role(
    contract: PlanningTemplateContract,
    role: PlanningSectionRole,
    remaining_budget: dict[str, int | None],
) -> list[str]:
    selected: list[str] = []
    per_section_counts: dict[str, int] = {}
    candidates = _role_components(contract, role)

    for component in candidates:
        if component not in contract.available_components and component not in contract.always_present:
            continue
        remaining = remaining_budget.get(component)
        if remaining is not None and remaining <= 0:
            continue
        limit = contract.max_per_section.get(component)
        if limit is not None and per_section_counts.get(component, 0) >= limit:
            continue
        selected.append(component)
        per_section_counts[component] = per_section_counts.get(component, 0) + 1
        if remaining is not None:
            remaining_budget[component] = remaining - 1

    return selected


def _placeholder_title(role: PlanningSectionRole, order: int) -> str:
    stem = _ROLE_TITLE_STEMS.get(role, f"Section {order}")
    return stem if len(stem.split()) <= 8 else f"{role.replace('-', ' ').title()} {order}"


def _objective(role: PlanningSectionRole, intent: str) -> str:
    mapping = {
        "intro": "Frame the lesson so the teacher and learners know what this section is trying to unlock.",
        "explain": "Build the core explanation with enough clarity for the target audience.",
        "practice": "Give the learner a chance to use the idea directly.",
        "summary": "Close the section arc and point toward what comes next.",
        "process": "Make the method feel sequential and repeatable.",
        "compare": "Keep distinctions visible so the learner can classify confidently.",
        "timeline": "Use chronology to show how one step leads to the next.",
        "visual": "Let the visual anchor lead the understanding before extra prose adds detail.",
        "discover": "Use guided exploration to reveal the pattern before formalising it.",
    }
    return mapping.get(role, f"Support the lesson's {intent} intent.")


def _generation_notes(role: PlanningSectionRole) -> SectionGenerationNotes | None:
    if role == "practice":
        return SectionGenerationNotes(brevity_override="tight")
    if role == "summary":
        return SectionGenerationNotes(
            brevity_override="tight",
            tone_override="clear and conclusive",
        )
    return None


def compose_sections(
    brief: NormalizedBrief,
    contract: PlanningTemplateContract,
) -> list[PlanningSectionPlan]:
    remaining_budget = _remaining_budget(contract)
    roles = _role_sequence(
        contract,
        _section_count(brief, contract),
        brief.brief.constraints.more_practice,
    )

    sections: list[PlanningSectionPlan] = []
    for index, role in enumerate(roles, start=1):
        sections.append(
            PlanningSectionPlan(
                id=f"section-{uuid4().hex[:8]}",
                order=index,
                role=role,
                title=_placeholder_title(role, index),
                objective=_objective(role, contract.intent),
                selected_components=_select_components_for_role(contract, role, remaining_budget),
                generation_notes=_generation_notes(role),
                rationale=f"This section uses the {role} role to support the chosen {contract.name} lesson shape.",
            )
        )

    return sections
