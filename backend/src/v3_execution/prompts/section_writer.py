from __future__ import annotations

import json

from v3_execution.prompts.formatting import (
    format_consistency_rules,
    format_source_of_truth,
    format_support_adaptations,
)
from v3_execution.models import SectionWriterWorkOrder


def build_section_writer_prompt(order: SectionWriterWorkOrder) -> str:
    components_list = "\n".join(
        f"- {c.teacher_label or c.component_id} ({c.component_id}): {c.content_intent}"
        for c in order.section.components
    )
    field_map = json.dumps(
        {
            c.component_id: order.manifest_components.get(c.component_id, {})
            for c in order.section.components
        },
        indent=2,
        default=str,
    )
    return f"""You are a section writer, not a lesson planner.

Your job is to generate component content for one section of a lesson.
You have been given a precise work order. Follow it exactly.

SECTION: {order.section.title}
SECTION_ID: {order.section.id}
LEARNING INTENT: {order.section.learning_intent}

COMPONENTS TO WRITE:
{components_list}

REGISTER:
- Level: {order.register_spec.level}
- Sentence length: {order.register_spec.sentence_length}
- Vocabulary: {order.register_spec.vocabulary_policy}
- Tone: {order.register_spec.tone}
- Avoid: {", ".join(order.register_spec.avoid) or "none"}

LEARNER PROFILE:
{order.learner_profile.level_summary}
Reading load: {order.learner_profile.reading_load}
Language support: {order.learner_profile.language_support}
Pacing: {order.learner_profile.pacing}

SUPPORT ADAPTATIONS:
{format_support_adaptations(order.support_adaptations)}

ANCHOR FACTS (do not change these):
{format_source_of_truth(order.source_of_truth)}

CONSISTENCY RULES:
{format_consistency_rules(order.consistency_rules)}

SECTION CONSTRAINTS:
{chr(10).join(f"- {c}" for c in order.section.constraints) or "- none"}

MANIFEST SCHEMA HINT (per component JSON contract):
{field_map}

STRICT RULES:
- Generate only the components listed above. Do not add others.
- Do not add diagrams, questions, or visuals. Those are separate.
- Do not change anchor facts, units, or fixed terms.
- Do not change question difficulty or numbering.
Return JSON ONLY with shape:
{{"fields": {{
  "<section_field snake_case>": {{ ...matching component schema }},
  ...
}}}}
"""


__all__ = ["build_section_writer_prompt"]
