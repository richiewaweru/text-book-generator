"""
qc_agent node -- real implementation.

Performs semantic quality control on assembled sections.
Structural validation (schema, capacity) is already done by section_assembler.
This node checks whether the content actually teaches well.

STATE CONTRACT
    Reads:  assembled_sections, qc_reports (capacity warnings from assembler),
            contract, rerender_count, max_rerenders
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
        generation_mode=state.request.mode,
    )
    agent = Agent(
        model=model,
        output_type=QCOutput,
        system_prompt=build_qc_system_prompt(state.contract.id),
    )

    reports = dict(state.qc_reports)
    rerender_reqs = []
    errors = []

    for section_id, section in state.assembled_sections.items():
        # Skip if already exceeded rerender limit for this section
        if state.rerender_count.get(section_id, 0) >= state.max_rerenders:
            continue

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
                generation_mode=state.request.mode,
            )

            qc_output = result.output

            # Merge semantic issues with existing capacity warnings
            existing = reports.get(section_id)
            existing_warnings = existing.warnings if existing else []

            reports[section_id] = QCReport(
                section_id=section_id,
                passed=qc_output.passed,
                issues=qc_output.issues,
                warnings=existing_warnings + qc_output.warnings,
            )

            # If blocking issues found, request a rerender
            blocking = [
                i
                for i in qc_output.issues
                if i.get("severity") == "blocking"
            ]
            if blocking:
                rerender_reqs.append(
                    RerenderRequest(
                        section_id=section_id,
                        block_type=blocking[0].get("block", "unknown"),
                        reason=blocking[0].get("message", "QC failed"),
                    )
                )

        except Exception as e:
            errors.append(
                PipelineError(
                    node="qc_agent",
                    section_id=section_id,
                    message=f"QC evaluation failed: {e}",
                    recoverable=True,
                )
            )

    output: dict = {
        "qc_reports": reports,
        "completed_nodes": ["qc_agent"],
    }
    if rerender_reqs:
        output["rerender_requests"] = rerender_reqs
    if errors:
        output["errors"] = errors

    return output
