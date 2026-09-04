"""Durable identity and processing state for keyed conversation messages."""

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Identity, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from backend.database import Base


class ConversationMessageRequest(Base):
    __tablename__ = "conversation_message_requests"

    id = Column(BigInteger, Identity(always=False), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", name="fk_conversation_message_requests_user_id"), nullable=False)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE", name="fk_conversation_message_requests_conversation_id"), nullable=False)
    key_digest = Column(String(64), nullable=False)
    content_digest = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False)
    user_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE", name="fk_conversation_message_requests_user_message_id"), nullable=False)
    assistant_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE", name="fk_conversation_message_requests_assistant_message_id"), nullable=True)
    claim_token = Column(String(64), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", "key_digest", name="uq_conversation_message_requests_owner_key"),
        UniqueConstraint("user_message_id", name="uq_conversation_message_requests_user_message"),
        UniqueConstraint("assistant_message_id", name="uq_conversation_message_requests_assistant_message"),
        CheckConstraint("status IN ('processing', 'completed')", name="ck_conversation_message_requests_status"),
        CheckConstraint("(status = 'processing' AND claim_token IS NOT NULL AND lease_expires_at IS NOT NULL AND assistant_message_id IS NULL AND completed_at IS NULL) OR (status = 'completed' AND assistant_message_id IS NOT NULL AND claim_token IS NULL AND lease_expires_at IS NULL AND completed_at IS NOT NULL)", name="ck_conversation_message_requests_state"),
        Index("ix_conversation_message_requests_conversation_id", "conversation_id"),
        Index("ix_conversation_message_requests_processing_lease", "lease_expires_at", postgresql_where=(status == "processing")),
    )