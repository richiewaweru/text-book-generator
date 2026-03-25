"""
Prompt builders for the content_generator node.

System prompt: fixed per template (required/optional fields, capacity, guidance).
User prompt: variable per section (plan, subject, grade, learner fit, rerender reason).
"""

from __future__ import annotations

import json

from pipeline.contracts import (
    get_required_fields,
    get_optional_fields,
    get_generation_guidance,
    get_lesson_flow,
)
from pipeline.prompts.shared import shared_context, capacity_reminder_for_fields
from pipeline.types.section_content import SectionContent
from pipeline.types.requests import SectionPlan


def build_content_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    guidance = get_generation_guidance(template_id)
    lesson_flow = " \u2192 ".join(get_lesson_flow(template_id))
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
    seed_section: SectionContent | None = None,
    seed_note: str | None = None,
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
Learner type: {learner_fit}"""

    if seed_section is not None:
        base += f"""

Use this prior draft section as seed material. Keep the same section_id and overall teaching intent,
but improve clarity, correctness, pacing, and completeness for the requested mode:

{json.dumps(seed_section.model_dump(exclude_none=True), indent=2)}"""

    if seed_note:
        base += f"""

Enhancement note:
  {seed_note}"""

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
    rerender_reason: str | None = None,
    seed_section: SectionContent | None = None,
    seed_note: str | None = None,
) -> str:
    return f"""Your previous response had schema validation issues.
Fix only the structure so it matches the SectionContent schema exactly.
Keep the teaching intent, examples, and progression aligned with the requested section.

Validation summary:
{validation_summary}

{build_content_user_prompt(
    section_plan=section_plan,
    subject=subject,
    context=context,
    grade_band=grade_band,
    learner_fit=learner_fit,
    template_id=template_id,
    rerender_reason=rerender_reason,
    seed_section=seed_section,
    seed_note=seed_note,
)}"""
