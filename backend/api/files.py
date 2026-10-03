"""
File upload API endpoint.
Handles PDF, DOCX, XLSX, CSV, TXT, PNG, JPG, JPEG, WEBP uploads.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/files", tags=["files"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".csv", ".docx", ".xlsx",
    ".json", ".png", ".jpg", ".jpeg", ".webp",
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/json",
    "image/png",
    "image/jpeg",
    "image/webp",
}


class UploadResponse(BaseModel):
    filename: str           # stored filename (safe, UUID-based)
    original_name: str
    size_bytes: int
    mime_type: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file for the agent to process.
    Returns the stored filename to use in subsequent chat messages.
    """
    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    # ── Validate extension ──────────────────────────────────────────────
    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{suffix}' not supported. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # ── Read file with size limit ───────────────────────────────────────
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb} MB.",
        )

    # ── Validate MIME type ──────────────────────────────────────────────
    mime = file.content_type or "application/octet-stream"
    # Be lenient — some clients send generic MIME types
    if not any(mime.startswith(allowed.split("/")[0]) for allowed in ALLOWED_MIME_TYPES):
        logger.warning("Unexpected MIME type: %s", mime)

    # ── Save file with safe UUID-based name ────────────────────────────
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    upload_path = Path(settings.upload_dir) / safe_name
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)

    logger.info(
        "File uploaded: %s -> %s (%d bytes)", original_name, safe_name, len(content)
    )

    return UploadResponse(
        filename=safe_name,
        original_name=original_name,
        size_bytes=len(content),
        mime_type=mime,
        message="File uploaded successfully. Use the 'filename' in your chat message.",
    )


@router.get("/list")
async def list_uploads():
    """List all files in the uploads directory."""
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return {"files": []}

    files = []
    for f in upload_dir.iterdir():
        if f.is_file():
            files.append(
                {
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "suffix": f.suffix,
                }
            )
    return {"files": files}
