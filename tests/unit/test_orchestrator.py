"""Unit tests for ProgramSaathi Orchestrator coordination."""

import pytest
from programsaathi.orchestrator.orchestrator import ProgramSaathiOrchestrator
from programsaathi.tools.registry import ToolRegistry
from programsaathi.tools.read_only import GetProjectOverviewTool
from programsaathi.tools.base import ToolContext
from programsaathi.models.base import ApprovalStatus
from programsaathi.models.governance import ApprovalRequest


def test_orchestrator_initialization(test_settings, in_memory_repos, mock_services):
    registry = ToolRegistry()
    registry.register(GetProjectOverviewTool(project_repo=in_memory_repos["project"]))

    orchestrator = ProgramSaathiOrchestrator(
        settings=test_settings,
        llm_service=mock_services["llm"],
        storage_service=mock_services["storage"],
        search_service=mock_services["search"],
        database_service=mock_services["database"],
        tool_registry=registry,
        approval_repo=in_memory_repos["approval"],
        event_repo=in_memory_repos["event"],
    )

    assert orchestrator.settings.app_name == "ProgramSaathi-Test"
    assert orchestrator.tool_registry.get("get_project_overview") is not None


def test_orchestrator_tool_dispatch_and_audit(test_settings, in_memory_repos, sample_project):
    in_memory_repos["project"].create(sample_project)
    registry = ToolRegistry()
    registry.register(GetProjectOverviewTool(project_repo=in_memory_repos["project"]))

    orchestrator = ProgramSaathiOrchestrator(
        settings=test_settings,
        tool_registry=registry,
        event_repo=in_memory_repos["event"],
    )

    context = ToolContext(project_id=sample_project.id, actor_id="agent-01")
    result = orchestrator.execute_tool(
        "get_project_overview",
        {"project_id": sample_project.id},
        context,
    )

    assert result.success is True
    # Verify audit event logged
    events = in_memory_repos["event"].list_by_project(sample_project.id)
    assert len(events) == 1
    assert events[0].event_type == "TOOL_EXECUTED"


def test_orchestrator_process_approval(test_settings, in_memory_repos, sample_project):
    orchestrator = ProgramSaathiOrchestrator(
        settings=test_settings,
        approval_repo=in_memory_repos["approval"],
        event_repo=in_memory_repos["event"],
    )

    req = ApprovalRequest(
        project_id=sample_project.id,
        entity_type="ScopeChange",
        entity_id="cr-100",
        action_type="CREATE",
        summary="Add audit log subsystem",
        proposed_diff={"budget": 5000.0},
        status=ApprovalStatus.PENDING,
    )
    in_memory_repos["approval"].create(req)

    # Human reviewer approves
    updated = orchestrator.process_approval(
        request_id=req.id,
        reviewer_id="lead-architect",
        decision=ApprovalStatus.APPROVED,
        comments="Approved as within budget margin.",
    )

    assert updated.status == ApprovalStatus.APPROVED
    assert updated.reviewer_id == "lead-architect"
    assert updated.reviewed_at is not None

    events = in_memory_repos["event"].list_by_project(sample_project.id)
    assert any(e.event_type == "APPROVAL_APPROVED" for e in events)
