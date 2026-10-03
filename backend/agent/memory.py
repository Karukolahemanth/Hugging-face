"""
Memory module — stores and retrieves conversation context using SQLite.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class Memory:
    """Simple session-scoped memory wrapper around the database session."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_conversation(
        self,
        conversation_id: str,
        title: str,
    ) -> None:
        """Create or update a conversation record."""
        from backend.database.models import Conversation
        from sqlalchemy import select

        existing = await self._db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = existing.scalar_one_or_none()

        if conv is None:
            conv = Conversation(
                id=conversation_id,
                title=title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._db.add(conv)
        else:
            conv.updated_at = datetime.utcnow()

        await self._db.commit()

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Persist a chat message."""
        import json
        from backend.database.models import ChatMessage

        msg = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=json.dumps(metadata or {}),
            created_at=datetime.utcnow(),
        )
        self._db.add(msg)
        await self._db.commit()

    async def get_messages(self, conversation_id: str, limit: int = 50) -> list[dict]:
        """Retrieve recent messages for a conversation."""
        from backend.database.models import ChatMessage
        from sqlalchemy import select, desc

        result = await self._db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()
        return [
            {"role": m.role, "content": m.content, "timestamp": m.created_at.isoformat()}
            for m in reversed(messages)
        ]

    async def save_task(
        self,
        task_id: str,
        conversation_id: str,
        task: str,
        status: str,
        result: dict | None = None,
    ) -> None:
        """Persist agent task results."""
        import json
        from backend.database.models import AgentTask

        existing = await self._db.get(AgentTask, task_id)
        if existing is None:
            record = AgentTask(
                id=task_id,
                conversation_id=conversation_id,
                task=task,
                status=status,
                result=json.dumps(result or {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self._db.add(record)
        else:
            existing.status = status
            existing.result = json.dumps(result or {})
            existing.updated_at = datetime.utcnow()

        await self._db.commit()
