from __future__ import annotations

import json


def _shared_context(template_name: str, template_family: str) -> str:
    return "\n".join(
        [
            f"Template: {template_name}",
            f"Template family: {template_family}",
        ]
    )


def build_curriculum_enrichment_system_prompt(
    *,
    template_name: str,
    template_family: str,
    lesson_flow: list[str],
    tone: str,
    pacing: str,
) -> str:
    lesson_flow_text = " -> ".join(lesson_flow) if lesson_flow else "not specified"
    return f"""You enrich an existing curriculum outline for an educational textbook section.

{_shared_context(template_name, template_family)}
Lesson flow each section follows: {lesson_flow_text}
Tone: {tone}
Pacing: {pacing}

You will receive a pre-existing section outline.
Do NOT change structural fields such as section_id, title, position, focus,
role, objective, selected_components, or section ordering.

Return a JSON object with key `sections`.
Each entry in `sections` must include:
- section_id
- terms_to_define (list[str])
- terms_assumed (list[str])
- practice_target (string or null)
- bridges_from (string or null)
- bridges_to (string or null)

Rules:
- Assign each key term to exactly one section via terms_to_define.
- Later sections that use earlier terms should list them in terms_assumed.
- practice_target should be specific to that section's practice work.
- bridges_from and bridges_to should describe the conceptual handoff between sections.
- Preserve the order of sections exactly as supplied.

Output only valid JSON. No preamble, no markdown fences."""


def build_curriculum_enrichment_user_prompt(
    *,
    context: str,
    subject: str,
    grade_band: str,
    learner_fit: str,
    sections: list[dict[str, object]],
) -> str:
    return f"""Context: {context}
Subject: {subject}
Grade level: {grade_band}
Learner type: {learner_fit}

Existing section outline:
{json.dumps(sections, indent=2)}

Return one enrichment entry per section using the same section_id values."""
