"""Unit tests for system prompts, prompt templates, and schema models."""

import pytest
from programsaathi.models.base import Priority
from programsaathi.prompts.system import PROGRAMSAATHI_SYSTEM_PROMPT
from programsaathi.prompts.templates import (
    ProjectUnderstandingResult,
    ExtractedRequirementItem,
    ExtractedUserStoryItem,
    RequirementExtractionResult,
    ProjectSummaryResult,
    format_project_understanding_prompt,
    format_requirement_extraction_prompt,
    format_project_summarization_prompt,
    format_grounded_prompt,
)


def test_system_prompt_principles():
    assert "ProgramSaathi" in PROGRAMSAATHI_SYSTEM_PROMPT
    assert "EVIDENCE-GROUNDED" in PROGRAMSAATHI_SYSTEM_PROMPT
    assert "HUMAN-IN-THE-LOOP" in PROGRAMSAATHI_SYSTEM_PROMPT
    assert "Never suggest, generate, or execute raw SQL" in PROGRAMSAATHI_SYSTEM_PROMPT


def test_project_understanding_schema_and_prompt():
    prompt = format_project_understanding_prompt("Legacy system rewrite specifications", project_name_hint="Core Modernization")
    assert "Core Modernization" in prompt
    assert "Legacy system rewrite" in prompt

    result = ProjectUnderstandingResult(
        project_name="Core Modernization",
        project_key="MOD01",
        executive_summary="Modernizing legacy systems to cloud-native microservices.",
        key_objectives=["Cut latency by 50%", "Attain 99.99% uptime"],
        key_stakeholders=[{"name": "Alice", "role": "PM", "organization": "Product"}],
        suggested_milestones=[{"title": "MVP", "target_date": "2026-11-01", "description": "Core APIs"}],
        constraints_and_assumptions=["Must run on Azure"],
        initial_risks=["Database cutoff schedule tight"],
    )
    assert result.project_key == "MOD01"
    assert len(result.key_objectives) == 2


def test_requirement_extraction_schema_and_prompt():
    prompt = format_requirement_extraction_prompt("All users must be authenticated via Entra ID.", project_id="p-123")
    assert "p-123" in prompt
    assert "Entra ID" in prompt

    req = ExtractedRequirementItem(
        code="REQ-001",
        title="Entra ID SSO",
        description="OAuth2/OIDC integration with enterprise directory.",
        category="Security",
        priority=Priority.CRITICAL,
        acceptance_criteria=["MFA prompted", "Session lasts 8 hours"],
    )
    story = ExtractedUserStoryItem(
        code="US-001",
        title="Sign in with work email",
        as_a="Corporate employee",
        i_want="to log in using corporate credentials",
        so_that="I access internal portal seamlessly",
        story_points=3,
        priority=Priority.HIGH,
        acceptance_criteria=["Redirect to Microsoft login"],
    )
    res = RequirementExtractionResult(
        requirements=[req],
        user_stories=[story],
        unresolved_questions=["Is multi-tenant B2B required in Phase 1?"],
    )
    assert len(res.requirements) == 1
    assert len(res.user_stories) == 1
    assert res.user_stories[0].story_points == 3


def test_project_summary_schema_and_prompt():
    project_dict = {
        "id": "proj-999",
        "name": "Portal NextGen",
        "status": "ACTIVE",
        "milestones": ["Architecture Signoff (DONE)", "Alpha Release (IN_PROGRESS)"],
    }
    prompt = format_project_summarization_prompt(project_dict, include_risks=True)
    assert "Portal NextGen" in prompt
    assert "active risks and blockers are highlighted" in prompt

    summary = ProjectSummaryResult(
        project_id="proj-999",
        project_name="Portal NextGen",
        overall_status="ACTIVE",
        health_indicator="GREEN",
        completed_milestones=["Architecture Signoff"],
        upcoming_milestones=["Alpha Release"],
        top_risks=[{"title": "Third-party webhook latency", "mitigation": "Circuit breaker"}],
        active_blockers=[],
        pending_approval_count=1,
        executive_narrative="Project is progressing on schedule with all major components initialized.",
    )
    assert summary.health_indicator == "GREEN"
    assert summary.pending_approval_count == 1


def test_format_grounded_prompt_structure():
    prompt = format_grounded_prompt(
        user_request="Summarize blockers impacting Q3 release.",
        project_context={"project_id": "PRJ-1", "name": "Payment Gateway Modernization"},
        retrieved_evidence=[
            {"source": "PRD v1.2", "content": "PCI-DSS compliance review required before Q3 cutoff."},
            {"source": "Meeting Notes 2026-10-02", "content": "Payment gateway sandbox API credentials delayed."},
        ],
    )
    assert "### AUTHORITATIVE PROJECT STATE:" in prompt
    assert "Payment Gateway Modernization" in prompt
    assert "### RETRIEVED GROUNDED EVIDENCE PASSAGES:" in prompt
    assert "[1] Source: PRD v1.2" in prompt
    assert "PCI-DSS compliance" in prompt
    assert "[2] Source: Meeting Notes 2026-10-02" in prompt
    assert "### USER INQUIRY / TASK:" in prompt
    assert "Summarize blockers impacting Q3 release." in prompt
    assert "### GROUNDING INSTRUCTIONS:" in prompt
