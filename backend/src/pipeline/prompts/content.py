"""
Prompt builders for the content_generator node.

System prompt: fixed per template (required/optional fields, capacity, guidance).
User prompt: variable per section (plan, subject, grade, learner fit, rerender reason).
"""

from __future__ import annotations

from pipeline.contracts import (
    get_generation_guidance,
    get_lesson_flow,
    get_optional_fields,
    get_required_fields,
)
from pipeline.prompts.shared import capacity_reminder_for_fields, shared_context
from pipeline.types.requests import SectionPlan


_FIELD_FORMATTING_RULES = """\
## Field formatting rules

- Body fields (explanation, hook, what_next, pitfall correction): prose only.
  Use **bold** for key terms, *italic* for emphasis, `code` for inline notation in prose.
  Use blank lines for paragraph breaks. Use --- for thematic breaks in explanation only.
  Never use # headers or bullet lists inside body fields.

- The `notation` field on DefinitionContent is LaTeX only.
  If you cannot write valid LaTeX for the notation, omit the field entirely.
  Plain English belongs in `examples`, not `notation`.

- `emphasis` arrays contain plain strings — no markdown syntax inside them.

- Short label fields (term, next, misconception, action): plain text, no markdown."""


def _section_plan_policy_block(section_plan: SectionPlan) -> str:
    continuity = section_plan.continuity_notes or "none"
    required_components = ", ".join(section_plan.required_components) or "none"
    optional_components = ", ".join(section_plan.optional_components) or "none"
    return f"""Planning policy:
  role: {section_plan.role}
  required_components: {required_components}
  optional_components: {optional_components}
  interaction_policy: {section_plan.interaction_policy}
  diagram_policy: {section_plan.diagram_policy}
  enrichment_enabled: {section_plan.enrichment_enabled}
  continuity_notes: {continuity}"""


def build_content_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    guidance = get_generation_guidance(template_id)
    lesson_flow = " -> ".join(get_lesson_flow(template_id))
    required = get_required_fields(template_id)
    optional = get_optional_fields(template_id)

    return f"""You generate content for one section of an educational textbook.
You fill structured JSON slots. You do not make layout decisions.

{shared_context(template_name, template_family, '', '', '')}
Lesson flow: {lesson_flow}

Tone: {guidance['tone']}
Pacing: {guidance['pacing']}
Chunking: {guidance['chunking']}
Emphasis: {guidance['emphasis']}
Avoid: {', '.join(guidance['avoid'])}

Required fields (must always be present):
{chr(10).join(f'  - {f}' for f in required)}

Optional fields (include only when content genuinely warrants it):
{chr(10).join(f'  - {f}' for f in optional)}

{capacity_reminder_for_fields(required + optional)}

{_FIELD_FORMATTING_RULES}

Output a single SectionContent JSON object.
Every field name must match the schema exactly (snake_case).
Do not invent field names. Do not omit required fields.
Output only valid JSON. No preamble, no markdown fences."""


def build_content_user_prompt(
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
    rerender_reason: str | None = None,
) -> str:
    base = f"""Section to generate:
  section_id: {section_plan.section_id}
  template_id: {template_id}
  title: {section_plan.title}
  position: {section_plan.position}
  focus: {section_plan.focus}
  bridges_from: {section_plan.bridges_from or 'none -- this is the first section'}
  bridges_to: {section_plan.bridges_to or 'none -- this is the last section'}
  needs_diagram: {section_plan.needs_diagram}
  needs_worked_example: {section_plan.needs_worked_example}

Subject: {subject}
Context: {context}
Grade level: {grade_band}
Learner type: {learner_fit}

{_section_plan_policy_block(section_plan)}"""

    if rerender_reason:
        base += f"""

This is a RERENDER. The previous version had this problem:
  {rerender_reason}

Fix only the affected content. Keep everything else the same quality."""

    return base


def build_content_repair_user_prompt(
    *,
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
    validation_summary: str,
    validation_errors: list[dict[str, str]] = (),
    rerender_reason: str | None = None,
) -> str:
    if validation_errors:
        error_lines = "\n".join(
            f"  - Field `{e['field']}`: {e['message']}"
            for e in validation_errors
        )
        error_block = (
            "Fix ONLY these specific fields while keeping all other content intact:\n"
            f"{error_lines}"
        )
    else:
        error_block = f"Validation summary:\n{validation_summary}"

    return f"""Your previous response had schema validation issues.
{error_block}

Keep the teaching intent, examples, and progression aligned with the requested section.
Match the SectionContent schema exactly.

{build_content_user_prompt(
    section_plan=section_plan,
    subject=subject,
    context=context,
    grade_band=grade_band,
    learner_fit=learner_fit,
    template_id=template_id,
    rerender_reason=rerender_reason,
)}"""


