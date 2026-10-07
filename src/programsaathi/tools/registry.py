"""Central registry for managing, discovering, and dispatching agent tools."""

from typing import Any, Optional
from programsaathi.tools.base import BaseTool, ToolContext, ToolResult
from programsaathi.exceptions import EntityNotFoundError
from programsaathi.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Registry maintaining available tools for the ProgramSaathi orchestrator."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance in the registry."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting already registered tool: {tool.name}")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool '{tool.name}' (requires_approval={tool.requires_human_approval})")

    def get(self, name: str) -> BaseTool:
        """Retrieves a registered tool by its name."""
        if name not in self._tools:
            raise EntityNotFoundError(f"Tool '{name}' is not registered in ToolRegistry.")
        return self._tools[name]

    def list_tools(self) -> list[BaseTool]:
        """Lists all registered tools."""
        return list(self._tools.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Returns standard OpenAI / Foundry tool schema definitions for all registered tools."""
        return [tool.get_openai_tool_definition() for tool in self._tools.values()]

    def execute(self, tool_name: str, raw_params: dict[str, Any], context: ToolContext) -> ToolResult:
        """Dispatches execution to a registered tool."""
        tool = self.get(tool_name)
        return tool.execute(raw_params, context)
