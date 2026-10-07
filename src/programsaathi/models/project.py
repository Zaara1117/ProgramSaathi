"""Project, Milestone, and Stakeholder domain entities."""

from datetime import date, datetime
from typing import Optional
from pydantic import Field, EmailStr
from programsaathi.models.base import BaseEntity, ProjectStatus, Priority, ItemStatus


class Stakeholder(BaseEntity):
    """A project stakeholder, team member, or approver."""

    name: str = Field(..., description="Full name of the stakeholder")
    email: str = Field(..., description="Corporate email address")
    role: str = Field(..., description="Role title, e.g., Product Owner, Tech Lead, Program Sponsor")
    is_approver: bool = Field(default=False, description="Whether stakeholder has authority to approve scope changes")
    organization: Optional[str] = Field(default=None, description="Department or company organization")


class Milestone(BaseEntity):
    """Major target delivery date or gate within a project."""

    project_id: str = Field(..., description="Associated Project UUID")
    title: str = Field(..., description="Milestone title, e.g., MVP Architecture Signoff")
    description: Optional[str] = Field(default=None, description="Detailed deliverables and gates")
    target_date: date = Field(..., description="Target completion date")
    actual_completion_date: Optional[date] = Field(default=None, description="Actual completion date")
    status: ItemStatus = Field(default=ItemStatus.TODO, description="Current milestone status")


class Project(BaseEntity):
    """The root container for all project state, artifacts, and decisions."""

    key: str = Field(..., min_length=2, max_length=10, description="Short unique project key, e.g., 'PRGMS'")
    name: str = Field(..., min_length=3, max_length=150, description="Official project title")
    description: str = Field(..., description="Executive summary and business objectives")
    status: ProjectStatus = Field(default=ProjectStatus.INITIATION, description="Project lifecycle status")
    priority: Priority = Field(default=Priority.MEDIUM, description="Overall business priority")
    owner_id: Optional[str] = Field(default=None, description="UUID of primary project owner / lead")
    start_date: Optional[date] = Field(default=None, description="Official kick-off date")
    target_end_date: Optional[date] = Field(default=None, description="Projected completion date")
    budget_allocated: Optional[float] = Field(default=None, description="Allocated budget in USD")
