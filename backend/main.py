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
from math import ceil
import hashlib
import os
import re
import json
import logging
import secrets
import threading
import time
from typing import AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models.conversation import Conversation
from backend.models.conversation_message_request import ConversationMessageRequest
from backend.models.message import Message
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
    generate_chat_response,
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
CHAT_REQUEST_LEASE_SECONDS = 120
CHAT_IDEMPOTENCY_MARKER = "v1"
_CHAT_FALLBACK = ("I'm sorry, I am currently unable to generate a response. "
                  "Please check back in a moment or try rephrasing your question.")

def _key_error(code: str, message: str, status_code: int, headers: dict[str, str] | None = None) -> HTTPException:
    error_headers = {"X-KelanaAI-Chat-Idempotency": CHAT_IDEMPOTENCY_MARKER}
    if headers:
        error_headers.update(headers)
    return HTTPException(status_code=status_code, detail={"code": code, "message": message}, headers=error_headers)

def _parse_idempotency_key(value: str | None) -> tuple[str, str] | None:
    if value is None:
        return None
    if len(value) > 36 or value != value.strip() or not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value
    ):
        raise _key_error("idempotency_key_invalid", "Idempotency-Key must be a UUIDv4.", 422)
    try:
        parsed = UUID(value)
    except ValueError:
        raise _key_error("idempotency_key_invalid", "Idempotency-Key must be a UUIDv4.", 422) from None
    if parsed.version != 4:
        raise _key_error("idempotency_key_invalid", "Idempotency-Key must be a UUIDv4.", 422)
    canonical = str(parsed)
    return canonical, hashlib.sha256(canonical.encode("ascii")).hexdigest()

def _content_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def _integrity_error() -> HTTPException:
    return _key_error("chat_request_integrity_error", "The message request state is inconsistent. Refresh the conversation.", 500)

def _generation_error() -> HTTPException:
    return _key_error("chat_generation_unavailable", "The assistant could not complete this message. Retry with the same Idempotency-Key.", 503)

def _valid_user_message(message: Message | None, conversation_id: int, content: str) -> bool:
    return bool(message and message.conversation_id == conversation_id and message.role == "user" and message.content == content)

def _valid_history(history: list[Message], conversation_id: int) -> bool:
    return all(message.conversation_id == conversation_id and message.role in {"user", "assistant"} for message in history)

