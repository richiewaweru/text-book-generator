from __future__ import annotations

from pipeline.media.types import VisualFrame, VisualSlot


def build_simulation_prompt(*, section_title: str, slot: VisualSlot, frame: VisualFrame) -> str:
    must_include = ", ".join(frame.must_include) if frame.must_include else "core concepts"
    return (
        f"Create one self-contained HTML simulation for {section_title}. "
        f"Simulation type: {slot.simulation_type or 'graph_slider'}. "
        f"Goal: {slot.simulation_goal or slot.simulation_intent or slot.pedagogical_intent}. "
        f"Anchor block: {slot.anchor_block or 'explanation'}. "
        f"Frame goal: {frame.generation_goal}. "
        f"Must include: {must_include}. "
        "Return one iframe-safe HTML document with inline CSS and inline JavaScript only. "
        "Do not rely on external fonts, scripts, network requests, or window.parent access. "
        "Make the interaction obvious, classroom-safe, and readable on both desktop and narrow widths."
    )
