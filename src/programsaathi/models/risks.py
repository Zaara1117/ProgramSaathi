"""Risk and Blocker domain entities."""

from typing import Optional
from pydantic import Field
from programsaathi.models.base import BaseEntity, RiskImpact, RiskLikelihood, Priority, ItemStatus


class Risk(BaseEntity):
    """An uncertain event or condition that could negatively impact project delivery."""

    project_id: str = Field(..., description="Parent Project UUID")
    code: str = Field(..., description="Unique identifier, e.g., 'RSK-005'")
    title: str = Field(..., description="Risk statement")
    description: str = Field(..., description="Detailed context and root cause")
    likelihood: RiskLikelihood = Field(default=RiskLikelihood.MEDIUM, description="Likelihood of occurrence")
    impact: RiskImpact = Field(default=RiskImpact.MEDIUM, description="Potential impact severity")
    mitigation_strategy: str = Field(..., description="Planned actions to reduce likelihood or impact")
    contingency_plan: Optional[str] = Field(default=None, description="Action taken if risk triggers")
    owner_id: Optional[str] = Field(default=None, description="Risk owner Stakeholder UUID")
    status: ItemStatus = Field(default=ItemStatus.TODO, description="Risk tracking status (TODO=Identified, IN_PROGRESS=Mitigating, DONE=Closed)")


class Blocker(BaseEntity):
    """An active impeding condition actively halting task or milestone progress."""

    project_id: str = Field(..., description="Parent Project UUID")
    code: str = Field(..., description="Unique identifier, e.g., 'BLK-012'")
    title: str = Field(..., description="Blocker description")
    description: str = Field(..., description="Detailed obstruction explanation")
    blocked_entity_id: str = Field(..., description="UUID of blocked task, milestone, or story")
    blocked_entity_type: str = Field(..., description="Entity type: 'Task', 'Milestone', 'UserStory'")
    severity: Priority = Field(default=Priority.HIGH, description="Blocker severity")
    status: ItemStatus = Field(default=ItemStatus.BLOCKED, description="Status (BLOCKED=Active, DONE=Resolved)")
    resolution_path: Optional[str] = Field(default=None, description="Proposed or completed resolution steps")
    owner_id: Optional[str] = Field(default=None, description="Resolver Stakeholder UUID")
