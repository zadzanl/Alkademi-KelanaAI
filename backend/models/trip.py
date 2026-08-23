"""ORM mapping for the `trips` table.

This module maps one trip snapshot to `trips` (14 columns, including the 
nullable `ai_recommendation` TEXT) and contains no engine or session code. 
PostgreSQL runtime is verified on `tests/` and tracked in AGENTS.md).
See `backend.database` for the create-only schema-creation ceiling 
and the documented manual `ALTER TABLE` migration path.
"""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from backend.database import Base


class Trip(Base):
    """One persisted trip snapshot.

    Stores six submitted inputs, five service-derived recommendation values,
    and two values issued by the database itself, plus the nullable AI snapshot.
    `id` and timezone-aware
    `created_at` are populated by the database, not by the API client; they
    appear on the persisted row only after commit/refresh, which is why
    `create_trip` reloads the row before building its response. See
    `backend.database` for the create-only schema-creation ceiling and the
    documented migration upgrade path.
    """

    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
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
