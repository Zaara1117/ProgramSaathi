"""Requirement, UserStory, Task, and Dependency domain entities."""

from typing import Optional
from pydantic import Field
from programsaathi.models.base import BaseEntity, Priority, ItemStatus, DependencyType


class Requirement(BaseEntity):
    """Business, functional, or non-functional requirement derived from PRD/intake documents."""

    project_id: str = Field(..., description="Parent Project UUID")
    code: str = Field(..., description="Unique business identifier, e.g., 'REQ-001'")
    title: str = Field(..., description="Short summary of requirement")
    description: str = Field(..., description="Full requirement specification")
    category: str = Field(default="Functional", description="Functional, Non-Functional, Compliance, Security")
    priority: Priority = Field(default=Priority.MEDIUM, description="Business priority")
    status: ItemStatus = Field(default=ItemStatus.PROPOSED, description="Lifecycle status")
    source_document_id: Optional[str] = Field(default=None, description="Source document UUID if extracted")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Explicit acceptance criteria")


class UserStory(BaseEntity):
    """User story detailing value proposition from a persona perspective."""

    requirement_id: Optional[str] = Field(default=None, description="Parent Requirement UUID if decomposed")
    project_id: str = Field(..., description="Parent Project UUID")
    code: str = Field(..., description="Unique business identifier, e.g., 'US-010'")
    title: str = Field(..., description="Short story title")
    as_a: str = Field(..., description="Role or user persona")
    i_want: str = Field(..., description="Desired capability or feature")
    so_that: str = Field(..., description="Business value or benefit achieved")
    story_points: Optional[int] = Field(default=None, ge=1, le=100, description="Agile story point estimate")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority")
    status: ItemStatus = Field(default=ItemStatus.BACKLOG, description="Lifecycle status")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Specific acceptance test criteria")


class Task(BaseEntity):
    """Concrete actionable engineering or operational work item."""

    project_id: str = Field(..., description="Parent Project UUID")
    user_story_id: Optional[str] = Field(default=None, description="Parent UserStory UUID if applicable")
    milestone_id: Optional[str] = Field(default=None, description="Associated Milestone UUID")
    code: str = Field(..., description="Unique business identifier, e.g., 'TSK-102'")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Implementation details")
    assignee_id: Optional[str] = Field(default=None, description="Assignee Stakeholder UUID")
    estimated_hours: Optional[float] = Field(default=None, ge=0.0, description="Estimated effort in hours")
    actual_hours: Optional[float] = Field(default=None, ge=0.0, description="Actual recorded effort in hours")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority")
    status: ItemStatus = Field(default=ItemStatus.TODO, description="Execution status")


class Dependency(BaseEntity):
    """Directional dependency linking two work items or milestones."""

    project_id: str = Field(..., description="Parent Project UUID")
    source_id: str = Field(..., description="Origin item UUID")
    source_type: str = Field(..., description="'Task', 'UserStory', 'Requirement', or 'Milestone'")
    target_id: str = Field(..., description="Destination item UUID")
    target_type: str = Field(..., description="'Task', 'UserStory', 'Requirement', or 'Milestone'")
    dependency_type: DependencyType = Field(default=DependencyType.BLOCKS, description="Type of relationship")
    description: Optional[str] = Field(default=None, description="Context regarding the constraint or dependency")
