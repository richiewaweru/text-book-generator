"""Gemini Imagen client for diagram image generation."""

from __future__ import annotations

import asyncio
from io import BytesIO

from pipeline.providers.image_client import (
    ImageFormat,
    ImageGenerationResult,
    ImageSize,
)


class GeminiImageClient:
    """Gemini Imagen implementation of the ImageModelClient protocol."""

    def __init__(
        self,
        api_key: str,
        model: str = "imagen-3.0-generate-001",
    ):
        self.api_key = api_key
        self.model = model
        self._client: object | None = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_image(
        self,
        *,
        prompt: str,
        size: ImageSize = "1024x1024",
        format: ImageFormat = "png",
        seed: int | None = None,
    ) -> ImageGenerationResult:
        """Generate an educational diagram image."""
        from google.genai.types import GenerateImageConfig

        config = GenerateImageConfig(
            number_of_images=1,
            negative_prompt="blurry, low quality, distorted, text overlay",
        )

        if seed is not None:
            config.seed = seed

        try:
            client = self._get_client()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_images(
                    model=self.model,
                    prompt=prompt,
                    config=config,
                ),
            )

            pil_image = response.images[0]._pil_image
            buffer = BytesIO()
            pil_image.save(buffer, format=format.upper())

            return ImageGenerationResult(
                bytes=buffer.getvalue(),
                format=format,
                mime_type=f"image/{format}",
            )
        except Exception as e:
            raise RuntimeError(f"Gemini image generation failed: {e}") from e
