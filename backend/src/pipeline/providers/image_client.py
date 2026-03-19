from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


ImageSize = Literal["256x256", "512x512", "1024x1024"]
ImageFormat = Literal["png", "jpeg", "webp"]


@dataclass(frozen=True)
class ImageGenerationResult:
    """
    Pipeline-local result type for image generation.

    This is intentionally simple and transport-agnostic. Callers can decide
    whether to store bytes, persist to a file store, or forward a URL.
    """

    bytes: bytes
    format: ImageFormat
    mime_type: str


class ImageModelClient(Protocol):
    """
    Minimal interface for image generation models.

    This is separate from PydanticAI's text/vision model interface so the pipeline
    can evolve multi-modal support without forcing everything through `Agent`.
    """

    async def generate_image(
        self,
        *,
        prompt: str,
        size: ImageSize = "1024x1024",
        format: ImageFormat = "png",
        seed: int | None = None,
    ) -> ImageGenerationResult:
        ...

