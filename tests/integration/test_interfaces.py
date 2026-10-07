"""Integration tests validating domain workflow loops and state persistence."""

from programsaathi.config import Settings
from programsaathi.models.project import Project, ProjectStatus, Priority
from programsaathi.models.base import ApprovalStatus
from programsaathi.orchestrator.orchestrator import ProgramSaathiOrchestrator
from programsaathi.repositories.project import InMemoryProjectRepository
from programsaathi.repositories.governance import (
    InMemoryApprovalRequestRepository,
    InMemoryProjectEventRepository,
    InMemoryScopeChangeRepository,
)
from programsaathi.repositories.work_item import InMemoryTaskRepository
from programsaathi.tools.base import ToolContext
from programsaathi.tools.registry import ToolRegistry
from programsaathi.tools.read_only import GetProjectOverviewTool, ListPendingApprovalsTool
from programsaathi.tools.mutation import ProposeScopeChangeTool


def test_end_to_end_proposal_to_approval_lifecycle():
    """Validates the full cycle: Propose mutation -> Approval queued -> Human reviews -> Event audited."""
    # 1. Repositories
    project_repo = InMemoryProjectRepository()
    approval_repo = InMemoryApprovalRequestRepository()
    event_repo = InMemoryProjectEventRepository()
    scope_repo = InMemoryScopeChangeRepository()

    # 2. Project creation
    project = Project(
        key="PS-INT",
        name="Enterprise Integration Program",
        description="Core integration baseline test.",
        status=ProjectStatus.ACTIVE,
        priority=Priority.HIGH,
    )
    project_repo.create(project)

    # 3. Tool Setup
    registry = ToolRegistry()
    registry.register(GetProjectOverviewTool(project_repo=project_repo))
    registry.register(ListPendingApprovalsTool(approval_repo=approval_repo))
    registry.register(
        ProposeScopeChangeTool(
            scope_repo=scope_repo,
            approval_repo=approval_repo,
            event_repo=event_repo,
        )
    )

    orchestrator = ProgramSaathiOrchestrator(
        tool_registry=registry,
        approval_repo=approval_repo,
        event_repo=event_repo,
    )

    # 4. Agent proposes change
    context_agent = ToolContext(project_id=project.id, actor_id="agent-planner")
    res_proposal = orchestrator.execute_tool(
        "propose_scope_change",
        {
            "project_id": project.id,
            "code": "CR-099",
            "title": "Migrate auth service to Azure Container Apps",
            "description": "Switch from standalone VMs to serverless containers.",
            "reason": "Reduce compute cost and improve elasticity.",
            "impact_level": "MODERATE",
            "schedule_impact_days": 7,
            "budget_impact": 15000.0,
        },
        context_agent,
    )

    assert res_proposal.success is True
    assert res_proposal.requires_approval is True
    approval_id = res_proposal.approval_request_id
    assert approval_id is not None

    # 5. List pending approvals
    context_reviewer = ToolContext(project_id=project.id, actor_id="human-pm")
    res_list = orchestrator.execute_tool("list_pending_approvals", {"project_id": project.id}, context_reviewer)
    assert res_list.success is True
    assert len(res_list.data) == 1
    assert res_list.data[0]["id"] == approval_id

    # 6. Human Approves
    orchestrator.process_approval(
        request_id=approval_id,
        reviewer_id="human-pm",
        decision=ApprovalStatus.APPROVED,
        comments="Sign-off granted after architecture review.",
    )

    # 7. Verify pending list is now empty
    res_list_after = orchestrator.execute_tool("list_pending_approvals", {"project_id": project.id}, context_reviewer)
    assert len(res_list_after.data) == 0

    # 8. Verify audit history integrity
    events = event_repo.list_by_project(project.id)
    assert len(events) >= 3  # TOOL_EXECUTED, SCOPE_CHANGE_PROPOSED, APPROVAL_APPROVED
