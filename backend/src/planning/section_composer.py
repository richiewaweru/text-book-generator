from __future__ import annotations

from uuid import uuid4

from planning.models import (
    NormalizedBrief,
    PlanningSectionPlan,
    PlanningSectionRole,
    PlanningTemplateContract,
    SectionGenerationNotes,
)


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
        base: list[PlanningSectionRole] = ["intro", "compare", "explain", "practice", "summary"]
    elif contract.intent == "teach-sequence":
        base = ["intro", "timeline", "explain", "practice", "summary"]
    elif contract.intent == "teach-procedure":
        base = ["intro", "process", "explain", "practice", "summary"]
    elif "discover" in contract.section_role_defaults:
        base = ["intro", "discover", "explain", "practice", "summary"]
    elif contract.intent == "explain-visually":
        base = ["intro", "visual", "explain", "practice", "summary"]
    else:
        base = ["intro", "explain", "practice", "summary"]

    if count <= len(base):
        roles = base[:count]
    else:
        roles = list(base)
        while len(roles) < count:
            roles.insert(-2, "explain")

    if more_practice and "practice" not in roles:
        roles.insert(-1, "practice")
    return roles[:count]


def _role_components(
    contract: PlanningTemplateContract,
    role: PlanningSectionRole,
) -> list[str]:
    direct = contract.section_role_defaults.get(role)
    if direct:
        return direct[:]
    if role in {"visual", "discover"} and "explain" in contract.section_role_defaults:
        return contract.section_role_defaults["explain"][:]
    if role == "summary" and contract.always_present:
        return [
            component
            for component in contract.always_present
            if component in {"what-next-bridge", "summary-block"}
        ]
    return []


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
                title=f"{role.replace('-', ' ').title()} {index}",
                objective=_objective(role, contract.intent),
                selected_components=_role_components(contract, role),
                generation_notes=_generation_notes(role),
                rationale=f"This section uses the {role} role to support the chosen {contract.name} lesson shape.",
            )
        )

    return sections
