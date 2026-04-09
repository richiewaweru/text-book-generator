"""
Deterministic. No LLM.

Validates assembled section content against the template contract
(Layer 3a: contract compliance, Layer 3b: capacity limits).

STATE CONTRACT
    Reads:  current_section_id, generated_sections, contract
    Writes: partial_sections/current_section_id or assembled_sections[current_section_id],
            qc_reports (capacity warnings), completed_nodes, errors
    Model:  none
    Skips:  never
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from pipeline.contracts import validate_section_for_template
from pipeline.console_diagnostics import force_console_log
from pipeline.section_assets import pending_visual_fields, required_visual_fields
from pipeline.state import (
    PartialSectionRecord,
    PipelineError,
    QCReport,
    TextbookPipelineState,
)
from pipeline.visual_resolution import resolve_visual_issue


def diag(tag: str, **fields) -> None:
    sys.stderr.write(f"DIAG::{tag}::{json.dumps(fields, default=str)}\n")
    sys.stderr.flush()


diag("BUILD_MARKER", file="section_assembler", version="diag_v1")


def _check_capacity(section_dict: dict) -> list[str]:
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
    for index, problem in enumerate(problems):
        hints = problem.get("hints", [])
        if len(hints) > 3:
            warnings.append(
                f"practice problem {index + 1} has {len(hints)} hints -- max 3"
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
    model_overrides: dict | None = None,
) -> dict:
    return await _assemble_section(state, mode="final", model_overrides=model_overrides)


async def partial_section_assembler(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    return await _assemble_section(state, mode="partial", model_overrides=model_overrides)


async def _assemble_section(
    state: TextbookPipelineState | dict,
    *,
    mode: str,
    model_overrides: dict | None = None,
) -> dict:
    _ = model_overrides
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    node_name = "partial_section_assembler" if mode == "partial" else "section_assembler"
    force_console_log(
        "FINALIZE",
        "START",
        section_id=section_id,
        mode=mode,
    )

    section = typed.generated_sections.get(section_id)
    if not section:
        force_console_log(
            "FINALIZE",
            "MISSING_SECTION",
            section_id=section_id,
            mode=mode,
        )
        return {
            "errors": [
                PipelineError(
                    node=node_name,
                    section_id=section_id,
                    message=(
                        f"No generated content found for section {section_id}. "
                        "content_generator may have failed."
                    ),
                    recoverable=False,
                )
            ],
            "completed_nodes": [node_name],
        }

    section_dict = section.model_dump(exclude_none=True)
    visual_issue = resolve_visual_issue(typed)
    if mode == "final" and visual_issue:
        force_console_log(
            "FINALIZE",
            "VISUAL_ISSUE",
            section_id=section_id,
            mode=mode,
            message=visual_issue,
        )
        return {
            "errors": [
                PipelineError(
                    node=node_name,
                    section_id=section_id,
                    message=visual_issue,
                    recoverable=True,
                )
            ],
            "completed_nodes": [node_name],
        }

    pending_assets = pending_visual_fields(typed)
    if mode == "final" and pending_assets:
        force_console_log(
            "FINALIZE",
            "AWAITING_ASSETS",
            section_id=section_id,
            mode=mode,
            pending_assets=pending_assets,
        )
        partials = dict(typed.partial_sections)
        partials[section_id] = PartialSectionRecord(
            section_id=section.section_id,
            template_id=section.template_id,
            content=section,
            status="awaiting_assets",
            pending_assets=pending_assets,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        lifecycle = dict(typed.section_lifecycle)
        lifecycle[section_id] = "awaiting_assets"
        return {
            "partial_sections": partials,
            "section_pending_assets": {section_id: pending_assets},
            "section_lifecycle": lifecycle,
            "completed_nodes": [node_name],
        }

    is_valid, violations = validate_section_for_template(
        section_dict,
        typed.contract.id,
        mode=mode,
        allow_missing_fields=set(pending_assets),
        additional_required_fields=set(required_visual_fields(typed)),
    )
    if not is_valid:
        payload = {
            "section_id": section_id,
            "violations": violations,
            "required_components": getattr(typed.contract, "required_components", None),
            "always_present": getattr(typed.contract, "always_present", None),
            "available_components": getattr(typed.contract, "available_components", None),
            "section_has_diagram": getattr(section, "diagram", None) is not None,
        }
        diag("ASSEMBLER_CONTRACT_VIOLATION", **payload)
        if any("diagram" in violation.lower() for violation in violations):
            diag("ASSEMBLER_MISSING_DIAGRAM", **payload)
        force_console_log(
            "FINALIZE",
            "CONTRACT_VIOLATION",
            section_id=section_id,
            mode=mode,
            violations=violations,
        )
        return {
            "errors": [
                PipelineError(
                    node=node_name,
                    section_id=section_id,
                    message=f"Contract violation: {'; '.join(violations)}",
                    recoverable=True,
                )
            ],
            "completed_nodes": [node_name],
        }

    qc_report = QCReport(
        section_id=section_id,
        passed=True,
        issues=[],
        warnings=_check_capacity(section_dict),
    )
    reports = dict(typed.qc_reports)
    reports[section_id] = qc_report

    if mode == "partial":
        partials = dict(typed.partial_sections)
        partials[section_id] = PartialSectionRecord(
            section_id=section.section_id,
            template_id=section.template_id,
            content=section,
            status="awaiting_assets" if pending_assets else "partial",
            pending_assets=pending_assets,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        lifecycle = dict(typed.section_lifecycle)
        lifecycle[section_id] = "awaiting_assets" if pending_assets else "partial"
        return {
            "partial_sections": partials,
            "section_pending_assets": {section_id: pending_assets},
            "section_lifecycle": lifecycle,
            "qc_reports": reports,
            "completed_nodes": [node_name],
        }

    assembled = dict(typed.assembled_sections)
    assembled[section_id] = section
    lifecycle = dict(typed.section_lifecycle)
    lifecycle[section_id] = "final"
    force_console_log(
        "FINALIZE",
        "ASSEMBLED",
        section_id=section_id,
        mode=mode,
    )
    return {
        "assembled_sections": assembled,
        "section_pending_assets": {section_id: []},
        "section_lifecycle": lifecycle,
        "qc_reports": reports,
        "completed_nodes": [node_name],
    }
