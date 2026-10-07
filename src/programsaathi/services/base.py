"""Base class and protocol definitions for infrastructure service clients."""

from abc import ABC, abstractmethod


class BaseService(ABC):
    """Abstract base class for all ProgramSaathi infrastructure services."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the underlying external service is configured and reachable."""
        pass
