"""
Tool registry — central store for all agent tools.
The agent queries the registry to discover available tools and their schemas.
"""

from backend.tools.base import BaseTool, ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Holds all registered tools and provides lookup and schema generation."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance by its name."""
        if tool.name in self._tools:
            logger.warning("Tool '%s' is already registered — overwriting.", tool.name)
        self._tools[tool.name] = tool
        logger.info("Tool registered: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Return a tool by name, or None if not found."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_llm_schemas(self) -> list[dict]:
        """Return OpenAI-style tool definitions for all registered tools."""
        return [tool.to_llm_tool() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        """Look up and execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found in registry.",
            )
        logger.info("Executing tool: %s | args: %s", name, list(arguments.keys()))
        try:
            result = await tool.execute(arguments)
            return result
        except Exception as exc:
            logger.error("Tool '%s' raised exception: %s", name, exc)
            return ToolResult(success=False, error=str(exc))


# ── Singleton instance ────────────────────────────────────────────────────────
tool_registry = ToolRegistry()
