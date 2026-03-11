from abc import ABC, abstractmethod

from textbook_agent.domain.entities.generation_context import GenerationContext


class FileStoragePort(ABC):
    """Abstract file storage interface for reading profiles and writing outputs."""

    @abstractmethod
    def read_profile(self, path: str) -> GenerationContext:
        """Read a learner profile from a JSON file."""
        ...

    @abstractmethod
    def write_output(self, path: str, content: str) -> None:
        """Write content to a file at the given path."""
        ...
