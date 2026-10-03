"""
Central configuration loader using python-dotenv + Pydantic.
All settings are loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings — loaded from .env or environment."""

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),   # search both locations
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    llm_provider: Literal["gemini", "openai"] = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    gemini_model: str = "gemini-3.5-flash"

    # ── Search ────────────────────────────────────────────────────────────
    search_provider: str = ""          # e.g. "tavily", "serper", "duckduckgo"
    search_api_key: str = ""

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./gaia.db"

    # ── Agent limits ──────────────────────────────────────────────────────
    max_agent_steps: int = 15

    # ── Files ─────────────────────────────────────────────────────────────
    max_file_size_mb: int = 20
    upload_dir: str = "uploads"

    # ── Python executor ───────────────────────────────────────────────────
    python_execution_timeout: int = 10

    # ── CORS ──────────────────────────────────────────────────────────────
    # Comma-separated allowed origins: "http://localhost:5173,http://localhost:3000"
    cors_origins_str: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_str.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
