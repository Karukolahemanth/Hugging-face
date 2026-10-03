"""
Google Gemini LLM provider.
Uses the new `google-genai` SDK (google.genai) with tool/function-calling support.
The older `google-generativeai` package is deprecated as of 2025.
"""

import json
from typing import Any

from backend.llm.base import BaseLLMProvider, LLMResponse, Message
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Wraps the Google Gemini API using the new google-genai SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Please add it to your backend/.env file."
            )
        from google import genai
        from google.genai import types as genai_types

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._types = genai_types
        self._model_name = settings.gemini_model
        logger.info("GeminiProvider initialised — model: %s", self._model_name)

    @property
    def provider_name(self) -> str:
        return "gemini"

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _to_contents(messages: list[Message]) -> list[dict]:
        """
        Convert internal Message list to Gemini Content dicts.
        System messages are handled via system_instruction; skip them here.

        NOTE: gemini-3.8-flash (thinking model) raises 400 INVALID_ARGUMENT when
        function_call parts are replayed without a thought_signature.
        Workaround: represent tool calls and results as plain text so the model
        retains full context without triggering the signature check.
        """
        contents = []
        for msg in messages:
            if msg.role == "system":
                continue  # handled by system_instruction in GenerateContentConfig

            elif msg.role == "assistant":
                text_parts: list[str] = []
                if msg.content:
                    text_parts.append(msg.content)
                # Represent tool calls as readable text (avoids thought_signature error).
                # Use a format the model won't echo back as a "final answer".
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        args = tc.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        text_parts.append(
                            f"<tool_use name=\"{tc['name']}\" args=\"{json.dumps(args)}\"/>"
                        )
                if text_parts:
                    contents.append({
                        "role": "model",
                        "parts": [{"text": "\n".join(text_parts)}],
                    })

            elif msg.role == "tool":
                # Represent tool results as a user message (plain text, no function_response)
                contents.append({
                    "role": "user",
                    "parts": [{
                        "text": f"[Tool result for {msg.tool_call_id or 'tool'}]: {msg.content}"
                    }],
                })

            else:  # user
                if msg.content:
                    contents.append({
                        "role": "user",
                        "parts": [{"text": msg.content}],
                    })
        return contents

    @staticmethod
    def _build_tools(tools: list[dict]) -> list[dict]:
        """Convert OpenAI-style tool schemas to Gemini function declarations."""
        declarations = []
        for tool in tools:
            fn = tool.get("function", tool)
            declarations.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            })
        return [{"function_declarations": declarations}]

    # ── public interface ─────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        from google.genai import types as gtypes

        contents = self._to_contents(messages)

        # Extract system instruction from the first system message if present
        system_instruction = None
        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
                break

        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if tools:
            config_kwargs["tools"] = self._build_tools(tools)

        generate_config = gtypes.GenerateContentConfig(
            system_instruction=system_instruction,
            **config_kwargs,
        )

        # Ensure at least one user message (Gemini requires it)
        if not contents or contents[0]["role"] != "user":
            contents = [{"role": "user", "parts": [{"text": "Begin."}]}] + contents

        # Retry with exponential back-off for transient 503 errors ONLY.
        # 429 RESOURCE_EXHAUSTED with a retryDelay of hours is NOT retryable here.
        import asyncio
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=generate_config,
                )
                return self._parse_response(response)
            except Exception as exc:
                err_str = str(exc)
                # Daily quota exhausted — no point retrying for hours
                if "RESOURCE_EXHAUSTED" in err_str and "retryDelay" in err_str:
                    logger.error("Gemini daily quota exhausted: %s", exc)
                    raise
                # Transient overload — retry with back-off
                if any(code in err_str for code in ("503", "429", "UNAVAILABLE")):
                    wait = 2 ** attempt          # 1s, 2s, 4s
                    logger.warning(
                        "Gemini transient error (attempt %d/3), retrying in %ds: %s",
                        attempt + 1, wait, exc,
                    )
                    last_exc = exc
                    await asyncio.sleep(wait)
                else:
                    logger.error("Gemini chat error: %s", exc)
                    raise
        logger.error("Gemini failed after 3 retries: %s", last_exc)
        raise last_exc  # type: ignore[misc]

    async def vision_chat(
        self,
        messages: list[Message],
        image_data: str,
        image_mime: str,
        temperature: float = 0.0,
    ) -> LLMResponse:
        import base64
        from google.genai import types as gtypes

        last_user = next(
            (m for m in reversed(messages) if m.role == "user"), None
        )
        prompt_text = last_user.content if last_user else "Describe this image."

        image_bytes = base64.b64decode(image_data)

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=[
                gtypes.Part.from_bytes(data=image_bytes, mime_type=image_mime),
                prompt_text,
            ],
            config=gtypes.GenerateContentConfig(temperature=temperature),
        )
        return self._parse_response(response)

    # ── internal ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(response) -> LLMResponse:
        """Parse a Gemini GenerateContentResponse into LLMResponse."""
        try:
            candidate = response.candidates[0]
            tool_calls = []
            text_parts = []

            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                    fc = part.function_call
                    tool_calls.append({
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            finish = str(candidate.finish_reason)

            # If model stopped with neither text nor tool calls, return a
            # best-effort text so the planner doesn't crash.
            if not text_parts and not tool_calls:
                logger.warning("Gemini returned empty response (finish=%s)", finish)
                return LLMResponse(
                    content="FINAL ANSWER: I was unable to determine the answer.",
                    finish_reason=finish,
                )

            return LLMResponse(
                content="\n".join(text_parts) if text_parts else None,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=finish,
            )
        except Exception as exc:
            logger.error("Error parsing Gemini response: %s", exc)
            return LLMResponse(content=str(response), finish_reason="error")
