from __future__ import annotations

from generation.v3_studio.prompts import build_v3_shared_prefix
from core.prompts import effective_prompt_text
from v3_execution.prompts.formatting import format_source_of_truth
from v3_execution.models import QuestionWriterWorkOrder


def _load_static_body() -> str:
    return effective_prompt_text("question-writer")


def build_question_writer_prompt(order: QuestionWriterWorkOrder) -> str:
    shared_prefix = build_v3_shared_prefix()
    if order.component_id:
        return _build_component_aware_prompt(order, shared_prefix=shared_prefix)

    questions_spec = "\n\n".join(
        f"""Question {q.id}:
  Difficulty: {q.difficulty}
  Skill target: {q.skill_target}
  Scaffolding: {q.scaffolding}
  Purpose: {q.purpose}
  Diagram required: {"yes" if q.diagram_required else "no"}
  Uses anchor: {q.uses_anchor_id or "no"}
  Expected answer: {q.expected_answer}
  Expected working: {q.expected_working or "not required"}
  Constraints: {", ".join(q.student_facing_constraints) or "none"}"""
        for q in order.questions
    )
    return f"""{shared_prefix}
{_load_static_body()}
{questions_spec}

ANCHOR FACTS (do not change these):
{format_source_of_truth(order.source_of_truth)}

REGISTER:
{order.register_spec.level} · {order.register_spec.tone}
Avoid: {", ".join(order.register_spec.avoid) or "none"}

Return JSON ONLY: {{"items": {{
  "<question_id>": {{"stem": "<student-facing text>"}}
}} }}
"""


def _build_component_aware_prompt(
    order: QuestionWriterWorkOrder,
    *,
    shared_prefix: str,
) -> str:
    schema = order.schema_summary or f"exact Lectio content for {order.component_id}"
    purpose = order.purpose or "Teach the lesson objective via this component."
    repair = ""
    if order.prior_validation_errors:
        error_lines = "\n".join(f"  - {e}" for e in order.prior_validation_errors[:12])
        repair = f"""
REPAIR REQUIRED — previous output failed the exact Lectio contract.
Validation errors:
{error_lines}

Repair the SAME component ({order.component_id}).
Do not change component identity.
Return only the expected component payload.
"""
    return f"""{shared_prefix}
{_load_static_body()}
{repair}
COMPONENT-AWARE ITEM GENERATION
component_id: {order.component_id}
section_field: {order.section_field or "unknown"}
purpose: {purpose}

You must produce the ACTUAL Lectio content object for this component.
Schema summary:
{schema}

Do NOT wrap the payload as {{"items":[...]}}.
Do NOT invent a different component_id.
Return JSON ONLY as:
{{
  "component_id": "{order.component_id}",
  "content": {{ ...exact Lectio {order.section_field or "field"} object... }}
}}

ANCHOR FACTS (do not change these):
{format_source_of_truth(order.source_of_truth)}

REGISTER:
{order.register_spec.level} · {order.register_spec.tone}
Avoid: {", ".join(order.register_spec.avoid) or "none"}
"""


__all__ = ["build_question_writer_prompt"]
