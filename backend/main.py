"""KelanaAI FastAPI application.

This module owns the FastAPI API boundary. 
Durable trip persistence (POST, ordered list/detail reads, PUT, DELETE) 
and AI recommendation generation (`ai_recommendation`). 

A POST request flows through five layers before its JSON response is sent. 
FastAPI/Pydantic validation runs first, then the deterministic service functions 
calculate the derived values. Trip handler builds one complete `Trip` snapshot, 
the request-scoped session persists through `add`/`commit`/`refresh`.
`TripResponse.model_validate(record)` converts row into public response shape.

This module does not own engine construction, session binding, schema lifecycle, 
or migration policy; those live in `backend.database`, and `backend.models.trip`
owns the ORM mapping. Treat `openapi.json`/Swagger, the handler docstrings, 
and the `TripResponse` schema as public-facing response contract; 
treat the `#` comments and module/class docstrings as developer-facing.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import re
import json
import logging
import threading
import time
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models.session import Session as AuthSession
from backend.models.trip import Trip
from backend.models.user import User
from backend.services.auth_service import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    new_session,
    normalize_username,
    session_for_token,
    verify_password,
)
from backend.services.ai_service import (
    generate_rag_comparison,
    get_ai_recommendation,
    log_ai_provider_config,
)

_comparison_hits: dict[int, list[float]] = {}
_comparison_lock = threading.Lock()
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
    log_ai_provider_config()
    yield


app = FastAPI(lifespan=lifespan)

AUTH_COOKIE_NAME = os.getenv("AUTH_SESSION_COOKIE", "kelana_session")
AUTH_SESSION_TTL_SECONDS = int(os.getenv("AUTH_SESSION_TTL_SECONDS", "604800"))
if AUTH_SESSION_TTL_SECONDS <= 0:
    raise RuntimeError("AUTH_SESSION_TTL_SECONDS must be a positive integer.")
AUTH_COOKIE_SECURE = os.getenv("ENVIRONMENT", "development").lower() == "production"
GENERIC_AUTH_ERROR = "Invalid username or password."


@app.exception_handler(RequestValidationError)
async def auth_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Avoid echoing submitted passwords in auth validation responses."""
    if not request.url.path.startswith("/api/v1/auth/"):
        return JSONResponse(status_code=422, content=jsonable_encoder({"detail": exc.errors()}))
    detail = []
    for error in exc.errors():
        safe_error = {key: value for key, value in error.items() if key != "input"}
        detail.append(safe_error)
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": detail}))

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

    destination: str = Field(max_length=100)
    country: str = Field(max_length=100)
    days: int = Field(gt=0)
    budget: float
    currency: str = Field(max_length=10)
    travel_month: str = Field(max_length=20)


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
    fields, the six submitted inputs, the five service-derived values, and
    the nullable AI-generated `ai_recommendation` snapshot — fourteen fields
    in total. `from_attributes=True` allows `TripResponse.model_validate(...)`
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
    ai_recommendation: str | None


class TripListResponse(BaseModel):
    """One page of stored trip snapshots plus collection metadata."""

    items: list[TripResponse]
    total: int
    page: int
    page_size: int


class AuthCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def canonical_username(cls, value: str) -> str:
        value = normalize_username(value)
        if not re.fullmatch(r"[a-z0-9_]+", value):
            raise ValueError("Username may contain only letters, numbers, and underscores.")
        return value


