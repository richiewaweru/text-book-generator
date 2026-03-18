from __future__ import annotations

from typing import Any, Mapping

from pipeline.providers.base import AbstractLLMProvider, LLMResponse


class OpenAILLMProvider(AbstractLLMProvider):
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        # Actual OpenAI client wiring lives in infrastructure; the pipeline
        # only needs a stable interface. This is a placeholder for future
        # direct OpenAI integration if desired.
        self._client = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError("OpenAI provider is not wired yet for pipeline use.")


def build_openai_provider(model_name: str) -> OpenAILLMProvider:
    return OpenAILLMProvider(model_name)

