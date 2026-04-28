"""
Prompt builders for the field_regenerator node.

System prompt: lean -- template tone + guidance only.
User prompt:   the failing field name, the reason it failed,
               and the rest of the section as context.
"""

from __future__ import annotations

import json

from pipeline.contracts import (
    get_field_schema,
    get_generation_guidance,
    get_lesson_flow,
)
from pipeline.types.section_content import SectionContent

# Fields the QC agent can flag for targeted retry.
# These map directly to SectionContent field names.
RETRYABLE_FIELDS = {
    "hook",
    "explanation",
    "callout",
    "summary",
    "student_textbox",
    "short_answer",
    "fill_in_blank",
    "practice",
    "worked_example",
    "definition",
    "key_fact",
    "pitfall",
    "glossary",
    "what_next",
    "divider",
}


def build_field_regen_system_prompt(template_id: str, field_name: str) -> str:
    guidance = get_generation_guidance(template_id)
    lesson_flow = " -> ".join(get_lesson_flow(template_id))
    schema = get_field_schema(field_name)
    schema_block = (
        f"\nTarget field schema:\n{json.dumps(schema, indent=2)}\n"
        if schema is not None
        else ""
    )

    return f"""You regenerate a single failing field in an educational section.
The rest of the section is already correct and complete.

Template flow: {lesson_flow}
Tone: {guidance['tone']}
Pacing: {guidance['pacing']}
Avoid: {', '.join(guidance['avoid'])}
{schema_block}

You receive:
  - the name of the field to regenerate
  - the reason it failed quality review
  - the rest of the section as context (do not reproduce it)

Output only the regenerated field value as valid JSON.
Match the target field schema exactly.
Do not output the full section. Do not add wrapper keys.
If the field is a string, output a JSON string.
If the field is an object, output a JSON object.
If the field is a list, output a JSON array.
No preamble, no markdown fences.
Example -- if regenerating 'hook', output only:
  {{"headline": "...", "body": "...", "anchor": "..."}}"""


def build_field_regen_user_prompt(
    section: SectionContent,
    failing_field: str,
    reason: str,
) -> str:
    # Serialize everything except the failing field as context.
    # The model sees what it needs to stay coherent.
    preserved = section.model_dump(
        exclude_none=True,
        exclude={failing_field},
    )

    return f"""Regenerate the '{failing_field}' field.

Reason it failed:
  {reason}

Rest of the section (context only -- do not reproduce):
{json.dumps(preserved, indent=2)}

Output only the regenerated '{failing_field}' JSON value."""
