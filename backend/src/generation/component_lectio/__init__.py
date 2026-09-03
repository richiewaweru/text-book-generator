"""Component Lectio package — canonical lesson generation path (non-Studio)."""

from generation.component_lectio.pipeline import (
    PipelineResult,
    mock_writer,
    run_mocked_component_lectio_pipeline,
)

__all__ = [
    "PipelineResult",
    "mock_writer",
    "run_mocked_component_lectio_pipeline",
]
