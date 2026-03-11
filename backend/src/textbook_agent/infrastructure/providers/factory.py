from textbook_agent.domain.ports.llm_provider import BaseProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider


class ProviderFactory:
    """Factory for creating LLM provider instances."""

    _registry: dict[str, type[BaseProvider]] = {
        "claude": AnthropicProvider,
        "openai": OpenAIProvider,
    }

    @classmethod
    def get(cls, name: str, **kwargs) -> BaseProvider:
        if name not in cls._registry:
            raise ValueError(
                f"Unknown provider: {name}. Available: {list(cls._registry.keys())}"
            )
        return cls._registry[name](**kwargs)
