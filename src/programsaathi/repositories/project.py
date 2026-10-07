"""Project, Milestone, and Stakeholder repositories."""

from typing import Optional
from programsaathi.models.project import Project, Milestone, Stakeholder
from programsaathi.repositories.base import BaseRepository, InMemoryRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository interface for Project aggregate."""

    def get_by_key(self, key: str) -> Optional[Project]:
        """Lookup project by business key, e.g., 'PRGMS'."""
        raise NotImplementedError


class InMemoryProjectRepository(InMemoryRepository[Project], ProjectRepository):
    """In-memory Project repository."""

    def get_by_key(self, key: str) -> Optional[Project]:
        for p in self._store.values():
            if p.key.upper() == key.upper():
                return p
        return None


class MilestoneRepository(BaseRepository[Milestone]):
    """Repository interface for Milestones."""
    pass


class InMemoryMilestoneRepository(InMemoryRepository[Milestone], MilestoneRepository):
    """In-memory Milestone repository."""
    pass


class StakeholderRepository(BaseRepository[Stakeholder]):
    """Repository interface for Stakeholders."""

    def get_by_email(self, email: str) -> Optional[Stakeholder]:
        raise NotImplementedError


class InMemoryStakeholderRepository(InMemoryRepository[Stakeholder], StakeholderRepository):
    """In-memory Stakeholder repository."""

    def get_by_email(self, email: str) -> Optional[Stakeholder]:
        for s in self._store.values():
            if s.email.lower() == email.lower():
                return s
        return None
