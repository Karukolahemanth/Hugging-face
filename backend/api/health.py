"""
Health check API endpoint.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.utils.config import get_settings
from backend.tools.registry import tool_registry

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    provider: str
    tools: list[str]
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Returns the health status and configuration of the agent."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        provider=settings.llm_provider,
        tools=[t.name for t in tool_registry.list_tools()],
        version="1.0.0",
    )
