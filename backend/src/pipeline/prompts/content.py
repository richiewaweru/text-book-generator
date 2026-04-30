"""
Prompt builders for manifest-driven section generation.
"""

from __future__ import annotations

from pipeline.contracts import build_section_generation_manifest
from pipeline.contracts import get_component_registry_entry
from pipeline.prompts.shared import capacity_reminder_for_manifest_fields
from pipeline.types.generation_manifest import GenerationFieldContract, SectionGenerationManifest
from pipeline.types.requests import SectionPlan

_FIELD_FORMATTING_RULES = """\
## Field formatting rules

- Body fields should be prose only unless the target schema explicitly requires arrays or structured items.
- Use markdown sparingly and only where the field naturally supports it.
- Do not invent schema keys or nested objects.
- Leave unselected fields absent.
"""


def _section_plan_policy_block(section_plan: SectionPlan) -> str:
    continuity = section_plan.continuity_notes or "none"
    required_components = ", ".join(section_plan.required_components) or "none"
    terms_to_define = ", ".join(section_plan.terms_to_define) or "none"
    terms_assumed = ", ".join(section_plan.terms_assumed) or "none"
    practice_target = section_plan.practice_target or "not specified"
    placement_count = len(section_plan.visual_placements)
    return f"""Planning policy:
  role: {section_plan.role}
  required_components: {required_components}
  interaction_policy: {section_plan.interaction_policy}
  diagram_policy: {section_plan.diagram_policy}
  continuity_notes: {continuity}
  terms_to_define: {terms_to_define}
  terms_assumed: {terms_assumed}
  practice_target: {practice_target}
  visual_placements: {placement_count} placement(s)"""


def _compact_shape(schema: dict) -> str:
    if not schema:
        return "unknown"
    title = schema.get("title")
    if isinstance(title, str) and title:
        return title
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        if isinstance(props, dict) and props:
            return f"object({', '.join(list(props.keys())[:4])})"
        return "object"
    any_of = schema.get("anyOf") or schema.get("oneOf")
    if isinstance(any_of, list):
        return " / ".join(
            str(branch.get("title") or branch.get("type") or "object")
            for branch in any_of[:3]
            if isinstance(branch, dict)
        ) or "union"
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
        f"Purpose: {purpose}\n"
        f"Generation hint: {field.generation_hint or 'n/a'}\n"
        f"Capacity: {_format_capacity(field.capacity)}\n"
        f"Shape: {_compact_shape(field.schema)}"
    )


def _manifest_field_block(fields: list[GenerationFieldContract]) -> str:
    if not fields:
        return "none"
    return "\n\n".join(_field_contract_block(field) for field in fields)


def _visual_context_block(section_plan: SectionPlan) -> str:
    if not section_plan.visual_placements:
        return (
            "Visual context:\n"
            "This section has NO diagram or visual element.\n"
            "Do NOT reference a diagram, image, or simulation."
        )

    section_placements = [
        placement for placement in section_plan.visual_placements if placement.block == "section"
    ]
    if section_placements:
        slot_type = section_placements[0].slot_type
        if slot_type == "diagram_series":
            return (
                "Visual context:\n"
                "This section's primary content IS the diagram series. "
                "Each step_label and caption you write will become an image generation prompt. "
                "Write captions as precise visual descriptions of what the image must show. "
                "Be specific: name the objects, their positions, labels, and spatial relationships. "
                "For mathematical content: name axes, label values, describe line direction. "
                "For scientific content: name structures, label components, describe relative positions. "
                "Do NOT write captions that restate the step title. "
                "Do NOT write prose that says 'see the diagram'. "
                "The caption IS the image instruction."
            )
        if slot_type == "diagram_compare":
            return (
                "Visual context:\n"
                "This section's primary content IS a comparison diagram. "
                "The before_label and after_label you write will become image prompts. "
                "Write them as precise visual descriptions. "
                "Be specific about what each state shows and how they differ visually."
            )
        return (
            "Visual context:\n"
            "This section's primary content IS a diagram. "
            "The caption and alt_text you write will become the image generation prompt. "
            "Write them as precise visual descriptions of what the image must show. "
            "Name the objects, labels, and relationships explicitly."
        )

    explanation_lines: list[str] = []
    practice_lines: list[str] = []
    worked_example_lines: list[str] = []

    for placement in section_plan.visual_placements:
        if placement.block == "explanation":
            if placement.slot_type == "diagram_series":
                explanation_lines.append("There will be a diagram series above the explanation.")
            elif placement.slot_type == "diagram_compare":
                explanation_lines.append("There will be a diagram series above the explanation for comparison.")
            else:
                explanation_lines.append("There will be a diagram alongside the explanation.")
        elif placement.block == "practice":
            if placement.problem_indices:
                labels = [str(index + 1) for index in placement.problem_indices]
                if len(labels) == 1:
                    target = f"problem {labels[0]}"
                else:
                    target = f"problems {', '.join(labels[:-1])} and {labels[-1]}"
                practice_lines.append(
                    f"The selected inline diagrams belong to {target}. Only those specific problems may say 'the diagram'."
                )
            else:
                practice_lines.append("Some practice problems have selected inline diagrams.")
        elif placement.block == "worked_example":
            worked_example_lines.append(
                "The worked example may include its own compact diagram. All other content must avoid visual references."
            )

    lines = [
        "Visual context:",
        "Selected visuals will be generated separately. You may reference them only where listed.",
    ]
    lines.extend(explanation_lines)
    if practice_lines:
        lines.extend(practice_lines)
    elif explanation_lines:
        lines.append(
            "The section diagram appears elsewhere in the section - not next to practice problems. Describe every scenario in words."
        )
    lines.extend(worked_example_lines)
    return "\n".join(lines)


