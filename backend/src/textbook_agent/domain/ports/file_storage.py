from abc import ABC, abstractmethod

from textbook_agent.domain.entities.learner_profile import LearnerProfile


class FileStoragePort(ABC):
    """Abstract file storage interface for reading profiles and writing outputs."""

    @abstractmethod
    def read_profile(self, path: str) -> LearnerProfile:
        """Read a learner profile from a JSON file."""
        ...

    @abstractmethod
    def write_output(self, path: str, content: str) -> None:
        """Write content to a file at the given path."""
        ...
