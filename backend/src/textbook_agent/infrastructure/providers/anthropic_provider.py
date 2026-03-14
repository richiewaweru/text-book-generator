import logging
from typing import Any

import anthropic

from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.exceptions import (
    ProviderConformanceError,
    ProviderRequestError,
)
from .json_utils import extract_json, to_strict_json_schema

logger = logging.getLogger(__name__)


def _extract_api_error_message(exc: anthropic.APIStatusError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
    return str(exc)


def _format_bad_request_detail(exc: anthropic.BadRequestError) -> str:
    message = _extract_api_error_message(exc)
    if "credit balance is too low" in message.lower():
        return (
            "Anthropic reports that the API credit balance for the workspace behind "
            "this key is too low. If you recently added credits, confirm "
            "`ANTHROPIC_API_KEY` belongs to the funded workspace and restart the "
            "backend if you changed `backend/.env`."
        )
    return message


class AnthropicProvider(BaseProvider):
    """Claude LLM provider implementation."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.default_max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> Any:
        max_tokens = max_tokens or self.default_max_tokens
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        selected_model = model or self.model

        tool_name = f"return_{response_schema.__name__.lower()}"
        try:
            message = self._client.messages.create(
                model=selected_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[
                    {
                        "name": tool_name,
                        "description": f"Return a response that matches the {response_schema.__name__} schema.",
                        "input_schema": to_strict_json_schema(
                            response_schema.model_json_schema()
                        ),
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
            )
        except anthropic.AuthenticationError as exc:
            raise ProviderRequestError(
                provider_name=selected_model,
                detail=(
                    "Anthropic authentication failed. Check that `ANTHROPIC_API_KEY` "
                    "is valid and belongs to the intended workspace."
                ),
            ) from exc
        except anthropic.BadRequestError as exc:
            raise ProviderRequestError(
                provider_name=selected_model,
                detail=_format_bad_request_detail(exc),
            ) from exc

        try:
            data = None
            for block in message.content:
                if getattr(block, "type", None) == "tool_use":
                    data = block.input
                    break

            if data is None:
                raw_text = message.content[0].text
                logger.debug("Anthropic raw response: %s", raw_text[:500])
                data = extract_json(raw_text)

            return response_schema.model_validate(data)
        except Exception as exc:
            raise ProviderConformanceError(
                provider_name=selected_model,
                schema_name=response_schema.__name__,
            ) from exc

    def name(self) -> str:
        return self.model
