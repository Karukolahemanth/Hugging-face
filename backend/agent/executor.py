"""
Executor — runs tool calls requested by the planner/LLM.
Translates raw LLM tool-call requests into registry lookups and returns observations.
"""

import json
from typing import Any

from backend.agent.state import AgentState
from backend.tools.registry import tool_registry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class Executor:
    """Executes tool calls and updates AgentState with observations."""

    async def run(
        self,
        state: AgentState,
        tool_name: str,
        arguments: dict,
    ) -> str:
        """
        Execute a tool, record the result in state, and return
        an observation string for the LLM.
        """
        logger.info("Executor -> %s | args: %s", tool_name, list(arguments.keys()))
        state.add_step(
            label=self._friendly_label(tool_name, arguments),
            status="running",
        )

        result = await tool_registry.execute(tool_name, arguments)

        # ── Update sources if web search ──────────────────────────────
        if tool_name == "web_search" and result.success:
            data = result.result or {}
            for item in data.get("results", []):
                state.add_source(
                    title=item.get("title", "Web result"),
                    url=item.get("url", ""),
                    source_type="web",
                )

        if tool_name == "read_webpage" and result.success:
            data = result.result or {}
            state.add_source(
                title=data.get("title", arguments.get("url", "")),
                url=arguments.get("url", ""),
                source_type="web",
            )

        # ── Record call ───────────────────────────────────────────────
        state.add_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            result=result.result,
            success=result.success,
            error=result.error,
        )

        # ── Update step status ────────────────────────────────────────
        state.steps[-1].status = "done" if result.success else "error"
        state.steps[-1].detail = result.error if not result.success else None

        # ── Build observation string ──────────────────────────────────
        if result.success:
            obs = f"[{tool_name}] SUCCESS:\n{self._format_result(result.result)}"
        else:
            obs = f"[{tool_name}] ERROR: {result.error}"

        state.add_observation(obs)
        logger.info("Executor <- %s | success=%s", tool_name, result.success)
        return obs

    @staticmethod
    def _format_result(result: Any) -> str:
        """Convert a result to a readable string for the LLM."""
        if isinstance(result, dict):
            return json.dumps(result, indent=2, default=str)[:6000]
        return str(result)[:6000]

    @staticmethod
    def _friendly_label(tool_name: str, arguments: dict) -> str:
        """Generate a safe, human-readable progress label (no CoT)."""
        labels = {
            "calculator": "🧮 Calculating...",
            "python_execute": "🐍 Running analysis...",
            "web_search": f"🔎 Searching: {arguments.get('query', '')[:50]}...",
            "read_webpage": f"📄 Reading: {arguments.get('url', '')[:60]}...",
            "read_file": f"📁 Reading file: {arguments.get('filename', '')}",
            "analyze_image": f"🖼️ Analyzing image: {arguments.get('filename', '')}",
        }
        return labels.get(tool_name, f"⚙️ Running {tool_name}...")
