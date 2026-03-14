import anthropic
import httpx
import pytest
from pydantic import BaseModel

from textbook_agent.domain.exceptions import ProviderRequestError
from textbook_agent.infrastructure.providers.factory import ProviderFactory
from textbook_agent.infrastructure.providers.anthropic_provider import AnthropicProvider
from textbook_agent.infrastructure.providers.openai_provider import OpenAIProvider


class _Schema(BaseModel):
    value: str


class _AnthropicMessagesStub:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, **kwargs):
        raise self._exc


class _AnthropicClientStub:
    def __init__(self, exc: Exception) -> None:
        self.messages = _AnthropicMessagesStub(exc)


class TestProviderFactory:
    def test_get_claude_provider(self):
        provider = ProviderFactory.get("claude")
        assert isinstance(provider, AnthropicProvider)

    def test_get_openai_provider(self):
        provider = ProviderFactory.get("openai")
        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.get("unknown")

    def test_provider_names(self):
        assert ProviderFactory.get("claude").name() == "claude-sonnet-4-20250514"
        assert ProviderFactory.get("openai").name() == "gpt-5-mini"


class TestAnthropicProvider:
    def test_low_credit_errors_raise_provider_request_error(self):
        response = httpx.Response(
            400,
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        error = anthropic.BadRequestError(
            "Your credit balance is too low to access the Anthropic API.",
            response=response,
            body={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": (
                        "Your credit balance is too low to access the Anthropic API. "
                        "Please go to Plans & Billing to upgrade or purchase credits."
                    ),
                },
            },
        )
        provider = AnthropicProvider(api_key="")
        provider._client = _AnthropicClientStub(error)

        with pytest.raises(ProviderRequestError, match="funded workspace"):
            provider.complete(
                system_prompt="system",
                user_prompt="user",
                response_schema=_Schema,
            )
