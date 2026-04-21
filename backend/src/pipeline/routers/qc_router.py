"""
pipeline.routers.qc_router

Routes post-section execution toward the narrowest valid retry:
    - media issues -> retry_media_frame
    - single text-field issues -> retry_field
    - other retryable issues -> process_section
"""

from __future__ import annotations

import json

import core.events as core_events  # noqa: F401
from langgraph.graph import END
from langgraph.types import Send

from pipeline.events import SectionRetryQueuedEvent
from pipeline.media.retry import (
    blocked_required_media,
    is_media_block,
    next_retry_request,
)
from pipeline.state import TextbookPipelineState
from pipeline.runtime_diagnostics import publish_runtime_event

_TEXT_FIELDS = {
    "hook",
    "explanation",
    "practice",
    "worked_example",
    "definition",
    "pitfall",
    "glossary",
    "what_next",
}


def _schema_failures_for_section(
    state: TextbookPipelineState,
    section_id: str,
) -> list[dict]:
    for error in reversed(state.errors):
        if error.node != "schema_validator" or error.section_id != section_id:
            continue
        try:
            payload = json.loads(error.message)
        except json.JSONDecodeError:
            return []
        failures = payload.get("failures", [])
        if isinstance(failures, list):
            return [failure for failure in failures if isinstance(failure, dict)]
        return []
    return []


def _schema_single_retry_field(failures: list[dict]) -> str | None:
    fields: set[str] = set()
    for failure in failures:
        field = str(failure.get("field", "")).strip()
        if not field or field == "<root>":
            continue
        root_field = field.split(".", 1)[0]
        fields.add(root_field)
    if len(fields) != 1:
        return None
    only_field = next(iter(fields))
    return only_field if only_field in _TEXT_FIELDS else None


def _blocking_issues_for_section(
    state: TextbookPipelineState,
    section_id: str,
) -> list[dict]:
    pending = state.pending_rerender_for(section_id)
    if pending is not None:
        return [
            {
                "severity": "blocking",
                "block": pending.block_type,
                "message": pending.reason,
            }
        ]

    report = state.qc_reports.get(section_id)
    if report is None:
        return []
    return [
        issue
        for issue in report.issues
        if issue.get("severity") == "blocking"
    ]


def _is_single_field_retry(blocking_issues: list[dict]) -> bool:
    blocks = {issue.get("block", "") for issue in blocking_issues}
    return len(blocks) == 1 and blocks <= _TEXT_FIELDS


def _publish_retry_queued(
    state: TextbookPipelineState,
    *,
    section_id: str,
    block_type: str,
    reason: str,
) -> None:
    generation_id = state.request.generation_id or ""
    publish_runtime_event(
        generation_id,
        SectionRetryQueuedEvent(
            generation_id=generation_id,
            section_id=section_id,
            reason=reason,
            block_type=block_type,
            next_attempt=state.rerender_count.get(section_id, 0) + 2,
            max_attempts=state.max_rerenders + 1,
        ),
    )


def route_after_qc(state: TextbookPipelineState | dict) -> list[Send] | str:
    state = TextbookPipelineState.parse(state)

    if any(not error.recoverable for error in state.errors):
        return END

    section_ids = (
        [state.current_section_id]
        if state.current_section_id is not None
        else list(state.media_plans.keys() or state.qc_reports.keys())
    )

    sends: list[Send] = []
    for section_id in section_ids:
        if section_id is None:
            continue

        plan = next(
            (
                section_plan
                for section_plan in (state.curriculum_outline or [])
                if section_plan.section_id == section_id
            ),
            None,
        )
        if plan is None:
            continue

        schema_failures = _schema_failures_for_section(state, section_id)
        if schema_failures and state.can_rerender(section_id):
            retry_field = _schema_single_retry_field(schema_failures)
            base = {
                **state.model_dump(),
                "current_section_id": section_id,
                "current_section_plan": plan.model_dump(),
            }
            if retry_field:
                _publish_retry_queued(
                    state,
                    section_id=section_id,
                    block_type=retry_field,
                    reason=f"Schema validation failed for field '{retry_field}'.",
                )
                sends.append(Send("retry_field", base))
            else:
                _publish_retry_queued(
                    state,
                    section_id=section_id,
                    block_type="schema_validator",
                    reason="Schema validation failed across multiple fields.",
                )
                sends.append(Send("process_section", base))
            continue

        blocking_issues = _blocking_issues_for_section(state, section_id)
        media_candidate = next_retry_request(
            state,
            section_id=section_id,
            blocking_issues=blocking_issues,
        )
        media_blocked = blocked_required_media(state, section_id=section_id)
        blocking_media_issue = any(is_media_block(issue.get("block")) for issue in blocking_issues)
        has_any_blocking = bool(blocking_issues)

        base = {
            **state.model_dump(),
            "current_section_id": section_id,
            "current_section_plan": plan.model_dump(),
        }

        if media_candidate is not None and (blocking_media_issue or media_blocked.blocked or not has_any_blocking):
            _publish_retry_queued(
                state,
                section_id=section_id,
                block_type=media_candidate.slot_type,
                reason=media_candidate.reason or "Retrying required media frame.",
            )
            sends.append(
                Send(
                    "retry_media_frame",
                    {
                        **base,
                        "current_media_retry": media_candidate.model_dump(),
                    },
                )
            )
            continue

        if media_blocked.blocked:
            continue

        if has_any_blocking and _is_single_field_retry(blocking_issues) and state.can_rerender(section_id):
            _publish_retry_queued(
                state,
                section_id=section_id,
                block_type=blocking_issues[0].get("block", "field"),
                reason=blocking_issues[0].get("message", "Retrying field."),
            )
            sends.append(Send("retry_field", base))
            continue

        if has_any_blocking and state.can_rerender(section_id):
            _publish_retry_queued(
                state,
                section_id=section_id,
                block_type=blocking_issues[0].get("block", "full"),
                reason=blocking_issues[0].get("message", "Retrying section."),
            )
            sends.append(Send("process_section", base))

    return sends or END
