"""
Base tool interface.
Every tool must subclass BaseTool and implement execute() and schema().
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolResult(BaseModel):
    """Standardised result returned by every tool."""
    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict | None = None


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, arguments: dict) -> ToolResult:
        """Execute the tool with given arguments."""

    @abstractmethod
    def schema(self) -> dict:
        """Return an OpenAI-style function schema for this tool."""

    def to_llm_tool(self) -> dict:
        """Wrap schema() in the OpenAI tool envelope."""
        return {
            "type": "function",
            "function": self.schema(),
        }
