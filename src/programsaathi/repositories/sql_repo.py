"""SQLAlchemy-backed repository implementations for authoritative state persistence."""

import json
from typing import Any, Generic, Optional, Type, TypeVar
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from programsaathi.models.base import BaseEntity, ApprovalStatus
from programsaathi.models.project import Project, Milestone, Stakeholder
from programsaathi.models.work_items import Requirement, UserStory, Task, Dependency
from programsaathi.models.risks import Risk, Blocker
from programsaathi.models.governance import (
    Decision,
    ScopeChange,
    ApprovalRequest,
    ProjectEvent,
    Meeting,
    ActionItem,
)
from programsaathi.models.document import Document, DocumentVersion
from programsaathi.database.tables import (
    BaseTable,
    ProjectModel,
    MilestoneModel,
    StakeholderModel,
    RequirementModel,
    UserStoryModel,
    TaskModel,
    DependencyModel,
    RiskModel,
    BlockerModel,
    DecisionModel,
    ScopeChangeModel,
    ApprovalRequestModel,
    ProjectEventModel,
    MeetingModel,
    ActionItemModel,
    DocumentModel,
    DocumentVersionModel,
)
from programsaathi.repositories.base import BaseRepository
from programsaathi.repositories.project import ProjectRepository, MilestoneRepository, StakeholderRepository
from programsaathi.repositories.work_item import RequirementRepository, UserStoryRepository, TaskRepository, DependencyRepository
from programsaathi.repositories.risk_blocker import RiskRepository, BlockerRepository
from programsaathi.repositories.governance import (
    DecisionRepository,
    ScopeChangeRepository,
    ApprovalRequestRepository,
    ProjectEventRepository,
    MeetingRepository,
    ActionItemRepository,
)
from programsaathi.repositories.document import DocumentRepository, DocumentVersionRepository

E = TypeVar("E", bound=BaseEntity)
M = TypeVar("M", bound=BaseTable)


class BaseSQLRepository(BaseRepository[E], Generic[E, M]):
    """Base SQL repository bridging SQLAlchemy ORM models and Pydantic domain models."""

    def __init__(self, session: Session, model_cls: Type[M], entity_cls: Type[E]) -> None:
        self.session = session
        self.model_cls = model_cls
        self.entity_cls = entity_cls

    def _to_entity(self, model: M) -> E:
        """Converts ORM model to Pydantic entity."""
        d = {c.name: getattr(model, c.name) for c in model.__table__.columns}
        if "metadata_json" in d:
            raw_meta = d.pop("metadata_json")
            d["metadata"] = json.loads(raw_meta) if raw_meta else {}
        if "acceptance_criteria" in d and isinstance(d["acceptance_criteria"], str):
            try:
                d["acceptance_criteria"] = json.loads(d["acceptance_criteria"])
            except Exception:
                d["acceptance_criteria"] = []
        if "attendees" in d and isinstance(d["attendees"], str):
            try:
                d["attendees"] = json.loads(d["attendees"])
            except Exception:
                d["attendees"] = []
        if "proposed_diff" in d and isinstance(d["proposed_diff"], str):
            try:
                d["proposed_diff"] = json.loads(d["proposed_diff"])
            except Exception:
                d["proposed_diff"] = {}
        if "payload" in d and isinstance(d["payload"], str):
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                d["payload"] = {}
        if "project_key" in d:
            d["key"] = d.pop("project_key")
        return self.entity_cls.model_validate(d)

    def _to_model_dict(self, entity: E) -> dict[str, Any]:
        """Converts Pydantic entity to dictionary matching ORM columns."""
        data = entity.model_dump()
        if "metadata" in data:
            meta = data.pop("metadata")
            data["metadata_json"] = json.dumps(meta, default=str)
        if "acceptance_criteria" in data and isinstance(data["acceptance_criteria"], list):
            data["acceptance_criteria"] = json.dumps(data["acceptance_criteria"])
        if "attendees" in data and isinstance(data["attendees"], list):
            data["attendees"] = json.dumps(data["attendees"])
        if "proposed_diff" in data and isinstance(data["proposed_diff"], dict):
            data["proposed_diff"] = json.dumps(data["proposed_diff"], default=str)
        if "payload" in data and isinstance(data["payload"], dict):
            data["payload"] = json.dumps(data["payload"], default=str)
        if "key" in data and hasattr(self.model_cls, "project_key"):
            data["project_key"] = data.pop("key")
        return data

    def get_by_id(self, entity_id: str) -> Optional[E]:
        row = self.session.get(self.model_cls, entity_id)
        return self._to_entity(row) if row else None

    def list_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> list[E]:
        if not hasattr(self.model_cls, "project_id"):
            return []
        stmt = (
            select(self.model_cls)
            .where(getattr(self.model_cls, "project_id") == project_id)
            .offset(offset)
            .limit(limit)
        )
        results = self.session.scalars(stmt).all()
        return [self._to_entity(r) for r in results]

    def create(self, entity: E) -> E:
        row = self.model_cls(**self._to_model_dict(entity))
        self.session.add(row)
        self.session.flush()
        return entity

    def update(self, entity: E) -> E:
        row = self.session.get(self.model_cls, entity.id)
        if not row:
            return self.create(entity)
        model_dict = self._to_model_dict(entity)
        for k, v in model_dict.items():
            if hasattr(row, k):
                setattr(row, k, v)
        self.session.flush()
        return entity

    def delete(self, entity_id: str) -> bool:
        row = self.session.get(self.model_cls, entity_id)
        if row:
            self.session.delete(row)
            self.session.flush()
            return True
        return False


