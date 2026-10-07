"""ProgramSaathi Orchestrator coordinating services, tools, and human-approval boundaries."""

from typing import Any, Optional
from programsaathi.config import Settings, get_settings
from programsaathi.exceptions import EntityNotFoundError, HumanApprovalRequiredError
from programsaathi.logging import get_logger
from programsaathi.models.base import ApprovalStatus, utc_now
from programsaathi.models.governance import ApprovalRequest, ProjectEvent
from programsaathi.repositories.governance import (
    ApprovalRequestRepository,
    ProjectEventRepository,
)
from programsaathi.security.guardrails import SecurityGuard
from programsaathi.services.database import DatabaseServiceInterface
from programsaathi.services.llm import LLMServiceInterface
from programsaathi.services.search import SearchServiceInterface
from programsaathi.services.storage import BlobStorageServiceInterface
from programsaathi.tools.base import ToolContext, ToolResult
from programsaathi.tools.registry import ToolRegistry

logger = get_logger(__name__)


class ProgramSaathiOrchestrator:
    """Master orchestrator for ProgramSaathi.

    Coordinates capability workflows, enforces human-in-the-loop gates,
    and safeguards authoritative state changes.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_service: Optional[LLMServiceInterface] = None,
        storage_service: Optional[BlobStorageServiceInterface] = None,
        search_service: Optional[SearchServiceInterface] = None,
        database_service: Optional[DatabaseServiceInterface] = None,
        tool_registry: Optional[ToolRegistry] = None,
        approval_repo: Optional[ApprovalRequestRepository] = None,
        event_repo: Optional[ProjectEventRepository] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_service = llm_service
        self.storage_service = storage_service
        self.search_service = search_service
        self.database_service = database_service
        self.tool_registry = tool_registry or ToolRegistry()
        self.approval_repo = approval_repo
        self.event_repo = event_repo
        logger.info(f"{self.settings.app_name} Orchestrator initialized (env={self.settings.environment})")

    def execute_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        """Executes a registered tool within security and approval boundaries."""
        # 1. Security scan inputs for prohibited patterns
        SecurityGuard.inspect_payload(params, context_label=f"tool_params.{tool_name}")

        # 2. Lookup tool
        tool = self.tool_registry.get(tool_name)

        # 3. Log intention
        logger.info(
            f"Orchestrator executing tool '{tool_name}'",
            extra={"project_id": context.project_id, "actor_id": context.actor_id},
        )

        # 4. Execute tool
        result = tool.execute(params, context)

        # 5. Audit event logging if event repo is wired
        if self.event_repo:
            self.event_repo.create(
                ProjectEvent(
                    project_id=context.project_id,
                    event_type="TOOL_EXECUTED",
                    actor_type="AGENT",
                    actor_id=context.actor_id,
                    summary=f"Tool '{tool_name}' executed. Success: {result.success}",
                    payload={"tool": tool_name, "success": result.success, "requires_approval": result.requires_approval},
                )
            )

        return result

    def process_approval(
        self,
        request_id: str,
        reviewer_id: str,
        decision: ApprovalStatus,
        comments: Optional[str] = None,
    ) -> ApprovalRequest:
        """Processes formal human review for a pending mutation request."""
        if not self.approval_repo:
            raise EntityNotFoundError("ApprovalRequestRepository not configured in Orchestrator.")

        approval = self.approval_repo.get_by_id(request_id)
        if not approval:
            raise EntityNotFoundError(f"ApprovalRequest '{request_id}' not found.")

        approval.status = decision
        approval.reviewer_id = reviewer_id
        approval.review_comments = comments
        approval.reviewed_at = utc_now()
        self.approval_repo.update(approval)

        if self.event_repo:
            self.event_repo.create(
                ProjectEvent(
                    project_id=approval.project_id,
                    event_type=f"APPROVAL_{decision.value}",
                    actor_type="USER",
                    actor_id=reviewer_id,
                    entity_type=approval.entity_type,
                    entity_id=approval.entity_id,
                    summary=f"Human reviewer marked request {request_id} as {decision.value}.",
                    payload={"comments": comments, "decision": decision.value},
                )
            )

        logger.info(
            f"Approval request {request_id} transitioned to {decision.value} by reviewer {reviewer_id}",
            extra={"project_id": approval.project_id},
        )
        return approval
