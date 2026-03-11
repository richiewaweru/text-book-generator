from abc import ABC, abstractmethod

from textbook_agent.domain.entities.textbook import RawTextbook


class RendererPort(ABC):
    """Abstract renderer interface. Infrastructure provides concrete implementations."""

    @abstractmethod
    def render(self, textbook: RawTextbook) -> str:
        """Render a textbook to its output format (e.g. HTML). Returns the rendered string."""
        ...
