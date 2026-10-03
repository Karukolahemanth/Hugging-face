"""
OpenAI-compatible LLM provider.
Works with OpenAI, Together, Groq, Ollama, and any OpenAI-compatible API.
"""

import json
from openai import AsyncOpenAI

from backend.llm.base import BaseLLMProvider, LLMResponse, Message
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """Wraps any OpenAI-compatible chat-completions API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Please add it to your .env file."
            )
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._model = settings.openai_model
        logger.info("OpenAIProvider initialised — model: %s", self._model)

    @property
    def provider_name(self) -> str:
        return "openai"

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _to_openai_messages(messages: list[Message]) -> list[dict]:
        result = []
        for msg in messages:
            if msg.role == "tool":
                result.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id or "unknown",
                        "content": msg.content,
                    }
                )
            elif msg.role == "assistant" and msg.tool_calls:
                openai_tool_calls = []
                for i, tc in enumerate(msg.tool_calls):
                    args = tc["arguments"]
                    if isinstance(args, dict):
                        args = json.dumps(args)
                    openai_tool_calls.append(
                        {
                            "id": f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": args,
                            },
                        }
                    )
                result.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": openai_tool_calls,
                    }
                )
            else:
                result.append({"role": msg.role, "content": msg.content})
        return result

    # ── public interface ─────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        openai_messages = self._to_openai_messages(messages)
        kwargs: dict = {
            "model": self._model,
            "messages": openai_messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self._client.chat.completions.create(**kwargs)
            return self._parse_response(response)
        except Exception as exc:
            logger.error("OpenAI chat error: %s", exc)
            raise

    async def vision_chat(
        self,
        messages: list[Message],
        image_data: str,
        image_mime: str,
        temperature: float = 0.0,
    ) -> LLMResponse:
        last_user = next(
            (m for m in reversed(messages) if m.role == "user"), None
        )
        prompt_text = last_user.content if last_user else "Describe this image."

        openai_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{image_data}"
                        },
                    },
                ],
            }
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature,
            )
            return self._parse_response(response)
        except Exception as exc:
            logger.error("OpenAI vision error: %s", exc)
            raise

    # ── internal ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(response) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message
        tool_calls = None

        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": args,
                    }
                )

        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )
