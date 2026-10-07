"""Tool framework establishing boundaries, schemas, and human-approval gates."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from programsaathi.exceptions import HumanApprovalRequiredError


class ToolContext(BaseModel):
    """Runtime context passed into tool execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_id: str = Field(..., description="Target Project UUID")
    actor_id: str = Field(default="system", description="Identifier of the executing user or agent")
    is_human_approved: bool = Field(default=False, description="Flag indicating human approval was confirmed")
    approval_request_id: Optional[str] = Field(default=None, description="Linked ApprovalRequest UUID if approved")


class ToolResult(BaseModel):
    """Structured result returned by tool execution."""

    success: bool = Field(..., description="Whether tool execution succeeded")
    message: str = Field(..., description="Human/LLM readable status message")
    data: Any = Field(default=None, description="Structured output payload")
    requires_approval: bool = Field(default=False, description="Whether this action requires human signoff")
    approval_request_id: Optional[str] = Field(default=None, description="Generated ApprovalRequest ID if gated")


class BaseTool(ABC):
    """Abstract base class for all ProgramSaathi tools."""

    name: str
    description: str
    input_schema: Type[BaseModel]
    requires_human_approval: bool = False

    @abstractmethod
    def run(self, params: BaseModel, context: ToolContext) -> ToolResult:
        """Executes the tool with validated parameters and execution context."""
        pass

    def execute(self, raw_params: dict[str, Any], context: ToolContext) -> ToolResult:
        """Validates raw parameters against schema and executes with approval safeguards."""
        validated_params = self.input_schema.model_validate(raw_params)

        if self.requires_human_approval and not context.is_human_approved:
            # Subclasses can implement a propose method or return a pending proposal
            return self.propose(validated_params, context)

        return self.run(validated_params, context)

    def propose(self, params: BaseModel, context: ToolContext) -> ToolResult:
        """Default handler when consequential tool is invoked without human signoff."""
        raise HumanApprovalRequiredError(
            f"Action '{self.name}' requires formal human approval before mutating project state.",
            details={"tool": self.name, "params": params.model_dump()},
        )

    def get_openai_tool_definition(self) -> dict[str, Any]:
        """Generates OpenAI / Foundry function calling JSON schema representation."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema.model_json_schema(),
            },
        }
