"""
Deterministic. No LLM.

Validates assembled section content against the template contract
(Layer 3a: contract compliance, Layer 3b: capacity limits).

STATE CONTRACT
    Reads:  current_section_id, generated_sections, contract
    Writes: assembled_sections[current_section_id], qc_reports (capacity warnings),
            completed_nodes, errors
    Model:  none
    Skips:  never
"""

from __future__ import annotations

from pipeline.contracts import validate_section_for_template
from pipeline.state import PipelineError, QCReport, TextbookPipelineState


def _check_capacity(section_dict: dict) -> list[str]:
    """
    Check capacity limits for all fields present in the section.
    Returns a list of warning strings -- not blocking violations.
    These mirror src/lib/validate.ts exactly.
    """
    warnings = []

    def words(text: str | None) -> int:
        if not text:
            return 0
        return len(str(text).strip().split())

    hook = section_dict.get("hook", {})
    if words(hook.get("headline")) > 12:
        warnings.append("hook.headline exceeds 12 words")
    if words(hook.get("body")) > 80:
        warnings.append("hook.body exceeds 80 words")

    explanation = section_dict.get("explanation", {})
    if words(explanation.get("body")) > 350:
        warnings.append("explanation.body exceeds 350 words")
    emphasis = explanation.get("emphasis", [])
    if len(emphasis) > 3:
        warnings.append(f"explanation.emphasis has {len(emphasis)} items -- max 3")

    practice = section_dict.get("practice", {})
    problems = practice.get("problems", [])
    if len(problems) < 2:
        warnings.append(f"practice has {len(problems)} problems -- minimum 2")
    if len(problems) > 5:
        warnings.append(f"practice has {len(problems)} problems -- maximum 5")
    for i, problem in enumerate(problems):
        hints = problem.get("hints", [])
        if len(hints) > 3:
            warnings.append(
                f"practice problem {i + 1} has {len(hints)} hints -- max 3"
            )

    glossary = section_dict.get("glossary")
    if glossary:
        terms = glossary.get("terms", [])
        if len(terms) > 8:
            warnings.append(f"glossary has {len(terms)} terms -- max 8")

    worked = section_dict.get("worked_example")
    if worked:
        steps = worked.get("steps", [])
        if len(steps) > 6:
            warnings.append(f"worked_example has {len(steps)} steps -- max 6")

    what_next = section_dict.get("what_next", {})
    if words(what_next.get("body")) > 50:
        warnings.append("what_next.body exceeds 50 words")

    definition = section_dict.get("definition")
    if definition:
        if words(definition.get("formal")) > 80:
            warnings.append("definition.formal exceeds 80 words")
        if words(definition.get("plain")) > 60:
            warnings.append("definition.plain exceeds 60 words")

    return warnings


async def section_assembler(
    state: TextbookPipelineState | dict,
    *,
    provider_overrides: dict | None = None,
) -> dict:
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id

    section = state.generated_sections.get(sid)
    if not section:
        return {
            "errors": [
                PipelineError(
                    node="section_assembler",
                    section_id=sid,
                    message=f"No generated content found for section {sid}. "
                    f"content_generator may have failed.",
                    recoverable=False,
                )
            ],
            "completed_nodes": ["section_assembler"],
        }

    section_dict = section.model_dump(exclude_none=True)

    # -- Layer 3a: Contract compliance -----------------------------------------
    is_valid, violations = validate_section_for_template(
        section_dict, state.contract.id
    )

    if not is_valid:
        return {
            "errors": [
                PipelineError(
                    node="section_assembler",
                    section_id=sid,
                    message=f"Contract violation: {'; '.join(violations)}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["section_assembler"],
        }

    # -- Layer 3b: Capacity limits ---------------------------------------------
    capacity_warnings = _check_capacity(section_dict)

    # Capacity warnings are non-blocking -- section is assembled regardless.
    # The QC agent will see these and can escalate if they degrade learning.
    qc_report = QCReport(
        section_id=sid,
        passed=True,
        issues=[],
        warnings=capacity_warnings,
    )

    assembled = dict(state.assembled_sections)
    assembled[sid] = section

    reports = dict(state.qc_reports)
    reports[sid] = qc_report

    return {
        "assembled_sections": assembled,
        "qc_reports": reports,
        "completed_nodes": ["section_assembler"],
    }
