"""
Chat API endpoints — non-streaming and streaming.
"""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.agent import GAIAAgent
from backend.agent.memory import Memory
from backend.database.database import get_db
from backend.security.safety import validate_request
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    files: list[str] | None = None   # filenames of uploaded files


class ChatResponse(BaseModel):
    answer: str
    steps: list[dict]
    sources: list[dict]
    tool_calls: list[dict]
    conversation_id: str
    status: str


class ConversationListItem(BaseModel):
    id: str
    title: str
    created_at: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Submit a task to the agent and receive the complete response.
    Non-streaming — waits for full completion.
    """
    # Safety check
    safety = validate_request(request.message)
    if not safety.safe:
        raise HTTPException(status_code=400, detail=safety.reason)

    conversation_id = request.conversation_id or str(uuid.uuid4())
    logger.info("Chat request [conv=%s]: %s", conversation_id, request.message[:80])

    memory = Memory(db)
    await memory.save_conversation(conversation_id, title=request.message[:80])
    await memory.save_message(conversation_id, "user", request.message)

    try:
        agent = GAIAAgent()
        state = await agent.run(
            task=request.message,
            conversation_id=conversation_id,
            files=request.files,
        )
    except Exception as exc:
        logger.error("Agent run failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    answer = state.final_answer or "I was unable to complete this task."
    await memory.save_message(conversation_id, "assistant", answer)
    await memory.save_task(
        task_id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        task=request.message,
        status=state.status.value,
        result={
            "answer": answer,
            "steps": len(state.steps),
            "tool_calls": len(state.tool_calls),
        },
    )

    return ChatResponse(
        answer=answer,
        steps=[s.model_dump() for s in state.steps],
        sources=[s.model_dump() for s in state.sources],
        tool_calls=[tc.model_dump() for tc in state.tool_calls],
        conversation_id=conversation_id,
        status=state.status.value,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Submit a task and receive a streaming SSE response.
    Only safe high-level events are emitted.
    """
    safety = validate_request(request.message)
    if not safety.safe:
        raise HTTPException(status_code=400, detail=safety.reason)

    conversation_id = request.conversation_id or str(uuid.uuid4())
    logger.info("Stream request [conv=%s]: %s", conversation_id, request.message[:80])

    memory = Memory(db)
    await memory.save_conversation(conversation_id, title=request.message[:80])
    await memory.save_message(conversation_id, "user", request.message)

    async def generate() -> AsyncGenerator[bytes, None]:
        try:
            agent = GAIAAgent()
            async for event in agent.stream(
                task=request.message,
                conversation_id=conversation_id,
                files=request.files,
            ):
                # SSE format: "data: <json>\n\n"
                payload = json.dumps(event)
                yield f"data: {payload}\n\n".encode("utf-8")

            # Save final message
            yield b"data: {\"event\": \"done\"}\n\n"

        except Exception as exc:
            logger.error("Stream error: %s", exc)
            err = json.dumps({"event": "error", "data": {"error": str(exc)}})
            yield f"data: {err}\n\n".encode("utf-8")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversation history."""
    from backend.database.models import Conversation
    from sqlalchemy import select, desc

    result = await db.execute(
        select(Conversation).order_by(desc(Conversation.updated_at)).limit(50)
    )
    convs = result.scalars().all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str, db: AsyncSession = Depends(get_db)
):
    """Get all messages for a conversation."""
    memory = Memory(db)
    messages = await memory.get_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str, db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and its messages."""
    from backend.database.models import Conversation, ChatMessage
    from sqlalchemy import delete

    await db.execute(
        delete(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
    )
    await db.execute(
        delete(Conversation).where(Conversation.id == conversation_id)
    )
    await db.commit()
    return {"deleted": conversation_id}
