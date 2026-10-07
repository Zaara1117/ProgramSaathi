"""Risk and Blocker repositories."""

from programsaathi.models.risks import Risk, Blocker
from programsaathi.repositories.base import BaseRepository, InMemoryRepository


class RiskRepository(BaseRepository[Risk]):
    """Repository interface for Risks."""
    pass


class InMemoryRiskRepository(InMemoryRepository[Risk], RiskRepository):
    """In-memory Risk repository."""
    pass


class BlockerRepository(BaseRepository[Blocker]):
    """Repository interface for Blockers."""
    pass


class InMemoryBlockerRepository(InMemoryRepository[Blocker], BlockerRepository):
    """In-memory Blocker repository."""
    pass
