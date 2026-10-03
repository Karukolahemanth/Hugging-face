"""
Core GAIA Agent — implements the full reasoning loop.

Loop:
  USER TASK -> PLANNING -> TOOL SELECTION -> TOOL EXECUTION
  -> OBSERVATION -> VERIFY -> REPLAN? -> FINAL ANSWER
"""

import asyncio
import uuid
from typing import AsyncGenerator

from backend.agent.executor import Executor
from backend.agent.planner import Planner, Decision
from backend.agent.state import AgentState, AgentStatus
from backend.llm import get_llm_provider
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class GAIAAgent:
    """
    The main agent orchestrator.
    Drives the plan -> execute -> observe -> verify loop until complete or
    the maximum iteration limit is reached.
    """

    def __init__(self) -> None:
        settings = get_settings()
        llm = get_llm_provider()
        self._planner = Planner(llm)
        self._executor = Executor()
        self._max_steps = settings.max_agent_steps

    async def run(
        self,
        task: str,
        conversation_id: str | None = None,
        files: list[str] | None = None,
    ) -> AgentState:
        """
        Run the agent on a task and return the final state.
        Non-streaming version.
        """
        state = self._init_state(task, conversation_id, files)
        await self._loop(state)
        return state

    async def stream(
        self,
        task: str,
        conversation_id: str | None = None,
        files: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Streaming version — yields Server-Sent Event payloads as dicts.
        Only safe high-level events are emitted (no chain-of-thought).
        """
        state = self._init_state(task, conversation_id, files)

        yield {"event": "status", "data": {"status": "planning", "message": "🧠 Understanding task..."}}
        state.add_step("Task received", status="done")

        async for event in self._loop_streaming(state):
            yield event

        if state.status == AgentStatus.completed:
            yield {
                "event": "final_answer",
                "data": {
                    "answer": state.final_answer,
                    "sources": [s.model_dump() for s in state.sources],
                    "steps": [s.model_dump() for s in state.steps],
                    "tool_calls": [tc.model_dump() for tc in state.tool_calls],
                },
            }
        else:
            yield {
                "event": "error",
                "data": {"error": state.error or "Agent failed without a reason."},
            }

    # ── Private ─────────────────────────────────────────────────────────

    def _init_state(
        self,
        task: str,
        conversation_id: str | None,
        files: list[str] | None,
    ) -> AgentState:
        state = AgentState(
            task=task,
            conversation_id=conversation_id or str(uuid.uuid4()),
            files=files or [],
        )
        # Inject the initial user message
        context = task
        if files:
            context += f"\n\nUploaded files available: {', '.join(files)}"
        state.messages.append({"role": "user", "content": context})
        logger.info("Agent started — task: %s", task[:80])
        return state

    def _build_fallback_answer(self, state: AgentState) -> str:
        """
        Build a best-effort answer from successful tool results when the LLM
        is temporarily unavailable (e.g. 503 / rate-limit).
        """
        successful = [
            tc for tc in state.tool_calls if tc.success and tc.result is not None
        ]
        if not successful:
            return "I was unable to complete this task due to a temporary API issue. Please try again."

        parts = [f"Based on tool results:"]
        for tc in successful:
            parts.append(f"• {tc.tool_name}: {tc.result}")
        return "\n".join(parts)

    async def _loop(self, state: AgentState) -> None:
        """Blocking agent loop."""
        while state.iteration < self._max_steps:
            state.iteration += 1
            state.status = AgentStatus.planning

            decision = await self._planner.decide(state)

            if decision.type == "error":
                # If tools already ran successfully, synthesise an answer
                # rather than returning "failed" due to a transient LLM error.
                if state.tool_calls and any(tc.success for tc in state.tool_calls):
                    logger.warning(
                        "LLM error after successful tool runs — synthesising answer: %s",
                        decision.reason,
                    )
                    state.final_answer = self._build_fallback_answer(state)
                    state.status = AgentStatus.completed
                    state.add_step("Answer synthesised from tool results", status="done")
                else:
                    state.status = AgentStatus.failed
                    state.error = decision.reason
                    state.add_step("Agent error", status="error", detail=decision.reason)
                break

            if decision.type == "final":
                state.final_answer = decision.answer
                state.status = AgentStatus.completed
                state.add_step("✅ Final answer ready", status="done")
                logger.info("Agent completed in %d iterations.", state.iteration)
                break

            if decision.type == "tool_call":
                if not decision.tool_name:
                    # LLM produced text without a tool call and without FINAL ANSWER
                    last_msg = state.messages[-1] if state.messages else {}
                    state.final_answer = last_msg.get("content", "I could not determine an answer.")
                    state.status = AgentStatus.completed
                    break

                state.status = AgentStatus.executing
                observation = await self._executor.run(
                    state,
                    decision.tool_name,
                    decision.arguments or {},
                )
                # Feed observation back to LLM
                self._planner.inject_tool_result(state, decision.tool_name, observation)
                state.status = AgentStatus.observing

        else:
            # Hit max steps
            state.status = AgentStatus.failed
            state.error = f"Exceeded maximum of {self._max_steps} steps."
            state.final_answer = (
                "I reached the maximum number of reasoning steps. "
                "Here is my best answer based on what I have gathered:\n\n"
                + "\n".join(state.observations[-3:])
            )
            state.add_step("⚠️ Max steps reached", status="error")

    async def _loop_streaming(self, state: AgentState) -> AsyncGenerator[dict, None]:
        """Streaming agent loop — yields events after each step."""
        while state.iteration < self._max_steps:
            state.iteration += 1

            decision = await self._planner.decide(state)

            if decision.type == "error":
                # If tools already ran, synthesise answer from results
                if state.tool_calls and any(tc.success for tc in state.tool_calls):
                    logger.warning(
                        "LLM error after successful tools — synthesising answer: %s",
                        decision.reason,
                    )
                    state.final_answer = self._build_fallback_answer(state)
                    state.status = AgentStatus.completed
                    state.add_step("Answer synthesised from tool results", status="done")
                else:
                    state.status = AgentStatus.failed
                    state.error = decision.reason
                    yield {"event": "error", "data": {"error": decision.reason}}
                return

            if decision.type == "final":
                state.final_answer = decision.answer
                state.status = AgentStatus.completed
                state.add_step("✅ Final answer ready", status="done")
                return

            if decision.type == "tool_call":
                if not decision.tool_name:
                    last_msg = state.messages[-1] if state.messages else {}
                    state.final_answer = last_msg.get("content", "")
                    state.status = AgentStatus.completed
                    return

                state.status = AgentStatus.executing

                label = self._executor._friendly_label(
                    decision.tool_name, decision.arguments or {}
                )
                yield {
                    "event": "tool_started",
                    "data": {
                        "tool": decision.tool_name,
                        "label": label,
                        "step": state.iteration,
                    },
                }

                observation = await self._executor.run(
                    state,
                    decision.tool_name,
                    decision.arguments or {},
                )

                yield {
                    "event": "tool_completed",
                    "data": {
                        "tool": decision.tool_name,
                        "label": label,
                        "success": state.tool_calls[-1].success if state.tool_calls else True,
                        "step": state.iteration,
                    },
                }

                self._planner.inject_tool_result(state, decision.tool_name, observation)
                state.status = AgentStatus.observing

                yield {
                    "event": "status",
                    "data": {
                        "status": "observing",
                        "message": "🔍 Reviewing results...",
                        "step": state.iteration,
                    },
                }

        # Max steps
        state.status = AgentStatus.failed
        state.error = f"Exceeded maximum of {self._max_steps} steps."
        state.final_answer = (
            "Reached step limit. Best answer from gathered information:\n\n"
            + "\n".join(state.observations[-3:])
        )
        yield {
            "event": "error",
            "data": {"error": state.error},
        }
