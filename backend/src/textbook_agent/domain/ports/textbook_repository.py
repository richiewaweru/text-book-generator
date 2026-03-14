from abc import ABC, abstractmethod

from textbook_agent.domain.entities.textbook import RawTextbook


class TextbookRepository(ABC):
    """Abstract repository for persisting generated textbooks."""

    @abstractmethod
    async def save(self, textbook: RawTextbook, html: str) -> str:
        """Save a rendered textbook. Returns the output path/ID."""
        ...

    @abstractmethod
    async def load_metadata(self, textbook_id: str) -> dict:
        """Load metadata for a previously generated textbook."""
        ...

    @abstractmethod
    async def load_html(self, output_path: str) -> str:
        """Load a previously rendered textbook HTML artifact."""
        ...

    @abstractmethod
    async def load_textbook(self, output_path: str) -> RawTextbook:
        """Load the saved textbook metadata for a rendered artifact."""
        ...
