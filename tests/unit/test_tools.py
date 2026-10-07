"""Unit tests for tool framework, registry, and human-in-the-loop boundaries."""

import pytest
from programsaathi.tools.base import ToolContext
from programsaathi.tools.registry import ToolRegistry
from programsaathi.tools.read_only import (
    GetProjectOverviewTool,
    SearchProjectEvidenceTool,
    ListPendingApprovalsTool,
)
from programsaathi.tools.mutation import (
    ProposeScopeChangeTool,
    ProposeTaskCreationTool,
)
from programsaathi.models.base import ApprovalStatus, Priority
from programsaathi.exceptions import EntityNotFoundError


def test_tool_registry_and_schema_export(in_memory_repos, mock_services):
    registry = ToolRegistry()
    overview_tool = GetProjectOverviewTool(project_repo=in_memory_repos["project"])
    search_tool = SearchProjectEvidenceTool(search_service=mock_services["search"])

    registry.register(overview_tool)
    registry.register(search_tool)

    assert len(registry.list_tools()) == 2
    assert registry.get("get_project_overview") is overview_tool

    with pytest.raises(EntityNotFoundError):
        registry.get("non_existent_tool")

    schemas = registry.get_openai_tools()
    assert len(schemas) == 2
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "get_project_overview"


def test_get_project_overview_tool(in_memory_repos, sample_project):
    in_memory_repos["project"].create(sample_project)
    tool = GetProjectOverviewTool(project_repo=in_memory_repos["project"])

    context = ToolContext(project_id=sample_project.id, actor_id="user-1")
    result = tool.execute({"project_id": sample_project.id}, context)

    assert result.success is True
    assert result.data["name"] == sample_project.name
    assert result.requires_approval is False


def test_mutation_tool_requires_approval_flow(in_memory_repos, sample_project):
    """Verifies that an unapproved mutation enters the formal human approval pipeline."""
    in_memory_repos["project"].create(sample_project)

    tool = ProposeScopeChangeTool(
        scope_repo=in_memory_repos["scope"],
        approval_repo=in_memory_repos["approval"],
        event_repo=in_memory_repos["event"],
    )

    context = ToolContext(
        project_id=sample_project.id,
        actor_id="agent-reasoner",
        is_human_approved=False,
    )

    params = {
        "project_id": sample_project.id,
        "code": "CR-001",
        "title": "Add multi-region disaster recovery",
        "description": "Deploy second hot-standby region in East US.",
        "reason": "Business continuity compliance.",
        "impact_level": "SIGNIFICANT",
        "schedule_impact_days": 21,
        "budget_impact": 40000.0,
    }

    result = tool.execute(params, context)

    # Must require approval
    assert result.success is True
    assert result.requires_approval is True
    assert result.approval_request_id is not None

    # Must be pending in ApprovalRequestRepository
    pending = in_memory_repos["approval"].list_pending(sample_project.id)
    assert len(pending) == 1
    assert pending[0].id == result.approval_request_id
    assert pending[0].status == ApprovalStatus.PENDING

    # Must have recorded an audit event
    events = in_memory_repos["event"].list_by_project(sample_project.id)
    assert len(events) == 1
    assert events[0].event_type == "SCOPE_CHANGE_PROPOSED"


def test_mutation_tool_with_human_approval_commits(in_memory_repos, sample_project):
    """Verifies that once human approval is asserted, mutation commits directly."""
    in_memory_repos["project"].create(sample_project)

    tool = ProposeTaskCreationTool(
        task_repo=in_memory_repos["task"],
        approval_repo=in_memory_repos["approval"],
        event_repo=in_memory_repos["event"],
    )

    context = ToolContext(
        project_id=sample_project.id,
        actor_id="lead-engineer",
        is_human_approved=True,
    )

    params = {
        "project_id": sample_project.id,
        "code": "TSK-001",
        "title": "Provision Azure SQL Hyperscale tier",
        "description": "Configure geo-replication and private endpoints.",
        "priority": "HIGH",
        "estimated_hours": 16.0,
    }

    result = tool.execute(params, context)

    assert result.success is True
    assert result.requires_approval is False
    assert result.data["code"] == "TSK-001"

    # Task should exist in repository
    tasks = in_memory_repos["task"].list_by_project(sample_project.id)
    assert len(tasks) == 1
    assert tasks[0].code == "TSK-001"
