"""
Prompt builders for the content_generator node.
"""

from __future__ import annotations

from pipeline.contracts import (
    get_component_registry_entry,
    get_generation_guidance,
    get_lesson_flow,
    get_optional_fields,
    get_required_fields,
)
from pipeline.prompts.shared import (
    capacity_reminder_for_fields,
    capacity_reminder_for_manifest_fields,
    shared_context,
)
from pipeline.types.generation_manifest import GenerationFieldContract, SectionGenerationManifest
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

- `emphasis` arrays contain plain strings; no markdown syntax inside them.

- Short label fields (term, next, misconception, action): plain text, no markdown."""


CORE_FIELDS = {"header", "hook", "explanation"}
PRACTICE_FIELDS = {"practice", "what_next", "pitfall", "pitfalls", "prerequisites"}
ENRICHMENT_FIELDS = {
    "callout",
    "summary",
    "student_textbox",
    "short_answer",
    "fill_in_blank",
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
    "divider",
    "key_fact",
}
_EXTERNAL_FIELDS = {
    "diagram",
    "diagram_compare",
    "diagram_series",
    "simulation",
    "image_block",
    "video_embed",
}


def _section_plan_policy_block(section_plan: SectionPlan) -> str:
    continuity = section_plan.continuity_notes or "none"
    required_components = ", ".join(section_plan.required_components) or "none"
    optional_components = ", ".join(section_plan.optional_components) or "none"
    terms_to_define = ", ".join(section_plan.terms_to_define) or "none"
    terms_assumed = ", ".join(section_plan.terms_assumed) or "none"
    practice_target = section_plan.practice_target or "not specified"
    visual_commitment = section_plan.visual_commitment or "not specified"
    return f"""Planning policy:
  role: {section_plan.role}
  required_components: {required_components}
  optional_components: {optional_components}
  interaction_policy: {section_plan.interaction_policy}
  diagram_policy: {section_plan.diagram_policy}
  enrichment_enabled: {section_plan.enrichment_enabled}
  continuity_notes: {continuity}
  terms_to_define: {terms_to_define}
  terms_assumed: {terms_assumed}
  practice_target: {practice_target}
  visual_commitment: {visual_commitment}"""


def _legacy_visual_context_block(section_plan: SectionPlan) -> str:
    commitment = section_plan.visual_commitment
    if commitment is None:
        return ""
    if commitment == "diagram":
        return (
            "Visual context:\n"
            "This section WILL include a diagram. You may reference it as "
            "'the diagram below' in explanations or practice."
        )
    if commitment == "interaction":
        return (
            "Visual context:\n"
            "This section WILL include an interactive element. You may reference "
            "it as 'the interactive above' in explanations or practice."
        )
    return (
        "Visual context:\n"
        "This section has NO diagram or interactive. Do not reference any visual "
        "element in explanations or practice."
    )


def _explanation_visual_reference(section_plan: SectionPlan) -> tuple[str, str] | None:
    placements = [placement for placement in section_plan.visual_placements if placement.block == "explanation"]
    slot_order = {
        "diagram_compare": 0,
        "diagram_series": 1,
        "diagram": 2,
    }
    placements.sort(key=lambda placement: slot_order.get(placement.slot_type, 99))
    if not placements:
        return None

    primary = placements[0]
    if primary.slot_type == "diagram_compare":
        return "comparison above", "the comparison above"
    if primary.slot_type == "diagram_series":
        return "diagrams above", "the diagrams above"
    return "diagram below", "the diagram below"


def _visual_context_block(
    section_plan: SectionPlan,
    *,
    phase: str = "all",
) -> str:
    if not section_plan.visual_placements:
        return _legacy_visual_context_block(section_plan)

    reference = _explanation_visual_reference(section_plan)

    if phase == "core":
        if reference is None:
            return (
                "Visual context:\n"
                "This section has NO diagram near the explanation. "
                "Do not reference any visual element."
            )
        location, phrase = reference
        if location == "diagram below":
            return (
                "Visual context:\n"
                "This section includes a diagram below the explanation. "
                f"You may reference it as '{phrase}'."
            )
        if location == "diagrams above":
            return (
                "Visual context:\n"
                "This section includes diagrams above the explanation. "
                f"You may reference them as '{phrase}'. "
                "Do NOT say 'the diagram below'."
            )
        return (
            "Visual context:\n"
            f"This section includes a {location} the explanation. "
            f"You may reference it as '{phrase}'. "
            "Do NOT say 'the diagram below'."
        )

    if phase == "practice":
        if any(placement.block == "practice" for placement in section_plan.visual_placements):
            return (
                "Visual context:\n"
                "Some practice items include their own supporting visuals. "
                "Only reference a diagram when the placement explicitly belongs to that problem."
            )
        if reference is not None:
            return (
                "Visual context:\n"
                "The section diagram appears elsewhere. "
                "Do not reference it from individual practice problems."
            )
        return (
            "Visual context:\n"
            "This section has NO diagram for practice problems. "
            "Do not reference any visual element."
        )

    if phase == "enrichment":
        return (
            "Visual context:\n"
            "Do not reference any diagram or other visual element in enrichment content."
        )

    if reference is None:
        return (
            "Visual context:\n"
            "This section has NO diagram or interactive. "
            "Do not reference any visual element."
        )

    location, phrase = reference
    if location == "diagram below":
        return (
            "Visual context:\n"
            "This section includes a diagram below the explanation. "
            f"Only the explanation may reference it as '{phrase}'. "
            "Practice problems must not reference that section-level diagram, "
            "and enrichment content must not reference visuals."
        )
    if location == "diagrams above":
        return (
            "Visual context:\n"
            "This section includes diagrams above the explanation. "
            f"Only the explanation may reference them as '{phrase}'. "
            "Practice problems must not reference that section-level visual, "
            "and enrichment content must not reference visuals."
        )
    return (
        "Visual context:\n"
        f"This section includes a {location} the explanation. "
        f"Only the explanation may reference it as '{phrase}'. "
        "Practice problems must not reference that section-level visual, "
        "and enrichment content must not reference visuals."
    )


def _compact_shape(schema: dict) -> str:
    if not schema:
        return "unknown"
    title = schema.get("title")
    if isinstance(title, str) and title:
        return title
    any_of = schema.get("anyOf") or schema.get("oneOf")
    if isinstance(any_of, list):
        return " / ".join(
            str(branch.get("title") or branch.get("type") or "object")
            for branch in any_of[:3]
            if isinstance(branch, dict)
        ) or "union"
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        if isinstance(props, dict) and props:
            sample = ", ".join(list(props.keys())[:4])
            return f"object({sample})"
        return "object"
    return str(schema.get("type", "unknown"))


def _format_capacity(capacity: dict) -> str:
    if not capacity:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(capacity.items()))


def _field_contract_block(field: GenerationFieldContract) -> str:
    registry_entry = get_component_registry_entry(field.component_id) or {}
    purpose = registry_entry.get("purpose") or "n/a"
    return (
        f"Field: {field.field_name}\n"
        f"Component: {field.component_id}\n"
        f"Required: {'yes' if field.required else 'no'}\n"
        f"Purpose: {purpose}\n"
        f"Generation hint: {field.generation_hint or 'n/a'}\n"
        f"Capacity: {_format_capacity(field.capacity)}\n"
        f"Shape: {_compact_shape(field.schema)}"
    )


def _manifest_field_block(fields: list[GenerationFieldContract]) -> str:
    if not fields:
        return "none"
    return "\n\n".join(_field_contract_block(field) for field in fields)


def _active_manifest_fields(
    manifest: SectionGenerationManifest | None,
    *,
    phase_fields: set[str] | None = None,
) -> list[GenerationFieldContract]:
    if manifest is None:
        return []
    fields = manifest.active_text_fields()
    if phase_fields is None:
        return fields
    return [field for field in fields if field.field_name in phase_fields]


def build_content_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
    *,
    manifest: SectionGenerationManifest | None = None,
) -> str:
    guidance = get_generation_guidance(template_id)
    lesson_flow = " -> ".join(get_lesson_flow(template_id))
    manifest_fields = _active_manifest_fields(manifest)

    if manifest_fields:
        required = [field.field_name for field in manifest.required_fields if not field.external]
        optional = [field.field_name for field in manifest.optional_fields if not field.external]
        field_contracts = _manifest_field_block(manifest_fields)
        capacity_block = capacity_reminder_for_manifest_fields(manifest_fields)
    else:
        required = get_required_fields(template_id)
        optional = get_optional_fields(template_id)
        field_contracts = "none"
        capacity_block = capacity_reminder_for_fields(required + optional)

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

Field contracts:
{field_contracts}

{capacity_block}

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

    visual_context = _visual_context_block(section_plan, phase="all")
    if visual_context:
        base += f"\n\n{visual_context}"

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
        error_lines = "\n".join(f"  - Field `{e['field']}`: {e['message']}" for e in validation_errors)
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


def _phase_system_prompt(
    *,
    template_id: str,
    template_name: str,
    template_family: str,
    phase_name: str,
    phase_fields: set[str],
    manifest: SectionGenerationManifest | None = None,
) -> str:
    guidance = get_generation_guidance(template_id)
    manifest_fields = _active_manifest_fields(manifest, phase_fields=phase_fields)

    if manifest_fields:
        active_required = [
            field.field_name
            for field in manifest.required_fields
            if not field.external and field.field_name in phase_fields
        ]
        active_optional = [
            field.field_name
            for field in manifest.optional_fields
            if not field.external and field.field_name in phase_fields
        ]
        capacity_block = capacity_reminder_for_manifest_fields(manifest_fields)
        field_contracts = _manifest_field_block(manifest_fields)
    else:
        required = get_required_fields(template_id)
        optional = get_optional_fields(template_id)
        active_required = [field for field in required if field in phase_fields]
        active_optional = [field for field in optional if field in phase_fields]
        capacity_block = capacity_reminder_for_fields(active_required + active_optional)
        field_contracts = "none"

    req_block = (
        "Required fields:\n" + "\n".join(f"  - {field}" for field in active_required)
        if active_required
        else "Required fields:\n  - none"
    )
    opt_block = (
        "Optional fields (include only when warranted):\n"
        + "\n".join(f"  - {field}" for field in active_optional)
        if active_optional
        else "Optional fields (include only when warranted):\n  - none"
    )

    return f"""You generate the {phase_name} phase of an educational textbook section.
