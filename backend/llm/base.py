"""
Base LLM provider abstraction.
All concrete providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class Message(BaseModel):
    """A single chat message."""
    role: str          # "user" | "assistant" | "system" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


class LLMResponse(BaseModel):
    """Structured response from the LLM."""
    content: str | None = None
    tool_calls: list[dict] | None = None   # list of {name, arguments}
    finish_reason: str | None = None
    raw: dict | None = None                # provider-specific raw response


class BaseLLMProvider(ABC):
    """Abstract base class that every LLM provider must implement."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a list of messages and return the model response."""

    @abstractmethod
    async def vision_chat(
        self,
        messages: list[Message],
        image_data: str,           # base-64 encoded image
        image_mime: str,           # e.g. "image/png"
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send messages that include an image and return the model response."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider."""
