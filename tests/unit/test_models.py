"""Unit tests for all 17 ProgramSaathi domain models."""

from datetime import date, datetime, timezone
import pytest
from pydantic import ValidationError

from programsaathi.models.base import (
    Priority,
    ItemStatus,
    ProjectStatus,
    RiskLikelihood,
    RiskImpact,
    DependencyType,
    ApprovalStatus,
    ScopeChangeImpact,
)
from programsaathi.models.project import Project, Milestone, Stakeholder
from programsaathi.models.work_items import Requirement, UserStory, Task, Dependency
from programsaathi.models.risks import Risk, Blocker
from programsaathi.models.governance import (
    Meeting,
    ActionItem,
    Decision,
    ScopeChange,
    ApprovalRequest,
    ProjectEvent,
)
from programsaathi.models.document import Document, DocumentVersion, DocumentType


def test_project_model_creation():
    project = Project(
        key="PRGMS",
        name="ProgramSaathi Core",
        description="Master project description.",
        status=ProjectStatus.PLANNING,
        priority=Priority.HIGH,
    )
    assert project.id is not None
    assert project.key == "PRGMS"
    assert project.status == "PLANNING"
    assert project.created_at <= datetime.now(timezone.utc)

    # Test key length validation
    with pytest.raises(ValidationError):
        Project(key="P", name="Too Short", description="Desc")


def test_milestone_model():
    milestone = Milestone(
        project_id="proj-123",
        title="Architecture Sign-off",
        target_date=date(2026, 12, 1),
    )
    assert milestone.project_id == "proj-123"
    assert milestone.status == ItemStatus.TODO


def test_stakeholder_model():
    stakeholder = Stakeholder(
        name="Alice Smith",
        email="alice@company.com",
        role="Product Lead",
        is_approver=True,
    )
    assert stakeholder.is_approver is True
    assert stakeholder.email == "alice@company.com"


def test_requirement_model():
    req = Requirement(
        project_id="proj-123",
        code="REQ-001",
        title="Azure SSO Login",
        description="Users must authenticate via Entra ID.",
        category="Security",
        priority=Priority.CRITICAL,
        acceptance_criteria=["MFA prompted", "Session valid 8 hours"],
    )
    assert req.code == "REQ-001"
    assert len(req.acceptance_criteria) == 2


def test_user_story_model():
    story = UserStory(
        project_id="proj-123",
        code="US-010",
        title="Self-service password reset",
        as_a="Customer",
        i_want="to reset my password without calling support",
        so_that="I regain account access immediately",
        story_points=5,
    )
    assert story.as_a == "Customer"
    assert story.story_points == 5


def test_task_model():
    task = Task(
        project_id="proj-123",
        code="TSK-101",
        title="Implement Entra ID token validation",
        description="Use PyJWT and MSAL to validate Bearer token.",
        estimated_hours=8.5,
        status=ItemStatus.TODO,
    )
    assert task.estimated_hours == 8.5
    assert task.status == ItemStatus.TODO


def test_dependency_model():
    dep = Dependency(
        project_id="proj-123",
        source_id="tsk-1",
        source_type="Task",
        target_id="tsk-2",
        target_type="Task",
        dependency_type=DependencyType.BLOCKS,
    )
    assert dep.dependency_type == DependencyType.BLOCKS


def test_risk_and_blocker_models():
    risk = Risk(
        project_id="proj-123",
        code="RSK-001",
        title="Database migration cutoff constraint",
        description="Legacy database schema could cause 2-hour downtime.",
        likelihood=RiskLikelihood.HIGH,
        impact=RiskImpact.HIGH,
        mitigation_strategy="Perform shadow dual-writing 2 weeks prior.",
    )
    assert risk.likelihood == RiskLikelihood.HIGH

    blocker = Blocker(
        project_id="proj-123",
        code="BLK-001",
        title="Firewall rule not approved",
        description="Ports 1433 blocked to Azure SQL.",
        blocked_entity_id="tsk-1",
        blocked_entity_type="Task",
        severity=Priority.CRITICAL,
    )
    assert blocker.severity == Priority.CRITICAL
    assert blocker.status == ItemStatus.BLOCKED


def test_meeting_and_action_item_models():
    meeting = Meeting(
        project_id="proj-123",
        title="Sprint Planning & Architecture Sync",
        meeting_date=datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc),
        duration_minutes=45,
        attendees=["alice@example.com", "bob@example.com"],
        summary="Agreed on microservices boundaries.",
    )
    assert meeting.duration_minutes == 45

    action_item = ActionItem(
        project_id="proj-123",
        meeting_id=meeting.id,
        title="Submit Azure subscription quota increase",
        priority=Priority.HIGH,
        status=ItemStatus.TODO,
    )
    assert action_item.meeting_id == meeting.id


def test_decision_model():
    decision = Decision(
        project_id="proj-123",
        code="DEC-001",
        title="Adopt Azure SQL as Authoritative Store",
        context="Need ACID guarantees, enterprise auditing, and strict relational integrity.",
        decision_taken="Use Azure SQL Hyperscale rather than NoSQL.",
        rationale="Authoritative project state requires relational transactions.",
    )
    assert decision.code == "DEC-001"
    assert decision.decided_at is not None


def test_scope_change_and_approval_request():
    scope_change = ScopeChange(
        project_id="proj-123",
        code="CR-002",
        title="Add multi-tenant billing support",
        description="Allow B2B parent entities to pay for child subscriptions.",
        reason="Enterprise client contractual commitment.",
        impact_level=ScopeChangeImpact.SIGNIFICANT,
        schedule_impact_days=14,
        budget_impact=25000.0,
        status=ApprovalStatus.PENDING,
    )
    assert scope_change.status == ApprovalStatus.PENDING
    assert scope_change.schedule_impact_days == 14

    approval_req = ApprovalRequest(
        project_id="proj-123",
        entity_type="ScopeChange",
        entity_id=scope_change.id,
        action_type="CREATE",
        summary="Approval requested for CR-002",
        proposed_diff=scope_change.model_dump(),
        status=ApprovalStatus.PENDING,
    )
    assert approval_req.status == ApprovalStatus.PENDING
    assert approval_req.requested_by == "AI_AGENT"


def test_project_event_model():
    event = ProjectEvent(
        project_id="proj-123",
        event_type="DECISION_RATIFIED",
        actor_type="USER",
        actor_id="user-456",
        summary="ADR approved by technical architect.",
        payload={"adr": "DEC-001"},
    )
    assert event.event_type == "DECISION_RATIFIED"
    assert event.payload["adr"] == "DEC-001"


def test_document_and_version_models():
    doc = Document(
        project_id="proj-123",
        title="Core PRD v1.0",
        document_type=DocumentType.PRD,
        latest_version=1,
    )
    assert doc.document_type == DocumentType.PRD

    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        file_name="core_prd.pdf",
        content_type="application/pdf",
        blob_path="projects/proj-123/docs/core_prd.pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_indexed=True,
        chunk_count=18,
    )
    assert version.document_id == doc.id
    assert version.chunk_count == 18
