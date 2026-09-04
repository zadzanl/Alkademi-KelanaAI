"""ORM mapping for the `messages` table.

This module maps one conversational message turn within a conversation thread.
PostgreSQL runtime is verified in `tests/`.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.sql import func

from backend.database import Base


class Message(Base):
    """One conversational message turn (user or assistant) within a conversation."""

    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE", name="fk_messages_conversation_id"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
    )
