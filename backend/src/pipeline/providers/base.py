from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass
class LLMResponse:
    """Unified response type for pipeline LLM calls."""

    text: str
    raw: Any


class BaseLLMProvider(Protocol):
    """Lightweight LLM provider interface for the pipeline.

    This intentionally mirrors the domain's BaseProvider shape at a high level,
    but stays decoupled so the pipeline can evolve independently if needed.
    """

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        ...


class AbstractLLMProvider(ABC):
    """Optional ABC base for concrete implementations."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        ...

