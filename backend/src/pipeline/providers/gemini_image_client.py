from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache

from google import genai
from google.genai import types

from pipeline.providers.image_client import ImageFormat, ImageGenerationResult, ImageSize

logger = logging.getLogger(__name__)
_API_KEY_ENV_NAMES = (
    "GOOGLE_CLOUD_NANO_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
)


class GeminiImageClient:
    """
    Concrete ImageModelClient using gemini-3.1-flash-image-preview.

    The model returns mixed TEXT + IMAGE parts. We extract the first
    inline_data part (raw PNG bytes) and return it.
    """

    MODEL = "gemini-3.1-flash-image-preview"

    def __init__(self, *, api_key: str) -> None:
        self._client = genai.Client(vertexai=False, api_key=api_key)
        logger.info(
            "GeminiImageClient: initialised model=%s vertexai=False",
            self.MODEL,
        )

    async def generate_image(
        self,
        *,
        prompt: str,
        size: ImageSize = "1024x1024",
        format: ImageFormat = "png",
        seed: int | None = None,
    ) -> ImageGenerationResult:
        config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            max_output_tokens=32768,
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="OFF",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="OFF",
                ),
            ],
            image_config=types.ImageConfig(
                aspect_ratio="auto",
                image_size="1K",
                output_mime_type=f"image/{format}",
            ),
            thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            )
        ]

        def _call() -> bytes:
            image_bytes: bytes | None = None
            for chunk in self._client.models.generate_content_stream(
                model=self.MODEL,
                contents=contents,
                config=config,
            ):
                if not chunk.candidates:
                    continue
                for part in chunk.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_bytes = part.inline_data.data
                        break
                if image_bytes is not None:
                    break

            if image_bytes is None:
                raise RuntimeError("Gemini returned no image data in response")
            return image_bytes

        image_bytes = await asyncio.to_thread(_call)

        return ImageGenerationResult(
            bytes=image_bytes,
            format=format,
            mime_type=f"image/{format}",
        )


def resolve_gemini_image_api_key() -> str | None:
    for env_name in _API_KEY_ENV_NAMES:
        value = os.environ.get(env_name)
        if value:
            return value
    return None


@lru_cache(maxsize=1)
def get_gemini_image_client() -> GeminiImageClient:
    api_key = resolve_gemini_image_api_key()
    if not api_key:
        raise RuntimeError(
            "No Gemini API key found. Set GOOGLE_CLOUD_NANO_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY."
        )
    return GeminiImageClient(api_key=api_key)
