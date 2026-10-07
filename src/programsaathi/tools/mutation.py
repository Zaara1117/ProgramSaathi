"""Mutation and proposal tools implementing human-in-the-loop safeguards."""

from typing import Optional
from pydantic import BaseModel, Field
from programsaathi.tools.base import BaseTool, ToolContext, ToolResult
from programsaathi.models.base import ApprovalStatus, ScopeChangeImpact, ItemStatus, Priority
from programsaathi.models.governance import ScopeChange, ApprovalRequest, ProjectEvent
from programsaathi.models.work_items import Task
from programsaathi.repositories.governance import (
    ScopeChangeRepository,
    ApprovalRequestRepository,
    ProjectEventRepository,
)
from programsaathi.repositories.work_item import TaskRepository


class ProposeScopeChangeInput(BaseModel):
    project_id: str = Field(..., description="Target Project UUID")
    code: str = Field(..., description="Unique CR code, e.g., 'CR-001'")
    title: str = Field(..., description="Scope change title")
    description: str = Field(..., description="Detailed explanation of change")
    reason: str = Field(..., description="Business rationale")
    impact_level: ScopeChangeImpact = Field(default=ScopeChangeImpact.MODERATE)
    schedule_impact_days: int = Field(default=0)
    budget_impact: float = Field(default=0.0)


class ProposeScopeChangeTool(BaseTool):
    name = "propose_scope_change"
    description = "Proposes a formal scope change requiring human stakeholder approval."
    input_schema = ProposeScopeChangeInput
    requires_human_approval = True

    def __init__(
        self,
        scope_repo: ScopeChangeRepository,
        approval_repo: ApprovalRequestRepository,
        event_repo: ProjectEventRepository,
    ) -> None:
        self.scope_repo = scope_repo
        self.approval_repo = approval_repo
        self.event_repo = event_repo

    def propose(self, params: ProposeScopeChangeInput, context: ToolContext) -> ToolResult:
        # Step 1: Create the unapproved ScopeChange entity
        scope_change = ScopeChange(
            project_id=params.project_id,
            code=params.code,
            title=params.title,
            description=params.description,
            reason=params.reason,
            impact_level=params.impact_level,
            schedule_impact_days=params.schedule_impact_days,
            budget_impact=params.budget_impact,
            status=ApprovalStatus.PENDING,
            proposed_by_id=context.actor_id,
        )
        self.scope_repo.create(scope_change)

        # Step 2: Create formal ApprovalRequest gate
        approval_req = ApprovalRequest(
            project_id=params.project_id,
            entity_type="ScopeChange",
            entity_id=scope_change.id,
            action_type="CREATE",
            requested_by=context.actor_id,
            summary=f"Scope Change proposed: {params.title}",
            proposed_diff=scope_change.model_dump(),
            status=ApprovalStatus.PENDING,
        )
        self.approval_repo.create(approval_req)

        # Step 3: Record audit event
        self.event_repo.create(
            ProjectEvent(
                project_id=params.project_id,
                event_type="SCOPE_CHANGE_PROPOSED",
                actor_type="AGENT" if context.actor_id.startswith("agent") else "USER",
                actor_id=context.actor_id,
                entity_type="ScopeChange",
                entity_id=scope_change.id,
                summary=f"Proposed scope change '{params.title}' awaiting approval.",
                payload={"approval_request_id": approval_req.id},
            )
        )

        return ToolResult(
            success=True,
            message=f"Scope change '{params.title}' created and queued for human approval.",
            data={"scope_change": scope_change.model_dump(), "approval_request_id": approval_req.id},
            requires_approval=True,
            approval_request_id=approval_req.id,
        )

    def run(self, params: ProposeScopeChangeInput, context: ToolContext) -> ToolResult:
        # Executed once formal human approval is confirmed
        scope_change = ScopeChange(
            project_id=params.project_id,
            code=params.code,
            title=params.title,
            description=params.description,
            reason=params.reason,
            impact_level=params.impact_level,
            schedule_impact_days=params.schedule_impact_days,
            budget_impact=params.budget_impact,
            status=ApprovalStatus.APPROVED,
            proposed_by_id=context.actor_id,
        )
        self.scope_repo.create(scope_change)

        self.event_repo.create(
            ProjectEvent(
                project_id=params.project_id,
                event_type="SCOPE_CHANGE_COMMITTED",
                actor_type="USER",
                actor_id=context.actor_id,
                entity_type="ScopeChange",
                entity_id=scope_change.id,
                summary=f"Scope change '{params.title}' ratified and applied to authoritative state.",
            )
        )

        return ToolResult(
            success=True,
            message=f"Scope change '{params.title}' successfully approved and committed.",
            data=scope_change.model_dump(),
            requires_approval=False,
        )


class ProposeTaskInput(BaseModel):
    project_id: str = Field(..., description="Target Project UUID")
    code: str = Field(..., description="Task code, e.g., 'TSK-100'")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    priority: Priority = Field(default=Priority.MEDIUM)
    estimated_hours: Optional[float] = Field(default=None)


class ProposeTaskCreationTool(BaseTool):
    name = "propose_task_creation"
    description = "Proposes a new task to be added to project plan, requiring signoff."
    input_schema = ProposeTaskInput
    requires_human_approval = True

    def __init__(
        self,
        task_repo: TaskRepository,
        approval_repo: ApprovalRequestRepository,
        event_repo: ProjectEventRepository,
    ) -> None:
        self.task_repo = task_repo
        self.approval_repo = approval_repo
        self.event_repo = event_repo

    def propose(self, params: ProposeTaskInput, context: ToolContext) -> ToolResult:
        task = Task(
            project_id=params.project_id,
            code=params.code,
            title=params.title,
            description=params.description,
            priority=params.priority,
            estimated_hours=params.estimated_hours,
            status=ItemStatus.PROPOSED,
        )
        self.task_repo.create(task)

        approval_req = ApprovalRequest(
            project_id=params.project_id,
            entity_type="Task",
            entity_id=task.id,
            action_type="CREATE",
            requested_by=context.actor_id,
            summary=f"Task creation proposed: {params.title}",
            proposed_diff=task.model_dump(),
            status=ApprovalStatus.PENDING,
        )
        self.approval_repo.create(approval_req)

        self.event_repo.create(
            ProjectEvent(
                project_id=params.project_id,
                event_type="TASK_PROPOSED",
                actor_type="AGENT",
                actor_id=context.actor_id,
                entity_type="Task",
                entity_id=task.id,
                summary=f"Task '{params.title}' proposed awaiting approval.",
            )
        )

        return ToolResult(
            success=True,
            message=f"Task '{params.title}' proposed and queued for approval.",
            data={"task": task.model_dump(), "approval_request_id": approval_req.id},
            requires_approval=True,
            approval_request_id=approval_req.id,
        )

    def run(self, params: ProposeTaskInput, context: ToolContext) -> ToolResult:
        task = Task(
            project_id=params.project_id,
            code=params.code,
            title=params.title,
            description=params.description,
            priority=params.priority,
            estimated_hours=params.estimated_hours,
            status=ItemStatus.TODO,
        )
        self.task_repo.create(task)

        self.event_repo.create(
            ProjectEvent(
                project_id=params.project_id,
                event_type="TASK_COMMITTED",
                actor_type="USER",
                actor_id=context.actor_id,
                entity_type="Task",
                entity_id=task.id,
                summary=f"Task '{params.title}' approved and added to active backlog.",
            )
        )

        return ToolResult(
            success=True,
            message=f"Task '{params.title}' created successfully.",
            data=task.model_dump(),
            requires_approval=False,
        )
