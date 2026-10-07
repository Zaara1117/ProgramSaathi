"""Governance, Meetings, Scope Changes, Human Approval, and Event models."""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import Field
from programsaathi.models.base import (
    BaseEntity,
    Priority,
    ItemStatus,
    ApprovalStatus,
    ScopeChangeImpact,
    utc_now,
)


class Meeting(BaseEntity):
    """Project meeting recording attendee list, minutes, and synthesized summary."""

    project_id: str = Field(..., description="Parent Project UUID")
    title: str = Field(..., description="Meeting title / subject")
    meeting_date: datetime = Field(..., description="Meeting date and time")
    duration_minutes: int = Field(default=30, ge=1, description="Duration in minutes")
    attendees: list[str] = Field(default_factory=list, description="List of participant emails or names")
    agenda: Optional[str] = Field(default=None, description="Meeting agenda")
    raw_notes_document_id: Optional[str] = Field(default=None, description="Document UUID containing raw transcript/notes")
    summary: Optional[str] = Field(default=None, description="AI-synthesized executive summary")


class ActionItem(BaseEntity):
    """Specific follow-up action captured during a meeting or review."""

    project_id: str = Field(..., description="Parent Project UUID")
    meeting_id: Optional[str] = Field(default=None, description="Associated Meeting UUID if derived from meeting")
    title: str = Field(..., description="Action item description")
    assignee_id: Optional[str] = Field(default=None, description="Assignee Stakeholder UUID")
    due_date: Optional[date] = Field(default=None, description="Target completion date")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority")
    status: ItemStatus = Field(default=ItemStatus.TODO, description="Status")


class Decision(BaseEntity):
    """Authoritative architectural, technical, or program decision (ADR / Decision Log)."""

    project_id: str = Field(..., description="Parent Project UUID")
    code: str = Field(..., description="Unique business identifier, e.g., 'DEC-004'")
    title: str = Field(..., description="Decision summary title")
    context: str = Field(..., description="Context, alternatives considered, and trade-offs")
    decision_taken: str = Field(..., description="The concrete agreed decision")
    rationale: str = Field(..., description="Justification and rationale")
    consequences: Optional[str] = Field(default=None, description="Anticipated consequences and follow-ups")
    decided_by_id: Optional[str] = Field(default=None, description="Stakeholder UUID who made or authorized decision")
    decided_at: datetime = Field(default_factory=utc_now, description="Timestamp when decision was ratified")


class ScopeChange(BaseEntity):
    """Proposed scope modification impacting requirements, timelines, or resources."""

    project_id: str = Field(..., description="Parent Project UUID")
    code: str = Field(..., description="Unique identifier, e.g., 'CR-001'")
    title: str = Field(..., description="Scope change title")
    description: str = Field(..., description="Detailed specification of the change")
    reason: str = Field(..., description="Business driver or root cause necessitating change")
    impact_level: ScopeChangeImpact = Field(default=ScopeChangeImpact.MODERATE, description="Estimated severity")
    schedule_impact_days: int = Field(default=0, description="Estimated schedule deviation in days (+/-)")
    budget_impact: float = Field(default=0.0, description="Estimated monetary impact in USD")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Approval lifecycle state")
    proposed_by_id: Optional[str] = Field(default=None, description="Proposer Stakeholder or 'AI_AGENT'")


class ApprovalRequest(BaseEntity):
    """Human-in-the-loop formal approval gate guarding consequential state mutations."""

    project_id: str = Field(..., description="Parent Project UUID")
    entity_type: str = Field(..., description="Type of entity being mutated, e.g., 'ScopeChange', 'Task', 'Milestone'")
    entity_id: str = Field(..., description="Target entity UUID")
    action_type: str = Field(..., description="Action: 'CREATE', 'UPDATE', 'DELETE', 'STATUS_CHANGE'")
    requested_by: str = Field(default="AI_AGENT", description="Initiator: 'AI_AGENT' or user UUID")
    summary: str = Field(..., description="Clear explanation of proposed change and rationale")
    proposed_diff: dict[str, Any] = Field(..., description="Exact key-value diff proposed for mutation")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Approval state")
    reviewer_id: Optional[str] = Field(default=None, description="Authorizing human Stakeholder UUID")
    review_comments: Optional[str] = Field(default=None, description="Reviewer feedback or conditions")
    reviewed_at: Optional[datetime] = Field(default=None, description="Approval / rejection timestamp")


class ProjectEvent(BaseEntity):
    """Authoritative audit record logging all actions, recommendations, approvals, and mutations."""

    project_id: str = Field(..., description="Parent Project UUID")
    event_type: str = Field(..., description="Event classification, e.g., 'SCOPE_PROPOSED', 'APPROVAL_GRANTED'")
    actor_type: str = Field(..., description="Actor classification: 'USER', 'AGENT', 'SYSTEM'")
    actor_id: str = Field(..., description="UUID or identifier of executing actor")
    entity_type: Optional[str] = Field(default=None, description="Target entity type")
    entity_id: Optional[str] = Field(default=None, description="Target entity UUID")
    summary: str = Field(..., description="Human-readable event log description")
    payload: dict[str, Any] = Field(default_factory=dict, description="Structured event payload")
