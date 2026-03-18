from __future__ import annotations

from typing import Any, Mapping

from pydantic_ai.models.anthropic import AnthropicModel

from pipeline.providers.base import AbstractLLMProvider, LLMResponse


class AnthropicLLMProvider(AbstractLLMProvider):
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = AnthropicModel(model_name)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        # pydantic-ai AnthropicModel is itself a model backend; the higher-level
        # pipeline nodes will use this via pydantic-ai run contexts. For now,
        # we surface a minimal text response and keep the raw model available.
        # The text is not produced here; callers are expected to use `_model`
        # directly when integrating with pydantic-ai's run API.
        return LLMResponse(text="", raw=self._model)


def build_anthropic_provider(model_name: str) -> AnthropicLLMProvider:
    return AnthropicLLMProvider(model_name)

