# LLM package
from backend.llm.base import BaseLLMProvider, Message, LLMResponse
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def get_llm_provider() -> BaseLLMProvider:
    """Factory — returns the configured LLM provider instance."""
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name == "gemini":
        from backend.llm.gemini import GeminiProvider
        return GeminiProvider()
    elif provider_name == "openai":
        from backend.llm.openai_compatible import OpenAIProvider
        return OpenAIProvider()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            "Supported values: 'gemini', 'openai'."
        )


__all__ = ["BaseLLMProvider", "Message", "LLMResponse", "get_llm_provider"]
