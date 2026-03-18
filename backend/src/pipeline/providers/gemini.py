from __future__ import annotations

from typing import Any, Mapping

from pipeline.providers.base import AbstractLLMProvider, LLMResponse


class GeminiLLMProvider(AbstractLLMProvider):
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._client = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError("Gemini provider is not wired yet for pipeline use.")


def build_gemini_provider(model_name: str) -> GeminiLLMProvider:
    return GeminiLLMProvider(model_name)

