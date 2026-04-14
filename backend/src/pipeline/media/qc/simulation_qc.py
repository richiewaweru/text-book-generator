from __future__ import annotations

from pipeline.media.types import VisualSlot
from pipeline.types.section_content import DiagramContent, SimulationContent


def validate_simulation_content(
    *,
    slot: VisualSlot,
    simulation: SimulationContent | None,
    fallback_diagram: DiagramContent | None,
) -> list[str]:
    issues: list[str] = []
    if simulation is None:
        issues.append("simulation content is missing")
        return issues
    if simulation.spec is None:
        issues.append("simulation spec is missing")
    if not (simulation.html_content or "").strip():
        issues.append("simulation html_content is missing")
    if slot.expects_static_fallback and fallback_diagram is None:
        issues.append("simulation fallback_diagram is required for print translation")
    return issues