def _expire_claim(db: Session, ledger_id: int, claim_token: str) -> bool:
    """Best-effort release of only this claimant's recoverable lease."""
    try:
        changed = db.query(ConversationMessageRequest).filter(
            ConversationMessageRequest.id == ledger_id,
            ConversationMessageRequest.status == "processing",
            ConversationMessageRequest.claim_token == claim_token,
        ).update({"lease_expires_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
        db.commit()
        return changed == 1
    except Exception:
        db.rollback()
        return False


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


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=256)


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ConversationCreateResponse(BaseModel):
    conversation_id: int
    title: str
    created_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime


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


# =====================================================================
# Conversational Assistant Endpoints
# =====================================================================


@app.post(
    "/api/v1/conversations",
    response_model=ConversationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreate | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConversationCreateResponse:
    """Create a new chat conversation owned by the authenticated user."""
    title = (payload.title.strip() if payload and payload.title and payload.title.strip() else "New Conversation")
    conv = Conversation(user_id=user.id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationCreateResponse(
        conversation_id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
    )


@app.get("/api/v1/conversations", response_model=list[ConversationResponse])
def list_conversations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ConversationResponse]:
    """List all conversations owned by the authenticated user in reverse chronological order."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .all()
    )
    return [ConversationResponse.model_validate(c) for c in conversations]


@app.get("/api/v1/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    """Retrieve full chronological message history for an owned conversation."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    return [MessageResponse.model_validate(m) for m in messages]


@app.post(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_conversation_message(
    conversation_id: int,
    payload: MessageCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send a user message, assemble multi-turn context, generate AI reply, and persist both."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if idempotency_key is not None:
        response.headers["X-KelanaAI-Chat-Idempotency"] = CHAT_IDEMPOTENCY_MARKER
    parsed_key = _parse_idempotency_key(idempotency_key)
    if parsed_key is not None:
        _canonical_key, key_digest = parsed_key
        content = payload.content.strip()
        content_digest = _content_digest(content)
        now = datetime.now(timezone.utc)
        claim_token = secrets.token_hex(32)
        lease = now.timestamp() + CHAT_REQUEST_LEASE_SECONDS
        ledger = None
        try:
            user_msg = Message(conversation_id=conversation_id, role="user", content=content)
            db.add(user_msg)
            db.flush()
            if conv.title == "New Conversation" and content:
                conv.title = content[:40].strip()
            ledger = ConversationMessageRequest(
                user_id=user.id, conversation_id=conversation_id, key_digest=key_digest,
                content_digest=content_digest, status="processing", user_message_id=user_msg.id,
                claim_token=claim_token, lease_expires_at=datetime.fromtimestamp(lease, timezone.utc),
            )
            db.add(ledger)
            db.commit()
            db.refresh(user_msg)
        except IntegrityError:
            db.rollback()
            try:
                ledger = db.query(ConversationMessageRequest).filter(
                    ConversationMessageRequest.user_id == user.id,
                    ConversationMessageRequest.conversation_id == conversation_id,
                    ConversationMessageRequest.key_digest == key_digest,
                ).first()
                if ledger is None:
                    raise _integrity_error()
                if ledger.user_id != user.id or ledger.conversation_id != conversation_id:
                    raise _integrity_error()
                if ledger.content_digest != content_digest:
                    raise _key_error("idempotency_key_conflict", "This Idempotency-Key was already used for different message content.", 409)
                if ledger.status == "completed":
                    assistant = db.get(Message, ledger.assistant_message_id)
                    linked = db.get(Message, ledger.user_message_id)
                    if not _valid_user_message(linked, conversation_id, content) or not assistant or assistant.conversation_id != conversation_id or assistant.role != "assistant":
                        raise _integrity_error()
                    response.status_code = 200
                    return MessageResponse.model_validate(assistant)
                if ledger.status != "processing" or not ledger.claim_token or not ledger.lease_expires_at:
                    raise _integrity_error()
                if ledger.lease_expires_at > now:
                    response.headers["Retry-After"] = str(max(1, min(CHAT_REQUEST_LEASE_SECONDS, ceil((ledger.lease_expires_at - now).total_seconds()))))
                    raise _key_error("idempotency_key_in_progress", "A message with this Idempotency-Key is still being processed. Retry with the same key.", 409, {"Retry-After": response.headers["Retry-After"]})
                old_token = ledger.claim_token
                new_token = secrets.token_hex(32)
                recovery_lease = datetime.now(timezone.utc).timestamp() + CHAT_REQUEST_LEASE_SECONDS
                changed = db.query(ConversationMessageRequest).filter(
                    ConversationMessageRequest.id == ledger.id,
                    ConversationMessageRequest.status == "processing",
                    ConversationMessageRequest.claim_token == old_token,
                    ConversationMessageRequest.lease_expires_at <= now,
                ).update({"claim_token": new_token, "lease_expires_at": datetime.fromtimestamp(recovery_lease, timezone.utc), "updated_at": now}, synchronize_session=False)
                if changed != 1:
                    db.rollback()
                    current = db.query(ConversationMessageRequest).filter(ConversationMessageRequest.id == ledger.id).first()
                    if current is None or current.status not in {"processing", "completed"}:
                        raise _integrity_error()
                    if current.status == "completed":
                        assistant = db.get(Message, current.assistant_message_id)
                        linked = db.get(Message, current.user_message_id)
                        if not _valid_user_message(linked, conversation_id, content) or not assistant or assistant.conversation_id != conversation_id or assistant.role != "assistant":
                            raise _integrity_error()
                        response.status_code = 200
                        return MessageResponse.model_validate(assistant)
                    response.headers["Retry-After"] = str(max(1, min(CHAT_REQUEST_LEASE_SECONDS, ceil((current.lease_expires_at - datetime.now(timezone.utc)).total_seconds()))))
                    raise _key_error("idempotency_key_in_progress", "A message with this Idempotency-Key is still being processed. Retry with the same key.", 409, {"Retry-After": response.headers["Retry-After"]})
                db.commit()
                claim_token = new_token
                user_msg = db.get(Message, ledger.user_message_id)
                if not _valid_user_message(user_msg, conversation_id, content):
                    raise _integrity_error()
            except HTTPException:
                db.rollback()
                raise
            except Exception:
                db.rollback()
                raise _generation_error()
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise _generation_error()

        try:
            history = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc(), Message.id.asc()).all()
            if not _valid_history(history, conversation_id) or not _valid_user_message(user_msg, conversation_id, content):
                raise _integrity_error()
            message_dicts = [{"role": m.role, "content": m.content} for m in history]
            db.rollback()
            ai_reply_text = generate_chat_response(message_dicts) or _CHAT_FALLBACK
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            _expire_claim(db, ledger.id, claim_token)
            raise _generation_error()
        try:
            assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=ai_reply_text)
            db.add(assistant_msg)
            db.flush()
            changed = db.query(ConversationMessageRequest).filter(ConversationMessageRequest.id == ledger.id, ConversationMessageRequest.status == "processing", ConversationMessageRequest.claim_token == claim_token).update({"status": "completed", "assistant_message_id": assistant_msg.id, "claim_token": None, "lease_expires_at": None, "completed_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
            if changed != 1:
                db.rollback()
                raise _integrity_error()
            db.commit()
            db.refresh(assistant_msg)
            return MessageResponse.model_validate(assistant_msg)
        except HTTPException:
            _expire_claim(db, ledger.id, claim_token)
            raise
        except Exception:
            db.rollback()
            _expire_claim(db, ledger.id, claim_token)
            raise _generation_error()

    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=payload.content.strip(),
    )
    db.add(user_msg)

    # Auto-title conversation if it still has the default title
    if conv.title == "New Conversation":
        snippet = payload.content.strip()[:40].strip()
        if snippet:
            conv.title = snippet

    db.commit()
    db.refresh(user_msg)

    # Load prior conversation history up to sliding-window context
    prior_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    message_dicts = [{"role": m.role, "content": m.content} for m in prior_messages]

    ai_reply_text = generate_chat_response(message_dicts)
    if not ai_reply_text:
        ai_reply_text = _CHAT_FALLBACK

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=ai_reply_text,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return MessageResponse.model_validate(assistant_msg)


@app.patch("/api/v1/conversations/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Rename a conversation thread owned by the authenticated user."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.title = payload.title.strip()
    db.commit()
    db.refresh(conv)
    return ConversationResponse.model_validate(conv)

