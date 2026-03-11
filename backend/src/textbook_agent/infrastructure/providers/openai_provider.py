import logging
from typing import Any

import openai

from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.exceptions import ProviderConformanceError
from .json_utils import extract_json

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI GPT-4 LLM provider implementation."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o") -> None:
        self.api_key = api_key
        self.model = model
        self._client = openai.OpenAI(api_key=api_key) if api_key else None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Any:
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key)

        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.choices[0].message.content or ""
        logger.debug("OpenAI raw response: %s", raw_text[:500])

        try:
            data = extract_json(raw_text)
            return response_schema.model_validate(data)
        except Exception as exc:
            raise ProviderConformanceError(
                provider_name=self.model,
                schema_name=response_schema.__name__,
            ) from exc

    def name(self) -> str:
        return self.model
