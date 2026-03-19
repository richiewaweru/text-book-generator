"""
pipeline.routers.qc_router

Decides what happens after qc_agent runs.

Returns END when all sections pass or on unrecoverable errors.
Returns list[Send] to fan out rerender for failing sections.
"""

from langgraph.graph import END
from langgraph.types import Send

from pipeline.state import TextbookPipelineState


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

    # Find sections needing rerender
    sends = []
    for section_id, report in state.qc_reports.items():
        blocking = [
            i for i in report.issues if i.get("severity") == "blocking"
        ]
        if blocking and state.can_rerender(section_id):
            plan = next(
                (
                    p
                    for p in (state.curriculum_outline or [])
                    if p.section_id == section_id
                ),
                None,
            )
            if plan:
                sends.append(
                    Send(
                        "process_section",
                        {
                            **state.model_dump(),
                            "current_section_id": section_id,
                            "current_section_plan": plan.model_dump(),
                        },
                    )
                )

    if sends:
        return sends

    return END
