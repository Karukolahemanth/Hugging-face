"""
Planner — interprets LLM decisions (tool calls vs final answers) and
drives the agent loop.
"""

import json
import re
from typing import Literal

from pydantic import BaseModel

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.state import AgentState, AgentStatus
from backend.llm.base import BaseLLMProvider, Message
from backend.tools.registry import tool_registry
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Patterns that signal the LLM has produced a final answer.
# Matches "FINAL ANSWER:", "Final Answer:", "Answer:", "The answer is", etc.
_FINAL_ANSWER_PATTERNS = re.compile(
    r"(?:final\s+answer\s*:|answer\s*:|the\s+answer\s+is\s*:|"
    r"therefore[,\s]+the\s+(?:final\s+)?answer\s+is\s*:|"
    r"result\s*:|in\s+summary[,\s])",
    re.IGNORECASE,
)


class Decision(BaseModel):
    """What the planner decided to do next."""
    type: Literal["tool_call", "final", "error"]
    tool_name: str | None = None
    arguments: dict | None = None
    answer: str | None = None
    reason: str | None = None


class Planner:
    """Builds prompts, calls the LLM, and interprets its decision."""

    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def decide(self, state: AgentState) -> Decision:
        """
        Call the LLM with the current conversation history and
        return a structured Decision.
        """
        messages = self._build_messages(state)
        tools = tool_registry.get_llm_schemas()

        logger.info(
            "Planner: calling LLM (iteration=%d, history_len=%d)",
            state.iteration,
            len(messages),
        )

        try:
            response = await self._llm.chat(messages=messages, tools=tools)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            return Decision(type="error", reason=str(exc))

        # ── Tool call requested ───────────────────────────────────────
        if response.tool_calls:
            tc = response.tool_calls[0]   # handle one at a time
            tool_name = tc["name"]
            arguments = tc.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": arguments}

            # Append assistant message with tool call to history
            state.messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                }
            )

            logger.info("Planner -> tool_call: %s", tool_name)
            return Decision(type="tool_call", tool_name=tool_name, arguments=arguments)

        # ── Text response — check for final answer ────────────────────
        content = response.content or ""
        state.messages.append({"role": "assistant", "content": content})

        # Check for explicit FINAL ANSWER: marker (our prompt asks for this)
        if "FINAL ANSWER:" in content:
            answer = content.split("FINAL ANSWER:", 1)[1].strip()
            logger.info("Planner -> final answer (explicit marker)")
            return Decision(type="final", answer=answer)

        # Also detect common natural-language answer patterns
        if _FINAL_ANSWER_PATTERNS.search(content):
            logger.info("Planner -> final answer (pattern match)")
            return Decision(type="final", answer=content.strip())

        # If we already ran at least one tool and got a text-only reply,
        # treat it as a final answer — the model is summarising its findings.
        # BUT reject answers that are just tool-call echo text.
        tool_calls_done = sum(
            1 for m in state.messages
            if m.get("role") == "assistant" and m.get("tool_calls")
        )
        is_tool_echo = content.strip().startswith("<tool_use") or content.strip().startswith("[Called tool")
        if tool_calls_done >= 1 and content.strip() and not is_tool_echo:
            logger.info(
                "Planner -> final answer (post-tool text after %d tool calls)",
                tool_calls_done,
            )
            return Decision(type="final", answer=content.strip())

        # No tool call, no detectable final answer — treat as continuation
        if content.strip():
            logger.info("Planner -> continuation (LLM thinking aloud)")
            return Decision(type="tool_call", tool_name=None, arguments=None)

        # Truly empty response — signal completion
        logger.warning("Planner -> empty LLM response; forcing final answer")
        return Decision(
            type="final",
            answer="I was unable to produce a complete answer. Please try rephrasing your question.",
        )

    # ── private helpers ───────────────────────────────────────────────

    def _build_messages(self, state: AgentState) -> list[Message]:
        """Construct the full message list for the LLM."""
        messages: list[Message] = [
            Message(role="system", content=SYSTEM_PROMPT)
        ]

        # Rebuild from state.messages (stored as dicts)
        for m in state.messages:
            messages.append(
                Message(
                    role=m["role"],
                    content=m.get("content") or "",
                    tool_calls=m.get("tool_calls"),
                    tool_call_id=m.get("tool_call_id"),
                )
            )

        return messages

    def inject_tool_result(self, state: AgentState, tool_name: str, observation: str):
        """Add a tool result message to state history."""
        state.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_name,
                "content": observation,
            }
        )
