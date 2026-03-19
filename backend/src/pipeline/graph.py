"""
pipeline.graph

The LangGraph generation graph. Curriculum planner fans out into
per-section mini-pipelines (process_section), then QC runs over everything.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import Send

from pipeline.nodes.curriculum_planner import curriculum_planner
from pipeline.nodes.process_section import process_section
from pipeline.nodes.qc_agent import qc_agent
from pipeline.routers.qc_router import route_after_qc
from pipeline.state import TextbookPipelineState


def fan_out_sections(state: TextbookPipelineState | dict) -> list[Send]:
    """Fan out one composite mini-pipeline per section after curriculum_planner."""
    state = TextbookPipelineState.parse(state)
    if not state.curriculum_outline:
        return []

    base = state.model_dump()
    return [
        Send("process_section", {
            **base,
            "current_section_id": plan.section_id,
            "current_section_plan": plan.model_dump(),
        })
        for plan in state.curriculum_outline
    ]


def build_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(TextbookPipelineState)

    # Register nodes
    workflow.add_node("curriculum_planner", curriculum_planner)
    workflow.add_node("process_section", process_section)
    workflow.add_node("qc_agent", qc_agent)

    # Entry point
    workflow.set_entry_point("curriculum_planner")

    # After curriculum_planner: fan out per section
    workflow.add_conditional_edges(
        "curriculum_planner",
        fan_out_sections,
    )

    # All sections join at QC
    workflow.add_edge("process_section", "qc_agent")

    # QC routes: router returns list[Send] for rerenders or END
    workflow.add_conditional_edges("qc_agent", route_after_qc)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())
