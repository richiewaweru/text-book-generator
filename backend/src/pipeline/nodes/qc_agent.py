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
from datetime import datetime, timezone

from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel
from pydantic_ai import Agent

from core.config import settings as app_settings
from pipeline.section_assets import is_required_visual_block
from pipeline.prompts.qc import build_qc_system_prompt, build_qc_user_prompt
from pipeline.providers.registry import get_node_text_model
from pipeline.runtime_context import retry_policy_for_node
from pipeline.runtime_policy import resolve_runtime_policy_bundle
from pipeline.state import (
    FailedSectionRecord,
    NodeFailureDetail,
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


def _terminal_qc_failure_record(
    *,
    state: TextbookPipelineState,
    section_id: str,
    block_type: str,
    reason: str,
) -> FailedSectionRecord:
    plan = state.current_section_plan
    failure_detail = NodeFailureDetail(
        node="qc_agent",
        section_id=section_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        error_type="blocking_qc_failure",
        error_message=reason,
        retry_attempt=state.rerender_count.get(section_id, 0),
        will_retry=False,
    )
    return FailedSectionRecord(
        section_id=section_id,
        title=plan.title if plan is not None else section_id,
        position=plan.position if plan is not None else 0,
        focus=plan.focus if plan is not None else None,
        bridges_from=plan.bridges_from if plan is not None else None,
        bridges_to=plan.bridges_to if plan is not None else None,
        needs_diagram=plan.needs_diagram if plan is not None else False,
        needs_worked_example=plan.needs_worked_example if plan is not None else False,
        failed_at_node="qc_agent",
        error_type="blocking_qc_failure",
        error_summary=reason,
        attempt_count=state.rerender_count.get(section_id, 0) + 1,
        can_retry=False,
        missing_components=[block_type],
        failure_detail=failure_detail,
    )


async def qc_agent(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
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
    errors = []
    rerender_updates: dict[str, RerenderRequest | None] = {}
    failed_sections: dict[str, FailedSectionRecord] = {}
    lifecycle_updates: dict[str, str] = {}
    pending_asset_updates: dict[str, list[str]] = {}

    section_id = state.current_section_id
    section = state.assembled_sections.get(section_id) if section_id else None
    if section_id is None or section is None:
        return {"completed_nodes": ["qc_agent"]}

    try:
        retry_policy = retry_policy_for_node(config, "qc_agent")
        if retry_policy is None:
            retry_policy = resolve_runtime_policy_bundle(
                app_settings,
                state.request.mode,
            ).retries.for_node("qc_agent")
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
            retry_policy=retry_policy,
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
        if blocking:
            block_type = blocking[0].get("block", "unknown")
            reason = blocking[0].get("message", "QC failed")
            diagram_budget_exhausted = (
                block_type in {"diagram", "diagram_compare", "diagram_series"}
                and state.diagram_retry_count.get(section_id, 0) >= 1
            )
            if diagram_budget_exhausted and is_required_visual_block(state, block_type):
                failed_sections[section_id] = _terminal_qc_failure_record(
                    state=state,
                    section_id=section_id,
                    block_type=block_type,
                    reason=reason,
                )
                lifecycle_updates[section_id] = "failed"
                pending_asset_updates[section_id] = []
                rerender_updates[section_id] = None
            elif not diagram_budget_exhausted and state.can_rerender(section_id):
                rerender_updates[section_id] = RerenderRequest(
                    section_id=section_id,
                    block_type=block_type,
                    reason=reason,
                )
            else:
                rerender_updates[section_id] = None
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
    if failed_sections:
        output["failed_sections"] = failed_sections
    if lifecycle_updates:
        output["section_lifecycle"] = lifecycle_updates
    if pending_asset_updates:
        output["section_pending_assets"] = pending_asset_updates
    if errors:
        output["errors"] = errors

    return output
