"""
Agent state — the single source of truth for one agent run.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    planning = "planning"
    executing = "executing"
    observing = "observing"
    verifying = "verifying"
    completed = "completed"
    failed = "failed"


class ToolCallRecord(BaseModel):
    """Records a single tool invocation and its result."""
    tool_name: str
    arguments: dict
    result: Any = None
    success: bool = True
    error: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Source(BaseModel):
    """A web or document source referenced during the task."""
    title: str
    url: str
    source_type: str = "web"   # "web" | "file"


class AgentStep(BaseModel):
    """A single agent action shown to the user in the activity panel."""
    status: str               # "pending" | "running" | "done" | "error"
    label: str                # Human-readable, NO chain-of-thought
    detail: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentState(BaseModel):
    """Full state of a running agent task."""
    task: str
    conversation_id: str | None = None
    plan: list[str] = Field(default_factory=list)
    current_step: int = 0
    messages: list[dict] = Field(default_factory=list)   # LLM message history
    observations: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)        # uploaded filenames
    sources: list[Source] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)  # UI activity log
    final_answer: str | None = None
    status: AgentStatus = AgentStatus.planning
    iteration: int = 0
    error: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # ── Helpers ────────────────────────────────────────────────────────

    def add_step(self, label: str, status: str = "done", detail: str | None = None):
        self.steps.append(AgentStep(label=label, status=status, detail=detail))

    def add_observation(self, text: str):
        self.observations.append(text)

    def add_source(self, title: str, url: str, source_type: str = "web"):
        # Deduplicate by URL
        if not any(s.url == url for s in self.sources):
            self.sources.append(Source(title=title, url=url, source_type=source_type))

    def add_tool_call(self, tool_name: str, arguments: dict, result: Any, success: bool, error: str | None = None):
        self.tool_calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=success,
                error=error,
            )
        )
