"""Base models and shared enumerations for ProgramSaathi domain entities."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Priority(str, Enum):
    """Priority levels across tasks, requirements, risks, and blockers."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ItemStatus(str, Enum):
    """Standard lifecycle status for work items and tasks."""
    PROPOSED = "PROPOSED"
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class ProjectStatus(str, Enum):
    """Lifecycle status for a project."""
    INITIATION = "INITIATION"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class RiskLikelihood(str, Enum):
    """Likelihood of risk occurrence."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskImpact(str, Enum):
    """Impact of risk occurrence."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DependencyType(str, Enum):
    """Type of dependency between work items."""
    BLOCKS = "BLOCKS"
    BLOCKED_BY = "BLOCKED_BY"
    RELATES_TO = "RELATES_TO"
    SUBTASK_OF = "SUBTASK_OF"


class ApprovalStatus(str, Enum):
    """Status for human-in-the-loop approval workflows."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class ScopeChangeImpact(str, Enum):
    """Magnitude of impact for proposed scope changes."""
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SIGNIFICANT = "SIGNIFICANT"
    CRITICAL = "CRITICAL"


class BaseEntity(BaseModel):
    """Base domain model providing UUID identity, timestamps, and metadata dict."""

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique entity UUID")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp in UTC")
    updated_at: datetime = Field(default_factory=utc_now, description="Last updated timestamp in UTC")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary extension metadata")
