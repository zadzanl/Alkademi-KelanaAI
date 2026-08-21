"""KelanaAI FastAPI application.

Status: active | Phase: Documentation pass over implemented Phase 1 trip persistence (PostgreSQL-unverified) | Sprint: week-2 | Last modified: 2026-08-20
Agent notes: This module owns the FastAPI API boundary. Phase 1 of trip persistence (durable POST and ordered list/detail reads) is implemented in this file, but no PostgreSQL runtime has been verified in this session.
Insights: A POST request flows through five owned layers before its JSON response is sent. FastAPI/Pydantic validation runs first, then the unchanged deterministic service functions calculate the derived values, the handler builds one complete `Trip` snapshot, the request-scoped session persists it through `add`/`commit`/`refresh`, and `TripResponse.model_validate(record)` converts the refreshed ORM row into the public response shape.

This module does not own engine construction, session binding, schema lifecycle, or migration policy; those live in `backend.database`, and `backend.models.trip` owns the ORM mapping. Treat `openapi.json`/Swagger, the handler docstrings, and the `TripResponse` schema as the publicly visible response contract; treat the `#` comments and module/class docstrings around them as developer-facing.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models.trip import Trip
from backend.services.trip_service import (
    calculate_daily_budget,
    get_recommended_places,
    get_recommended_transportation,
    get_travel_season,
    get_trip_category,
)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run once before the first request: create the trips table if missing.

    FastAPI executes every statement before `yield` exactly once during
    application startup, then enters request handling. Statements after
    `yield` would run during shutdown, but this project has no shutdown
    step today. `init_db()` is the owner of the engine bind and table
    creation; see `backend.database` for the schema-creation ceiling.
    """
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Mirrors the transportation order in `backend.services.trip_service.RECOMMENDATIONS`
# (Backpacker -> Bus, Standard -> Train, Luxury -> Flight). This list is a
# static API-layer mirror and only changes when the service mapping changes.
TRANSPORTATIONS = ["Bus", "Train", "Flight"]


class TripRequest(BaseModel):
    """Submitted trip body, validated by FastAPI/Pydantic before the handler runs.

    Pydantic enforces the field types and the `days > 0` rule. A missing
    field, a non-coercible value, or `days <= 0` produces a 422 response
    that reaches the client before this module's handler bodies ever
    execute; the handler can therefore assume `trip` is already valid.
    """

    destination: str
    country: str
    days: int = Field(gt=0)
    budget: float
    currency: str
    travel_month: str


class TripUpdate(BaseModel):
    """Budget update body.

    Enforces `extra="forbid"` so any additional fields (e.g. `days`) are 
    rejected with 422.
    """

    model_config = ConfigDict(extra="forbid")

    budget: float


class TripResponse(BaseModel):
    """Stored trip snapshot returned by trip-resource routes.

    Includes the database-issued `id` and timezone-aware `created_at`
    fields alongside the six submitted inputs and the five service-derived
    values. `from_attributes=True` allows `TripResponse.model_validate(...)`
    to read ORM attributes directly; the handlers still call the explicit
    conversion so the response construction stays visible in the route.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    destination: str
    country: str
    days: int
    budget: float
    currency: str
    travel_month: str
    daily_budget: float
    travel_season: str
    category: str
    recommended_places: list[str]
    recommended_transportation: str
    created_at: datetime


@app.get("/")
def welcome() -> dict[str, str]:
    """Return the application welcome message."""
    return {"message": "Welcome to KelanaAI"}


@app.get("/health")
def health() -> dict[str, str]:
    """Return the application health status."""
    return {"status": "OK"}


@app.get("/api/v1/recommendations")
def list_recommendations() -> list[str]:
    """Return the service-backed ordered place recommendations."""
    # 1500 is a nominal budget used only to select the stable legacy
    # "Standard" category for this demonstration endpoint; it is not a
    # stored trip and not a new business rule.
    return get_recommended_places(get_trip_category(1500))


@app.get("/api/v1/transportations")
def list_transportations() -> list[str]:
    """Return the ordered transportation options."""
    return TRANSPORTATIONS


@app.post("/api/v1/trips", response_model=TripResponse)
def create_trip(
    trip: TripRequest, db: Session = Depends(get_db)
) -> TripResponse:
    """Save a trip snapshot and return the full stored snapshot.

    Persists the deterministic trip snapshot computed from the validated
    request and returns the complete stored record, including the
    database-issued `id` and `created_at` values.
    """
    # FastAPI invokes `get_db()` for this request and yields one SQLAlchemy
    # session that is closed automatically once the response is sent; the
    # route body should not call `db.close()` itself.
    category = get_trip_category(trip.budget)
    # Calculation-to-snapshot boundary: the unchanged service functions
    # above produce derived values; everything below builds the complete
    # `Trip` row that will be persisted.
    record = Trip(
        destination=trip.destination,
        country=trip.country,
        days=trip.days,
        budget=trip.budget,
        currency=trip.currency,
        travel_month=trip.travel_month,
        daily_budget=calculate_daily_budget(trip.budget, trip.days),
        travel_season=get_travel_season(trip.travel_month),
        category=category,
        recommended_places=get_recommended_places(category),
        recommended_transportation=get_recommended_transportation(category),
    )
    db.add(record)
    db.commit()
    # Refresh reloads database-issued values (notably `id` and `created_at`)
    # so they are part of the response before explicit conversion.
    db.refresh(record)
    return TripResponse.model_validate(record)


@app.get("/api/v1/trips", response_model=list[TripResponse])
def list_trips(db: Session = Depends(get_db)) -> list[TripResponse]:
    """Return every persisted trip as an ordered snapshot list."""
    # Ascending server-issued `id` yields deterministic oldest-first order
    # without imposing pagination or extra query filters.
    return [
        TripResponse.model_validate(row)
        for row in db.query(Trip).order_by(Trip.id).all()
    ]


@app.get("/api/v1/trips/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db)) -> TripResponse:
    """Return one stored trip, or 404 if no trip has that ID."""
    row = db.get(Trip, trip_id)
    if row is None:
        # The exact envelope below matches the trip-persistence contract;
        # a non-integer `trip_id` path segment is rejected by FastAPI with
        # 422 before reaching this branch.
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripResponse.model_validate(row)


@app.put("/api/v1/trips/{trip_id}", response_model=TripResponse)
def update_trip_budget(
    trip_id: int, update: TripUpdate, db: Session = Depends(get_db)
) -> TripResponse:
    """Update a trip's budget and recalc derived fields."""
    row = db.get(Trip, trip_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    row.budget = update.budget
    row.daily_budget = calculate_daily_budget(row.budget, row.days)
    new_category = get_trip_category(row.budget)
    row.category = new_category
    row.recommended_places = get_recommended_places(new_category)
    row.recommended_transportation = get_recommended_transportation(new_category)

    db.commit()
    db.refresh(row)
    return TripResponse.model_validate(row)


@app.delete("/api/v1/trips/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a trip and return a 204 response."""
    row = db.get(Trip, trip_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    db.delete(row)
    db.commit()
    return Response(status_code=204)