You fill structured JSON slots. You do not make layout decisions.

{shared_context(template_name, template_family, '', '', '')}

Tone: {guidance['tone']}
Pacing: {guidance['pacing']}

{req_block}
{opt_block}

Field contracts:
{field_contracts}

{capacity_block}

{_FIELD_FORMATTING_RULES}

Output valid JSON matching the schema exactly. No preamble, no markdown fences."""


def build_core_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
    *,
    manifest: SectionGenerationManifest | None = None,
) -> str:
    return _phase_system_prompt(
        template_id=template_id,
        template_name=template_name,
        template_family=template_family,
        phase_name="core",
        phase_fields=CORE_FIELDS,
        manifest=manifest,
    )


def build_practice_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
    *,
    manifest: SectionGenerationManifest | None = None,
) -> str:
    return _phase_system_prompt(
        template_id=template_id,
        template_name=template_name,
        template_family=template_family,
        phase_name="practice",
        phase_fields=PRACTICE_FIELDS,
        manifest=manifest,
    )


def build_enrichment_system_prompt(
    template_id: str,
    template_name: str,
    template_family: str,
    active_enrichment_fields: list[str] | None = None,
    *,
    manifest: SectionGenerationManifest | None = None,
) -> str:
    return _phase_system_prompt(
        template_id=template_id,
        template_name=template_name,
        template_family=template_family,
        phase_name="enrichment",
        phase_fields=set(active_enrichment_fields or ENRICHMENT_FIELDS),
        manifest=manifest,
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

    visual_context = _visual_context_block(section_plan, phase="core")
    if visual_context:
        base += f"\n\n{visual_context}"

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
    _ = template_id
    return f"""Generate the PRACTICE content for this section.

Section: {section_plan.title} (position {section_plan.position})
Focus: {section_plan.focus}
Subject: {subject}
Context: {context}
Grade level: {grade_band}
Learner type: {learner_fit}
{_section_plan_policy_block(section_plan)}

{_visual_context_block(section_plan, phase="practice")}

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
    _ = template_id
    fields_block = ", ".join(active_enrichment_fields)
    return f"""Generate ENRICHMENT content for this section.

Section: {section_plan.title} (position {section_plan.position})
Focus: {section_plan.focus}
Subject: {subject}
Context: {context}
Grade level: {grade_band}
Learner type: {learner_fit}
{_section_plan_policy_block(section_plan)}

{_visual_context_block(section_plan, phase="enrichment")}

Core content already generated:
{core_summary}

Generate these enrichment fields: {fields_block}
Include only fields that genuinely add value. Omit any that feel forced.
{f"RERENDER - fix: {rerender_reason}" if rerender_reason else ""}"""
