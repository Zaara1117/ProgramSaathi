"""Read-only query and evidence tools for ProgramSaathi."""

from typing import Optional
from pydantic import BaseModel, Field
from programsaathi.tools.base import BaseTool, ToolContext, ToolResult
from programsaathi.repositories.project import ProjectRepository
from programsaathi.repositories.governance import ApprovalRequestRepository
from programsaathi.services.search import SearchServiceInterface


class GetProjectOverviewInput(BaseModel):
    project_id: str = Field(..., description="Project UUID to query")


class GetProjectOverviewTool(BaseTool):
    name = "get_project_overview"
    description = "Retrieves authoritative project status, business objectives, and metadata."
    input_schema = GetProjectOverviewInput
    requires_human_approval = False

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    def run(self, params: GetProjectOverviewInput, context: ToolContext) -> ToolResult:
        project = self.project_repo.get_by_id(params.project_id)
        if not project:
            return ToolResult(
                success=False,
                message=f"Project with ID '{params.project_id}' not found.",
                data=None,
            )
        return ToolResult(
            success=True,
            message="Project overview retrieved successfully.",
            data=project.model_dump(),
        )


class SearchEvidenceInput(BaseModel):
    query: str = Field(..., description="Query string for searching project documents")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum evidence passages to retrieve")


class SearchProjectEvidenceTool(BaseTool):
    name = "search_project_evidence"
    description = "Retrieves grounded text evidence and citations from ingested project documentation."
    input_schema = SearchEvidenceInput
    requires_human_approval = False

    def __init__(self, search_service: SearchServiceInterface) -> None:
        self.search_service = search_service

    def run(self, params: SearchEvidenceInput, context: ToolContext) -> ToolResult:
        results = self.search_service.search(query=params.query, top_k=params.top_k)
        return ToolResult(
            success=True,
            message=f"Found {len(results)} evidence chunks matching query.",
            data={"query": params.query, "results": results},
        )


class ListPendingApprovalsInput(BaseModel):
    project_id: str = Field(..., description="Target Project UUID")


class ListPendingApprovalsTool(BaseTool):
    name = "list_pending_approvals"
    description = "Lists all pending scope changes and mutations awaiting human approval."
    input_schema = ListPendingApprovalsInput
    requires_human_approval = False

    def __init__(self, approval_repo: ApprovalRequestRepository) -> None:
        self.approval_repo = approval_repo

    def run(self, params: ListPendingApprovalsInput, context: ToolContext) -> ToolResult:
        pending = self.approval_repo.list_pending(params.project_id)
        return ToolResult(
            success=True,
            message=f"Retrieved {len(pending)} pending approval requests.",
            data=[req.model_dump() for req in pending],
        )
