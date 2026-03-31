"""
qc_agent node -- real implementation.

Performs semantic quality control on assembled sections.
Structural validation (schema, capacity) is already done by section_assembler.
This node checks whether the content actually teaches well.

STATE CONTRACT
    Reads:  current_section_id, assembled_sections, qc_reports
            (capacity warnings from assembler), contract, rerender_count,
            max_rerenders
    Writes: qc_reports (semantic issues added), rerender_requests,
            completed_nodes, errors
    Slot:   FAST
    Skips:  never
"""

from __future__ import annotations

import json

from pydantic import BaseModel
from pydantic_ai import Agent

from pipeline.prompts.qc import build_qc_system_prompt, build_qc_user_prompt
from pipeline.providers.registry import get_node_text_model
from pipeline.state import (
    PipelineError,
    QCReport,
    RerenderRequest,
    TextbookPipelineState,
)
from pipeline.llm_runner import run_llm


class QCOutput(BaseModel):
    passed: bool
    issues: list[dict]
    warnings: list[str]


async def qc_agent(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Run semantic quality checks and request rerenders for blocking issues."""

    state = TextbookPipelineState.parse(state)

    model = get_node_text_model(
        "qc_agent",
        model_overrides=model_overrides,
    )
    agent = Agent(
        model=model,
        output_type=QCOutput,
        system_prompt=build_qc_system_prompt(state.contract.id),
    )

    reports = dict(state.qc_reports)
    errors = []
    rerender_updates: dict[str, RerenderRequest | None] = {}

    section_id = state.current_section_id
    section = state.assembled_sections.get(section_id) if section_id else None
    if section_id is None or section is None:
        return {"completed_nodes": ["qc_agent"]}

    try:
        section_json = json.dumps(
            (
                section.model_dump(exclude_none=True)
                if hasattr(section, "model_dump")
                else section
            ),
            indent=2,
        )

        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="qc_agent",
            agent=agent,
            model=model,
            user_prompt=build_qc_user_prompt(section_json),
            section_id=section_id,
        )

        qc_output = result.output

        # Preserve assembler warnings, then append semantic QC warnings.
        existing = reports.get(section_id)
        existing_warnings = existing.warnings if existing else []

        reports[section_id] = QCReport(
            section_id=section_id,
            passed=qc_output.passed,
            issues=qc_output.issues,
            warnings=existing_warnings + qc_output.warnings,
        )

        blocking = [
            issue
            for issue in qc_output.issues
            if issue.get("severity") == "blocking"
        ]
        if blocking and state.can_rerender(section_id):
            rerender_updates[section_id] = RerenderRequest(
                section_id=section_id,
                block_type=blocking[0].get("block", "unknown"),
                reason=blocking[0].get("message", "QC failed"),
            )
        else:
            rerender_updates[section_id] = None

    except Exception as exc:
        errors.append(
            PipelineError(
                node="qc_agent",
                section_id=section_id,
                message=f"QC evaluation failed: {exc}",
                recoverable=True,
            )
        )

    output: dict = {
        "qc_reports": reports,
        "completed_nodes": ["qc_agent"],
    }
    if rerender_updates:
        output["rerender_requests"] = rerender_updates
    if errors:
        output["errors"] = errors

    return output
