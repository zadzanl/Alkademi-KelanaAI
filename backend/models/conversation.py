"""ORM mapping for the `conversations` table.

This module maps one conversational thread scoped to a user account.
PostgreSQL runtime is verified in `tests/`.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.sql import func

from backend.database import Base


class Conversation(Base):
    """One chat conversation thread owned by a user."""

    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_conversations_user_id"),
        nullable=False,
        index=True,
    )
    title = Column(String(256), nullable=False, default="New Conversation")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_conversations_user_id_id", "user_id", "id"),
    )
