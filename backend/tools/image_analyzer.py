"""
Image analyzer tool.
Uses the configured vision-capable LLM to understand images.
"""

import base64
import os
from pathlib import Path

from backend.tools.base import BaseTool, ToolResult
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class ImageAnalyzerTool(BaseTool):
    """Analyzes images using a vision-capable LLM."""

    name = "analyze_image"
    description = (
        "Analyzes an uploaded image using a vision model. "
        "Can describe content, read text (OCR), interpret charts/diagrams, "
        "identify objects, and understand screenshots. "
        "Use the filename from the upload endpoint."
    )

    def __init__(self) -> None:
        self._provider = None   # Lazy-loaded to avoid startup failures

    def _get_provider(self):
        if self._provider is None:
            from backend.llm import get_llm_provider
            self._provider = get_llm_provider()
        return self._provider

    async def execute(self, arguments: dict) -> ToolResult:
        filename: str = arguments.get("filename", "").strip()
        prompt: str = arguments.get(
            "prompt",
            "Describe this image in detail, including all visible text, objects, charts, and information.",
        )

        if not filename:
            return ToolResult(success=False, error="No filename provided.")

        settings = get_settings()
        upload_dir = Path(settings.upload_dir)
        file_path = upload_dir / filename

        # Security: path traversal check
        try:
            file_path = file_path.resolve()
            file_path.relative_to(upload_dir.resolve())
        except ValueError:
            return ToolResult(
                success=False,
                error="Invalid filename — path traversal detected.",
            )

        if not file_path.exists():
            return ToolResult(
                success=False,
                error=f"Image file '{filename}' not found.",
            )

        suffix = file_path.suffix.lower()
        if suffix not in ALLOWED_MIME:
            return ToolResult(
                success=False,
                error=f"Unsupported image type: {suffix}. Allowed: {list(ALLOWED_MIME)}",
            )

        mime_type = ALLOWED_MIME[suffix]
        image_bytes = file_path.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        logger.info("ImageAnalyzer: analyzing %s (prompt: %s...)", filename, prompt[:60])

        try:
            from backend.llm.base import Message
            provider = self._get_provider()
            messages = [Message(role="user", content=prompt)]

            response = await provider.vision_chat(
                messages=messages,
                image_data=image_b64,
                image_mime=mime_type,
            )

            analysis = response.content or "No analysis returned."

            return ToolResult(
                success=True,
                result={"analysis": analysis, "filename": filename, "prompt": prompt},
            )

        except Exception as exc:
            logger.error("ImageAnalyzer error: %s", exc)
            return ToolResult(success=False, error=str(exc))

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename of the uploaded image.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": (
                            "What to analyze or extract from the image. "
                            "Examples: 'Describe the chart', 'Read all text in the image', "
                            "'List all products visible'."
                        ),
                        "default": "Describe this image in detail.",
                    },
                },
                "required": ["filename"],
            },
        }


# Singleton instance
image_analyzer_tool = ImageAnalyzerTool()
