from __future__ import annotations

from pipeline.media.providers.openai_image_client import OpenAICompatibleImageClient


class XAIImageClient(OpenAICompatibleImageClient):
    DEFAULT_MODEL = "grok-2-image"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(api_key=api_key, model_name=model_name, base_url=base_url)
