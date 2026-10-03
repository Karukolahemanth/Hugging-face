"""
Tests for FastAPI endpoints.
Uses httpx AsyncClient with the ASGI test interface.
"""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """Create an async test client."""
    # Import here to avoid startup side effects at module load
    from backend.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "tools" in data
    assert "calculator" in data["tools"]


@pytest.mark.asyncio
async def test_chat_requires_message(client):
    resp = await client.post("/api/chat", json={})
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_conversations_list(client):
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_file_upload_invalid_type(client):
    from io import BytesIO
    resp = await client.post(
        "/api/files/upload",
        files={"file": ("test.exe", BytesIO(b"fake exe"), "application/octet-stream")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_file_upload_txt(client, tmp_path):
    from io import BytesIO
    content = b"Hello, this is a test file."
    resp = await client.post(
        "/api/files/upload",
        files={"file": ("test.txt", BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["original_name"] == "test.txt"
    assert data["size_bytes"] == len(content)
    assert data["filename"].endswith(".txt")