class PublicUser(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_session = session_for_token(db, request.cookies.get(AUTH_COOKIE_NAME))
    if auth_session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.get(User, auth_session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        raw_token,
        max_age=AUTH_SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=AUTH_COOKIE_SECURE,
        path="/",
    )


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


@app.post("/api/v1/auth/register", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
def register(credentials: AuthCredentials, db: Session = Depends(get_db)) -> PublicUser:
    """Create a pseudonymous account without returning credential material."""
    if db.query(User).filter(User.username == credentials.username).first() is not None:
        raise HTTPException(status_code=409, detail="Username is already registered.")
    record = User(username=credentials.username, password_hash=hash_password(credentials.password))
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username is already registered.") from None
    db.refresh(record)
    return PublicUser.model_validate(record)


@app.post("/api/v1/auth/login", response_model=PublicUser)
def login(credentials: AuthCredentials, response: Response, db: Session = Depends(get_db)) -> PublicUser:
    """Authenticate with a generic failure response and issue an opaque cookie."""
    record = db.query(User).filter(User.username == credentials.username).first()
    password_hash = record.password_hash if record is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(password_hash, credentials.password)
    if record is None or not password_matches:
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    _session, raw_token = new_session(db, record, AUTH_SESSION_TTL_SECONDS)
    set_session_cookie(response, raw_token)
    return PublicUser.model_validate(record)


@app.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    """Revoke the presented session and clear the browser cookie."""
    auth_session = session_for_token(db, request.cookies.get(AUTH_COOKIE_NAME))
    if auth_session is not None:
        auth_session.revoked_at = datetime.now(timezone.utc)
        db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@app.get("/api/v1/auth/me", response_model=PublicUser)
def me(user: User = Depends(current_user)) -> PublicUser:
    return PublicUser.model_validate(user)


@app.post("/api/v1/trips", response_model=TripResponse)
def create_trip(
    trip: TripRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TripResponse:
    """Save an owner-scoped trip snapshot and return the full stored snapshot.

    Persists the deterministic trip snapshot computed from the validated
    request and returns the complete stored record, including the
    database-issued `id` and `created_at` values, stamping the authenticated
    user ID on the server.
    """
    # FastAPI invokes `get_db()` for this request and yields one SQLAlchemy
    # session that is closed automatically once the response is sent; the
    # route body should not call `db.close()` itself.
    category = get_trip_category(trip.budget)
    # Calculation-to-snapshot boundary: the unchanged service functions
    # above produce derived values; everything below builds the complete
    # `Trip` row that will be persisted.
    record = Trip(
        user_id=user.id,
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
    generation_started = time.perf_counter()
    record.ai_recommendation = get_ai_recommendation(
        destination=trip.destination,
        country=trip.country,
        days=trip.days,
        budget=trip.budget,
        currency=trip.currency,
        travel_month=trip.travel_month,
        category=category,
        recommended_places=record.recommended_places,
        recommended_transportation=record.recommended_transportation,
        travel_season=record.travel_season,
    )
    db.add(record)
    db.commit()
    # Refresh reloads database-issued values (notably `id` and `created_at`)
    # so they are part of the response before explicit conversion.
    db.refresh(record)
    rag_logging_enabled = (
        os.getenv("RAG_COMPARISON_LOGGING", "false").lower() == "true"
        and os.getenv("RAG_ENABLED", "true").lower() == "true"
    )
    if rag_logging_enabled:
        elapsed_ms = int((time.perf_counter() - generation_started) * 1000)
        metrics = {
            "event": "rag_inference",
            "trip_id": record.id,
            "provider": "openrouter" if os.getenv("OPENROUTER_MODEL") else "bedrock",
            "rag_enabled": True,
            "bedrock_ms": 0,
            "exa_ms": 0,
            "total_retrieval_ms": 0,
            "generation_ms": elapsed_ms,
            "total_ms": elapsed_ms,
            "kb_chunks_count": 0,
            "exa_highlights_count": 0,
            "top_chunk_score": 0.0,
            "top_exa_score": 0.0,
            "sources": [],
            "web_domains": [],
            "bedrock_fallback": False,
            "exa_fallback": False,
        }
        logging.getLogger("backend.services.ai_service").info(
            "RAG_METRICS:%s", json.dumps(metrics, separators=(",", ":"))
        )
    return TripResponse.model_validate(record)

@app.post("/api/v1/knowledge/compare")
def compare_knowledge(trip: TripRequest, user: User = Depends(current_user)) -> dict:
    if os.getenv("RAG_COMPARISON_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="RAG comparison endpoint is disabled in this environment.")
    now = time.time()
    with _comparison_lock:
        recent = [stamp for stamp in _comparison_hits.get(user.id, []) if now - stamp < 60]
        if len(recent) >= 5:
            raise HTTPException(
                status_code=429,
                detail="RAG comparison rate limit exceeded.",
            )
        recent.append(now)
        _comparison_hits[user.id] = recent
    return generate_rag_comparison(trip)


@app.get("/api/v1/trips", response_model=TripListResponse)
def list_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TripListResponse:
    """Return one newest-first page of persisted trip snapshots for the current user.

    Offset pagination becomes slower at very large offsets. If trip volume
    reaches that ceiling, replace it with keyset pagination (`id < cursor`).
    """
    total = db.query(Trip).filter(Trip.user_id == user.id).count()
    offset = (page - 1) * page_size
    rows = []
    if offset < total:
        rows = (
            db.query(Trip)
            .filter(Trip.user_id == user.id)
            .order_by(Trip.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
    items = [
        TripResponse.model_validate(row)
        for row in rows
    ]
    return TripListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@app.get("/api/v1/trips/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TripResponse:
    """Return one stored trip belonging to the current user, or 404."""
    row = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user.id).first()
    if row is None:
        # The exact envelope below matches the trip-persistence contract;
        # a non-integer `trip_id` path segment is rejected by FastAPI with
        # 422 before reaching this branch.
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripResponse.model_validate(row)


@app.put("/api/v1/trips/{trip_id}", response_model=TripResponse)
def update_trip_budget(
    trip_id: int,
    update: TripUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TripResponse:
    """Update an owned trip's budget and recalc derived fields."""
    row = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user.id).first()
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
def delete_trip(
    trip_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete an owned trip and return a 204 response."""
    row = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    db.delete(row)
    db.commit()
    return Response(status_code=204)
