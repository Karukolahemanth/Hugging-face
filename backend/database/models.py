"""
SQLAlchemy models for GAIA Agent persistence.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    """Stores chat conversation metadata."""
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    """Stores individual chat messages within a conversation."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    role = Column(String(32), nullable=False)     # user | assistant | tool
    content = Column(Text, nullable=False)
    message_metadata = Column(Text, default="{}")  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentTask(Base):
    """Records individual agent task runs."""
    __tablename__ = "agent_tasks"

    id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    task = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    result = Column(Text, default="{}")   # JSON-encoded final state summary
    execution_time_ms = Column(Float, default=0.0)
    num_steps = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UploadedFile(Base):
    """Tracks uploaded files."""
    __tablename__ = "uploaded_files"

    id = Column(String(64), primary_key=True)
    original_name = Column(String(256), nullable=False)
    stored_name = Column(String(256), nullable=False)
    mime_type = Column(String(128), nullable=False)
    size_bytes = Column(Integer, default=0)
    conversation_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
