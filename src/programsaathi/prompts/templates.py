"""Prompt templates and structured schema models for ProgramSaathi core workflows."""

import json
from typing import Any, Optional
from pydantic import BaseModel, Field

from programsaathi.models.base import Priority, ItemStatus


# ------------------------------------------------------------------------------
# Structured Output Schemas
# ------------------------------------------------------------------------------

class ProjectUnderstandingResult(BaseModel):
    """Structured extraction of high-level project charter from documentation."""

    project_name: str = Field(..., description="Identified or suggested project name")
    project_key: str = Field(..., min_length=2, max_length=10, description="Short 2-6 character project key, e.g. 'NGCP'")
    executive_summary: str = Field(..., description="High-level narrative of project goals and business value")
    key_objectives: list[str] = Field(default_factory=list, description="Primary business or technical OKRs / goals")
    target_completion_date: Optional[str] = Field(default=None, description="Projected completion timeline or quarter")
    key_stakeholders: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of stakeholders with 'name', 'role', and 'organization'",
    )
    suggested_milestones: list[dict[str, str]] = Field(
        default_factory=list,
        description="Major phase gates with 'title', 'target_date', and 'description'",
    )
    constraints_and_assumptions: list[str] = Field(default_factory=list, description="Identified constraints or boundary conditions")
    initial_risks: list[str] = Field(default_factory=list, description="Explicit or implicit delivery risks identified")


class ExtractedRequirementItem(BaseModel):
    """Discrete requirement extracted from specification."""

    code: str = Field(..., description="Identifier, e.g., 'REQ-001'")
    title: str = Field(..., description="Short summary of requirement")
    description: str = Field(..., description="Complete functional or non-functional requirement details")
    category: str = Field(default="Functional", description="Category: Functional, Non-Functional, Security, Compliance")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority rating")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Testable criteria for completion")


class ExtractedUserStoryItem(BaseModel):
    """Discrete agile story extracted or derived from requirements."""

    code: str = Field(..., description="Identifier, e.g., 'US-010'")
    title: str = Field(..., description="Story summary")
    as_a: str = Field(..., description="Persona or role")
    i_want: str = Field(..., description="Action or capability")
    so_that: str = Field(..., description="Benefit or value")
    story_points: Optional[int] = Field(default=None, ge=1, le=100, description="Agile point estimate")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Explicit acceptance criteria")


class RequirementExtractionResult(BaseModel):
    """Structured collection of extracted requirements and user stories."""

    requirements: list[ExtractedRequirementItem] = Field(default_factory=list, description="List of discrete requirements")
    user_stories: list[ExtractedUserStoryItem] = Field(default_factory=list, description="List of decomposed agile stories")
    unresolved_questions: list[str] = Field(
        default_factory=list,
        description="Gaps, ambiguities, or missing specifications in the input text",
    )


class ProjectSummaryResult(BaseModel):
    """Executive project status report."""

    project_id: str = Field(..., description="Target Project UUID")
    project_name: str = Field(..., description="Project Name")
    overall_status: str = Field(..., description="Status, e.g., ACTIVE, PLANNING, AT_RISK")
    health_indicator: str = Field(..., description="Overall health: 'GREEN', 'AMBER', or 'RED'")
    completed_milestones: list[str] = Field(default_factory=list, description="Milestones achieved")
    upcoming_milestones: list[str] = Field(default_factory=list, description="Upcoming target milestones")
    top_risks: list[dict[str, str]] = Field(default_factory=list, description="Critical risks and mitigations")
    active_blockers: list[dict[str, str]] = Field(default_factory=list, description="Active impeding blockers")
    pending_approval_count: int = Field(default=0, ge=0, description="Number of proposals awaiting human signoff")
    executive_narrative: str = Field(..., description="Comprehensive status summary for stakeholders")


# ------------------------------------------------------------------------------
# Prompt Formatters
# ------------------------------------------------------------------------------

def format_project_understanding_prompt(document_text: str, project_name_hint: Optional[str] = None) -> str:
    """Constructs prompt for digesting project intake / PRD document."""
    hint_clause = f"The expected project name hint is: '{project_name_hint}'." if project_name_hint else ""
    return f"""Analyze the following project intake document, PRD, or charter.
Extract the project parameters, business objectives, milestones, stakeholders, and risks.
{hint_clause}

DOCUMENT CONTENT:
---
{document_text}
---

Produce a rigorous, structured project understanding output according to the requested schema.
"""


def format_requirement_extraction_prompt(document_text: str, project_id: Optional[str] = None) -> str:
    """Constructs prompt for extracting requirements and decomposing into user stories."""
    proj_clause = f"Target Project ID: {project_id}" if project_id else ""
    return f"""Analyze the following specification or requirement text.
Extract all discrete functional and non-functional requirements with verifiable acceptance criteria.
Where appropriate, decompose requirements into persona-centric Agile User Stories.
Identify any ambiguities or unresolved questions in the specification.
{proj_clause}

SPECIFICATION TEXT:
---
{document_text}
---

Produce a validated requirements extraction result conforming to the requested schema.
"""


def format_project_summarization_prompt(project_data: dict[str, Any], include_risks: bool = True) -> str:
    """Constructs prompt for synthesizing an executive project health report."""
    serialized_context = json.dumps(project_data, indent=2, default=str)
    risk_clause = "Ensure active risks and blockers are highlighted." if include_risks else ""
    return f"""Synthesize an authoritative, executive-level project status summary from the current project state below.
Assess overall delivery health (GREEN, AMBER, RED) based on milestone progress, active blockers, and unresolved scope proposals.
{risk_clause}

CURRENT PROJECT STATE:
---
{serialized_context}
---

Produce an executive project summary result conforming to the requested schema.
"""


def format_grounded_prompt(
    user_request: str,
    project_context: Optional[dict[str, Any] | str] = None,
    retrieved_evidence: Optional[list[dict[str, Any] | str]] = None,
) -> str:
    """Builds a grounded prompt combining user request, authoritative project context, and retrieved evidence."""
    sections: list[str] = []

    # 1. Authoritative Project Context
    if project_context:
        if isinstance(project_context, dict):
            context_str = json.dumps(project_context, indent=2, default=str)
        else:
            context_str = str(project_context)
        sections.append(f"### AUTHORITATIVE PROJECT STATE:\n```json\n{context_str}\n```")

    # 2. Retrieved Evidence from Azure AI Search
    if retrieved_evidence:
        evidence_lines: list[str] = []
        for idx, item in enumerate(retrieved_evidence, 1):
            if isinstance(item, dict):
                src = item.get("source", item.get("title", f"Document #{idx}"))
                content = item.get("content", item.get("text", str(item)))
                evidence_lines.append(f"[{idx}] Source: {src}\n{content}")
            else:
                evidence_lines.append(f"[{idx}] {item}")
        sections.append("### RETRIEVED GROUNDED EVIDENCE PASSAGES:\n" + "\n\n".join(evidence_lines))

    # 3. User Request & Instructions
    sections.append(f"""### USER INQUIRY / TASK:
{user_request}

### GROUNDING INSTRUCTIONS:
- Base your response strictly on the Authoritative Project State and Retrieved Evidence passages provided above.
- If the available evidence does not contain sufficient details to answer authoritatively, state the limitation clearly.
- If proposing changes to the project plan, remember that all consequential mutations require human sign-off.
""")

    return "\n\n".join(sections)
