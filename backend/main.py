"""
GAIA Agent — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import health_router, chat_router, files_router
from backend.database.database import init_db
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()

    # Ensure required directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("workspace").mkdir(exist_ok=True)

    # Initialise database
    await init_db()

    # Import tools package to trigger auto-registration
    import backend.tools  # noqa: F401

    logger.info("GAIA Agent started — provider: %s", settings.llm_provider)
    yield
    logger.info("GAIA Agent shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="GAIA Agent API",
        description="A production-oriented general-purpose AI agent",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API routes ────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(files_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
