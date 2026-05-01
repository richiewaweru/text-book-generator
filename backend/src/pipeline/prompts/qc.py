"""
Prompt builders for the qc_agent node.

System prompt: fixed per template (QC criteria, what good looks like).
User prompt: variable per section (assembled section JSON).
"""

from __future__ import annotations

from pipeline.contracts import get_generation_guidance, get_lesson_flow


def build_qc_system_prompt(template_id: str) -> str:
    guidance = get_generation_guidance(template_id)
    lesson_flow = " \u2192 ".join(get_lesson_flow(template_id))

    return f"""You perform semantic quality control on a generated educational section.

Structural schema validation has already passed.
Do not report missing JSON fields, wrong field names, or schema issues.
Your job is semantic quality only -- does the content that is present actually teach well?

Template intent: {lesson_flow}
Expected tone: {guidance['tone']}
Expected pacing: {guidance['pacing']}
Avoid: {', '.join(guidance['avoid'])}

Evaluate only fields that are present in the section JSON.
For each field present, ask whether the content does its job well.

HOOK (if present): Does it create genuine felt need?
EXPLANATION (if present): Is the core concept actually explained?
PRACTICE (if present): Are the problems genuinely graduated in difficulty?
PITFALL (if present): Is the misconception specific and real?
WORKED EXAMPLE (if present): Does each step state why, not just what?
SUMMARY (if present): Does it capture the key ideas without padding?
COMPARISON GRID (if present): Do the rows reveal genuine contrast?
DEFINITION FAMILY (if present): Are plain definitions usable on their own?

Output a JSON object with:
  passed: bool
  issues: list of objects, each with:
    block: which field failed (e.g. "hook", "explanation")
    severity: "blocking" (must fix) or "warning" (should fix)
    message: one sentence describing the problem
  warnings: list of strings (minor style notes)

If passed is true, issues must be empty.
Output only valid JSON. No preamble, no markdown fences."""


def build_qc_user_prompt(
    section_json: str,
    selected_components: list[str] | None = None,
    section_role: str | None = None,
    pack_objective: str | None = None,
) -> str:
    components_block = ""
    if selected_components:
        components_list = ", ".join(selected_components)
        role_label = section_role or "unspecified"
        components_block = f"""Planned components for this section: {components_list}
Role: {role_label}

IMPORTANT: Evaluate ONLY the components listed above.
Do NOT flag missing components that were not planned.
Absence of a component that is not in the planned list is correct behavior, not a quality failure.

"""

    objective_block = ""
    if pack_objective:
        objective_block = f"Pack objective: {pack_objective}\n\n"

    return f"""Evaluate this section:

{objective_block}{components_block}{section_json}"""
