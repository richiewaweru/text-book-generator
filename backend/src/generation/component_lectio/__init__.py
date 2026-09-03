"""Component Lectio package — canonical lesson generation path (non-Studio)."""

from generation.component_lectio.pipeline import (
    PipelineResult,
    mock_writer,
    run_mocked_component_lectio_pipeline,
)
from generation.component_lectio.service import (
    adapt_exact_orders_to_section_work_orders,
    fill_plan_components_for_legacy_studio,
    load_ready_block_ids,
    reconstruct_checkpoint_store,
    run_component_lectio_execution,
)

__all__ = [
    "PipelineResult",
    "adapt_exact_orders_to_section_work_orders",
    "fill_plan_components_for_legacy_studio",
    "load_ready_block_ids",
    "mock_writer",
    "reconstruct_checkpoint_store",
    "run_component_lectio_execution",
    "run_mocked_component_lectio_pipeline",
]
