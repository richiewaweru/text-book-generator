"""
Prompt builders for the curriculum_planner node.

System prompt: fixed per template (lesson flow, guidance, section format).
User prompt: variable per invocation (context, subject, grade, learner fit, count).
"""

from __future__ import annotations

from curriculum_enrichment.prompts import (
    build_curriculum_enrichment_system_prompt as _shared_enrichment_system_prompt,
    build_curriculum_enrichment_user_prompt as _shared_enrichment_user_prompt,
)

from pipeline.contracts import get_lesson_flow, get_generation_guidance
from pipeline.prompts.shared import shared_context


def build_curriculum_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    lesson_flow = " \u2192 ".join(get_lesson_flow(template_id))
    guidance = get_generation_guidance(template_id)

    return f"""You plan the curriculum outline for an educational textbook section.

{shared_context(template_name, template_family, '', '', '')}
Lesson flow each section follows: {lesson_flow}
Tone: {guidance['tone']}
Pacing: {guidance['pacing']}

Your output is a JSON array of section plans.
Each plan has: section_id, title, position, focus, bridges_from, bridges_to,
needs_worked_example (bool), terms_to_define (list[str]),
terms_assumed (list[str]), practice_target (string or null).

Rules:
- section_id format: s-01, s-02, s-03 etc.
- title: max 10 words, specific to the content
- focus: one sentence describing what this section specifically covers
- bridges_from: the concept from the previous section (null for first)
- bridges_to: the concept the next section will cover (null for last)
- needs_worked_example: true for procedural or mathematical concepts
- assign each key term to exactly one section via terms_to_define
- later sections that use earlier terms should list them in terms_assumed
- practice_target should say what the practice in THIS section should test

Output only valid JSON. No preamble, no markdown fences."""


def build_curriculum_user_prompt(
    context: str,
    subject: str,
    grade_band: str,
    learner_fit: str,
    section_count: int,
) -> str:
    return f"""Context: {context}
Subject: {subject}
Grade level: {grade_band}
Learner type: {learner_fit}
Number of sections to plan: {section_count}

Plan {section_count} sections that teach this context progressively."""


def build_curriculum_enrichment_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
) -> str:
    guidance = get_generation_guidance(template_id)
    return _shared_enrichment_system_prompt(
        template_name=template_name,
        template_family=template_family,
        lesson_flow=get_lesson_flow(template_id),
        tone=str(guidance["tone"]),
        pacing=str(guidance["pacing"]),
    )


def build_curriculum_enrichment_user_prompt(
    *,
    context: str,
    subject: str,
    grade_band: str,
    learner_fit: str,
    sections: list[dict[str, object]],
) -> str:
    return _shared_enrichment_user_prompt(
        context=context,
        subject=subject,
        grade_band=grade_band,
        learner_fit=learner_fit,
        sections=sections,
    )