# ------------------------------------------------------------------------------
# Concrete SQL Repositories
# ------------------------------------------------------------------------------

class SQLProjectRepository(BaseSQLRepository[Project, ProjectModel], ProjectRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ProjectModel, Project)

    def get_by_key(self, key: str) -> Optional[Project]:
        stmt = select(ProjectModel).where(ProjectModel.project_key == key.upper())
        row = self.session.scalars(stmt).first()
        return self._to_entity(row) if row else None


class SQLMilestoneRepository(BaseSQLRepository[Milestone, MilestoneModel], MilestoneRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MilestoneModel, Milestone)


class SQLStakeholderRepository(BaseSQLRepository[Stakeholder, StakeholderModel], StakeholderRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, StakeholderModel, Stakeholder)

    def get_by_email(self, email: str) -> Optional[Stakeholder]:
        stmt = select(StakeholderModel).where(StakeholderModel.email == email.lower())
        row = self.session.scalars(stmt).first()
        return self._to_entity(row) if row else None


class SQLRequirementRepository(BaseSQLRepository[Requirement, RequirementModel], RequirementRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RequirementModel, Requirement)


class SQLUserStoryRepository(BaseSQLRepository[UserStory, UserStoryModel], UserStoryRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UserStoryModel, UserStory)


class SQLTaskRepository(BaseSQLRepository[Task, TaskModel], TaskRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, TaskModel, Task)


class SQLDependencyRepository(BaseSQLRepository[Dependency, DependencyModel], DependencyRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DependencyModel, Dependency)


class SQLRiskRepository(BaseSQLRepository[Risk, RiskModel], RiskRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RiskModel, Risk)


class SQLBlockerRepository(BaseSQLRepository[Blocker, BlockerModel], BlockerRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, BlockerModel, Blocker)


class SQLDecisionRepository(BaseSQLRepository[Decision, DecisionModel], DecisionRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DecisionModel, Decision)


class SQLScopeChangeRepository(BaseSQLRepository[ScopeChange, ScopeChangeModel], ScopeChangeRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ScopeChangeModel, ScopeChange)


class SQLApprovalRequestRepository(BaseSQLRepository[ApprovalRequest, ApprovalRequestModel], ApprovalRequestRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ApprovalRequestModel, ApprovalRequest)

    def list_pending(self, project_id: str) -> list[ApprovalRequest]:
        stmt = (
            select(ApprovalRequestModel)
            .where(
                ApprovalRequestModel.project_id == project_id,
                ApprovalRequestModel.status == ApprovalStatus.PENDING.value,
            )
        )
        rows = self.session.scalars(stmt).all()
        return [self._to_entity(r) for r in rows]


class SQLProjectEventRepository(BaseSQLRepository[ProjectEvent, ProjectEventModel], ProjectEventRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ProjectEventModel, ProjectEvent)


class SQLMeetingRepository(BaseSQLRepository[Meeting, MeetingModel], MeetingRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MeetingModel, Meeting)


class SQLActionItemRepository(BaseSQLRepository[ActionItem, ActionItemModel], ActionItemRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ActionItemModel, ActionItem)


class SQLDocumentRepository(BaseSQLRepository[Document, DocumentModel], DocumentRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DocumentModel, Document)


class SQLDocumentVersionRepository(BaseSQLRepository[DocumentVersion, DocumentVersionModel], DocumentVersionRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DocumentVersionModel, DocumentVersion)

    def list_by_document(self, document_id: str) -> list[DocumentVersion]:
        stmt = select(DocumentVersionModel).where(DocumentVersionModel.document_id == document_id)
        rows = self.session.scalars(stmt).all()
        return [self._to_entity(r) for r in rows]
