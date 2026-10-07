"""Governance repositories: Decision, ScopeChange, ApprovalRequest, ProjectEvent, Meeting, ActionItem."""

from typing import Optional
from programsaathi.models.governance import (
    Decision,
    ScopeChange,
    ApprovalRequest,
    ProjectEvent,
    Meeting,
    ActionItem,
)
from programsaathi.models.base import ApprovalStatus
from programsaathi.repositories.base import BaseRepository, InMemoryRepository


class DecisionRepository(BaseRepository[Decision]):
    pass


class InMemoryDecisionRepository(InMemoryRepository[Decision], DecisionRepository):
    pass


class ScopeChangeRepository(BaseRepository[ScopeChange]):
    pass


class InMemoryScopeChangeRepository(InMemoryRepository[ScopeChange], ScopeChangeRepository):
    pass


class ApprovalRequestRepository(BaseRepository[ApprovalRequest]):
    def list_pending(self, project_id: str) -> list[ApprovalRequest]:
        raise NotImplementedError


class InMemoryApprovalRequestRepository(InMemoryRepository[ApprovalRequest], ApprovalRequestRepository):
    def list_pending(self, project_id: str) -> list[ApprovalRequest]:
        return [
            req for req in self._store.values()
            if req.project_id == project_id and req.status == ApprovalStatus.PENDING
        ]


class ProjectEventRepository(BaseRepository[ProjectEvent]):
    pass


class InMemoryProjectEventRepository(InMemoryRepository[ProjectEvent], ProjectEventRepository):
    pass


class MeetingRepository(BaseRepository[Meeting]):
    pass


class InMemoryMeetingRepository(InMemoryRepository[Meeting], MeetingRepository):
    pass


class ActionItemRepository(BaseRepository[ActionItem]):
    pass


class InMemoryActionItemRepository(InMemoryRepository[ActionItem], ActionItemRepository):
    pass
