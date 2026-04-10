"""
pipeline.routers.qc_router

Decides what happens after QC (now inline in process_section) runs.

Returns END when all sections pass or on unrecoverable errors.
Returns list[Send] to fan out retries for failing sections, routed to
the narrowest possible retry scope:
    - diagram-only failures  -> retry_diagram  (re-runs diagram + assembler + QC)
    - text field failures    -> retry_field    (re-generates one field via FAST LLM)
    - unknown / multi-field  -> process_section (full rerun)
"""

import core.events as core_events
from langgraph.graph import END
from langgraph.types import Send

from pipeline.events import InteractionRetryQueuedEvent
from pipeline.state import TextbookPipelineState

# Diagram component blocks that retry_diagram handles.
_DIAGRAM_FIELDS = {"diagram", "diagram_series", "diagram_compare"}

# Interaction/simulation component blocks that retry_interaction handles.
_INTERACTION_FIELDS = {"simulation", "simulation_block"}

# Text fields that field_regenerator handles (targeted single-field retry).
_TEXT_FIELDS = {
    "hook", "explanation", "practice", "worked_example",
    "definition", "pitfall", "glossary", "what_next",
}


def _classify_retry_scope(blocking_issues: list[dict]) -> str:
    """Classify the narrowest retry scope for a set of blocking issues.

    Returns one of: "diagram", "interaction", "field", "full".
    """
    blocks = {i.get("block", "") for i in blocking_issues}
    if blocks and blocks <= _DIAGRAM_FIELDS:
        return "diagram"
    if blocks and blocks <= _INTERACTION_FIELDS:
        return "interaction"
    if len(blocks) == 1 and blocks <= _TEXT_FIELDS:
        # Single text field failure — can be fixed with a targeted LLM call
        return "field"
    # Mixed diagram + interaction only (no text) → drain diagram first
    if blocks and blocks <= (_DIAGRAM_FIELDS | _INTERACTION_FIELDS):
        return "diagram"
    return "full"


def _publish_interaction_retry_queued(
    generation_id: str,
    section_id: str,
    *,
    next_attempt: int,
    blocking_issues: list[dict],
) -> None:
    if not generation_id:
        return
    reasons = [
        issue.get("message") or issue.get("block") or ""
        for issue in blocking_issues
        if issue.get("message") or issue.get("block")
    ]
    core_events.event_bus.publish(
        generation_id,
        InteractionRetryQueuedEvent(
            generation_id=generation_id,
            section_id=section_id,
            next_attempt=next_attempt,
            reason="; ".join(reasons),
        ),
    )


def route_after_qc(state: TextbookPipelineState | dict) -> list[Send] | str:
    """
    Route after QC:
        - Unrecoverable errors -> END
        - Sections with blocking issues (under rerender limit) -> fan-out Send
        - All pass -> END
    """
    state = TextbookPipelineState.parse(state)

    # Unrecoverable errors -> stop
    if any(not e.recoverable for e in state.errors):
        return END

    section_ids = (
        [state.current_section_id]
        if state.current_section_id is not None
        else list(state.qc_reports.keys())
    )

    sends = []
    for section_id in section_ids:
        if section_id is None:
            continue

        pending = state.pending_rerender_for(section_id)
        if pending is not None:
            if not state.can_rerender(section_id):
                continue
            blocking = [
                {
                    "severity": "blocking",
                    "block": pending.block_type,
                    "message": pending.reason,
                }
            ]
        else:
            report = state.qc_reports.get(section_id)
            if report is None:
                continue
            blocking = [
                issue
                for issue in report.issues
                if issue.get("severity") == "blocking"
            ]
            if not blocking or not state.can_rerender(section_id):
                continue

        plan = next(
            (
                p
                for p in (state.curriculum_outline or [])
                if p.section_id == section_id
            ),
            None,
        )
        if not plan:
            continue

        base = {
            **state.model_dump(),
            "current_section_id": section_id,
            "current_section_plan": plan.model_dump(),
        }

        scope = _classify_retry_scope(blocking)
        if scope == "diagram":
            if state.diagram_retry_count.get(section_id, 0) >= 1:
                continue  # diagram budget exhausted, accept section without diagram
            sends.append(Send("retry_diagram", base))
        elif scope == "interaction":
            if state.interaction_retry_count.get(section_id, 0) >= 1:
                continue  # interaction budget exhausted, accept section without interaction
            _publish_interaction_retry_queued(
                state.request.generation_id or "",
                section_id,
                next_attempt=state.interaction_retry_count.get(section_id, 0) + 2,
                blocking_issues=blocking,
            )
            sends.append(Send("retry_interaction", base))
        elif scope == "field":
            sends.append(Send("retry_field", base))
        else:
            sends.append(Send("process_section", base))

    if sends:
        return sends

    return END
