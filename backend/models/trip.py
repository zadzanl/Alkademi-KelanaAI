"""ORM mapping for the `trips` table.

This module maps one owner-scoped trip snapshot to `trips` (15 columns, including
user_id foreign key and nullable `ai_recommendation` TEXT) and contains no engine
or session code. PostgreSQL runtime is verified on `tests/` and tracked in AGENTS.md.
See `backend.database` and `backend.migrations` for schema migration and backfill.
"""

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from backend.database import Base


class Trip(Base):
    """One persisted trip snapshot scoped to a user account.

    Stores owner user_id, six submitted inputs, five service-derived recommendation
    values, database-issued `id` and `created_at`, plus nullable AI snapshot.
    """

    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", name="fk_trips_user_id"), nullable=False, index=True)
    destination = Column(String, nullable=False)
    country = Column(String, nullable=False)
    days = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    travel_month = Column(String, nullable=False)
    daily_budget = Column(Float, nullable=False)
    travel_season = Column(String, nullable=False)
    category = Column(String, nullable=False)
    recommended_places = Column(JSON, nullable=False)
    recommended_transportation = Column(String, nullable=False)
    ai_recommendation = Column(Text, nullable=True)
    # `server_default` means PostgreSQL stamps this timestamp using
    # `func.now()`; the application never supplies a value for this column.
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_trips_user_id_id", "user_id", "id"),
    )
