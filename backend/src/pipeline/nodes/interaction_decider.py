"""
interaction_decider (DEPRECATED)

This node is retained as a thin shim for backward compatibility.
The spec-building logic has moved to interaction_generator._build_interaction_spec.
The node itself is now a no-op since interaction_generator handles everything.
"""

from __future__ import annotations

# Re-export for any external callers
from pipeline.nodes.interaction_generator import build_interaction_spec  # noqa: F401
from pipeline.state import TextbookPipelineState


async def interaction_decider(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """No-op shim — interaction_generator now handles spec building."""
    _ = model_overrides, state
    return {"completed_nodes": ["interaction_decider"]}