# Fields belonging to each generation phase.
CORE_FIELDS = {"header", "hook", "explanation"}
PRACTICE_FIELDS = {"practice", "what_next", "pitfall", "pitfalls", "prerequisites"}
ENRICHMENT_FIELDS = {
    "worked_example",
    "worked_examples",
    "process",
    "definition",
    "definition_family",
    "quiz",
    "reflection",
    "glossary",
    "comparison_grid",
    "timeline",
    "insight_strip",
    "interview",
}
# Diagram and simulation fields are handled by dedicated nodes, not content phases.
_EXTERNAL_FIELDS = {"diagram", "diagram_compare", "diagram_series", "simulation"}


def _phase_system_prompt(
    *,
    template_id: str,
    template_name: str,
    template_family: str,
    phase_name: str,
    phase_fields: set[str],
) -> str:
    """Build a system prompt scoped to one content phase."""
    guidance = get_generation_guidance(template_id)
    required = get_required_fields(template_id)
    optional = get_optional_fields(template_id)

    active_required = [f for f in required if f in phase_fields]
    active_optional = [f for f in optional if f in phase_fields]
    active_fields = active_required + active_optional

    req_block = (
        "Required fields:\n" + "\n".join(f"  - {f}" for f in active_required)
        if active_required
        else ""
    )
    opt_block = (
        "Optional fields (include only when warranted):\n"
        + "\n".join(f"  - {f}" for f in active_optional)
        if active_optional
        else ""
    )

    return f"""You generate the {phase_name} phase of an educational textbook section.
You fill structured JSON slots. You do not make layout decisions.

{shared_context(template_name, template_family, '', '', '')}

Tone: {guidance['tone']}
Pacing: {guidance['pacing']}

{req_block}
{opt_block}

{capacity_reminder_for_fields(active_fields)}

{_FIELD_FORMATTING_RULES}

Output valid JSON matching the schema exactly. No preamble, no markdown fences."""


def build_core_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    return _phase_system_prompt(
        template_id=template_id,
        template_name=template_name,
        template_family=template_family,
        phase_name="core",
        phase_fields=CORE_FIELDS,
    )


def build_practice_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    return _phase_system_prompt(
        template_id=template_id,
        template_name=template_name,
        template_family=template_family,
        phase_name="practice",
        phase_fields=PRACTICE_FIELDS,
    )


def build_enrichment_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    return _phase_system_prompt(
        template_id=template_id,
        template_name=template_name,
        template_family=template_family,
        phase_name="enrichment",
        phase_fields=ENRICHMENT_FIELDS,
    )


def build_core_user_prompt(
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
    rerender_reason: str | None = None,
) -> str:
    """User prompt for Phase 1: header + hook + explanation."""
    base = f"""Generate the CORE content for this section (header, hook, explanation).

Section:
  section_id: {section_plan.section_id}
  template_id: {template_id}
  title: {section_plan.title}
  position: {section_plan.position}
  focus: {section_plan.focus}
  bridges_from: {section_plan.bridges_from or 'none -- first section'}
  bridges_to: {section_plan.bridges_to or 'none -- last section'}

Subject: {subject}
Context: {context}
Grade level: {grade_band}
Learner type: {learner_fit}

{_section_plan_policy_block(section_plan)}"""

    if rerender_reason:
        base += f"\n\nRERENDER - fix this problem: {rerender_reason}"

    return base


def build_practice_user_prompt(
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
    core_summary: str,
    rerender_reason: str | None = None,
) -> str:
    """User prompt for Phase 2: practice + what_next + optional pitfall/prerequisites."""
    return f"""Generate the PRACTICE content for this section.

Section: {section_plan.title} (position {section_plan.position})
Focus: {section_plan.focus}
Subject: {subject}
Context: {context}
Grade level: {grade_band}
Learner type: {learner_fit}
{_section_plan_policy_block(section_plan)}

Core content already generated:
{core_summary}

Generate practice problems, what_next bridge, and any applicable pitfall/prerequisites.
{f"RERENDER - fix: {rerender_reason}" if rerender_reason else ""}"""


def build_enrichment_user_prompt(
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
    core_summary: str,
    active_enrichment_fields: list[str],
    rerender_reason: str | None = None,
) -> str:
    """User prompt for Phase 3: optional enrichment components."""
    fields_block = ", ".join(active_enrichment_fields)
    return f"""Generate ENRICHMENT content for this section.

Section: {section_plan.title} (position {section_plan.position})
Focus: {section_plan.focus}
Subject: {subject}
Context: {context}
Grade level: {grade_band}
Learner type: {learner_fit}
{_section_plan_policy_block(section_plan)}

Core content already generated:
{core_summary}

Generate these enrichment fields: {fields_block}
Include only fields that genuinely add value. Omit any that feel forced.
{f"RERENDER - fix: {rerender_reason}" if rerender_reason else ""}"""
