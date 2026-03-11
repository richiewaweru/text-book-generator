import pytest

from textbook_agent.infrastructure.providers.factory import ProviderFactory
from textbook_agent.infrastructure.providers.anthropic_provider import AnthropicProvider
from textbook_agent.infrastructure.providers.openai_provider import OpenAIProvider


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
        assert ProviderFactory.get("claude").name() == "claude-sonnet-4-6"
        assert ProviderFactory.get("openai").name() == "gpt-4o"