def build_content_user_prompt(
    *,
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
) -> str:
    manifest = build_section_generation_manifest(
        template_id=template_id,
        section_plan=section_plan,
    )
    return build_section_user_prompt(
        plan=section_plan,
        subject=subject,
        context=context,
        grade_band=grade_band,
        learner_fit=learner_fit,
        manifest=manifest,
    )


def build_core_user_prompt(
    *,
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    template_id: str,
) -> str:
    return build_content_user_prompt(
        section_plan=section_plan,
        subject=subject,
        context=context,
        grade_band=grade_band,
        learner_fit=learner_fit,
        template_id=template_id,
    )


def build_section_system_prompt(manifest: SectionGenerationManifest) -> str:
    text_fields = manifest.active_text_fields()
    required = [field.field_name for field in manifest.required_fields if not field.external]
    optional = [field.field_name for field in manifest.optional_fields if not field.external]
    field_contracts = _manifest_field_block(text_fields)
    capacity_block = capacity_reminder_for_manifest_fields(text_fields)

    return f"""You generate content for one textbook section from a manifest.
Generate only the fields listed below.
Do not add fields.
Do not invent components.
Do not generate media content - media is generated separately.

Required text fields:
{chr(10).join(f'  - {field}' for field in required) if required else '  - none'}

Optional text fields:
{chr(10).join(f'  - {field}' for field in optional) if optional else '  - none'}

Field contracts:
{field_contracts}

{capacity_block}

{_FIELD_FORMATTING_RULES}

Output a single SectionContent JSON object with only the selected fields populated.
Output only valid JSON. No preamble. No markdown fences."""


def build_section_user_prompt(
    *,
    plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    manifest: SectionGenerationManifest,
    rerender_reason: str | None = None,
) -> str:
    field_names = [
        field.field_name
        for field in [*manifest.required_fields, *manifest.optional_fields]
        if not field.external
    ]
    lines = [
        "Section to generate:",
        f"  section_id: {plan.section_id}",
        f"  template_id: {manifest.template_id}",
        f"  title: {plan.title}",
        f"  position: {plan.position}",
        f"  focus: {plan.focus}",
        f"  bridges_from: {plan.bridges_from or 'none'}",
        f"  bridges_to: {plan.bridges_to or 'none'}",
        "",
        f"Subject: {subject}",
        f"Context: {context}",
        f"Grade level: {grade_band}",
        f"Learner type: {learner_fit}",
        "",
        _section_plan_policy_block(plan),
        "",
        "Selected text fields:",
        *(f"- {name}" for name in field_names),
        "",
        _visual_context_block(plan),
    ]
    if rerender_reason:
        lines.extend(
            [
                "",
                "Repair instructions:",
                rerender_reason,
                "Fix only the selected fields that need repair while staying inside the manifest.",
            ]
        )
    return "\n".join(lines)


def build_content_repair_user_prompt(
    *,
    section_plan: SectionPlan,
    subject: str,
    context: str,
    grade_band: str,
    learner_fit: str,
    manifest: SectionGenerationManifest,
    validation_summary: str,
    validation_errors: list[dict[str, str]] = (),
    rerender_reason: str | None = None,
) -> str:
    if validation_errors:
        error_lines = "\n".join(f"- Field `{e['field']}`: {e['message']}" for e in validation_errors)
        repair_summary = f"Validation issues to fix:\n{error_lines}"
    else:
        repair_summary = f"Validation summary:\n{validation_summary}"

    return "\n\n".join(
        [
            repair_summary,
            build_section_user_prompt(
                plan=section_plan,
                subject=subject,
                context=context,
                grade_band=grade_band,
                learner_fit=learner_fit,
                manifest=manifest,
                rerender_reason=rerender_reason,
            ),
        ]
    )
