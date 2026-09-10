"""Idempotency record for the trip-to-chat refinement handoff."""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint

from backend.database import Base


class TripRefinementRequest(Base):
    __tablename__ = "trip_refinement_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    operation_id = Column(String(64), nullable=False)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    message_key = Column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "operation_id", name="uq_trip_refinement_owner_operation"),
    )