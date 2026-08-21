"""Database connection and session ownership for KelanaAI.

Status: active | Phase: Documentation pass over implemented Phase 1 trip persistence (PostgreSQL-unverified) | Sprint: week-2 | Last modified: 2026-08-20
Agent notes: Owns environment loading, the SQLAlchemy `Base`, the lazily bound session factory, `init_db()`, and the request-scoped `get_db()` dependency. No PostgreSQL runtime has been verified in this session.
Insights: `Base.metadata.create_all()` is **create-only**: it creates the `trips` table when missing, but it does **not** structurally migrate an existing table. Any future schema change to `trips` therefore requires a separate, approved Alembic migration change first; Alembic is the documented upgrade path, not currently installed. URLs in error messages and examples intentionally use only a redacted placeholder shape, never an operator-supplied password or expanded URL. The redacted `postgresql+psycopg://<user>:<password>@127.0.0.1:5432/<db>` form is the only safe pattern in this module.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Read .env so DATABASE_URL is available. A pre-exported real environment
# value wins because `load_dotenv()` does not pass `override=True`. This is
# the AGENTS.md-permitted import-time side effect; no other module-level
# work runs here.
load_dotenv()

_BASE_URL = os.getenv("DATABASE_URL")
if not _BASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Create a .env file in the repo root with "
        "DATABASE_URL=postgresql+psycopg://<user>:<password>@127.0.0.1:5432/kelanaai"
    )

Base = declarative_base()

# Built without a bind. `init_db()` binds this factory to the engine once at
# FastAPI lifespan startup, and `get_db()` then issues one request-scoped
# session from this factory. A plain `from backend.database import
# SessionLocal` therefore does *not* force engine construction.
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)

_engine: Engine | None = None


def init_db() -> None:
    """Bind the engine and create the `trips` table if it is missing.

    Runs once when the FastAPI lifespan starts the app, before any request
    can reach a handler. `init_db()` is **not** retryable in-process: the
    `DATABASE_URL` was captured at module import, so editing `.env` and
    re-calling `init_db()` keeps using the original URL. Fix the underlying
    cause and restart `uvicorn` so the module re-imports. If startup fails,
    the raised `RuntimeError` is intentionally redacted so neither the
    raw URL nor the password echoes into startup logs; the message tells
    an operator which placeholder shape to verify, not which password to
    type.
    """
    global _engine
    # When this same factory is already bound to the same engine (e.g. a
    # repeated startup path), return without rebuilding the pool so module
    # state is preserved across the identity check.
    if _engine is not None and SessionLocal.kw.get("bind") is _engine:
        return
    try:
        candidate = create_engine(_BASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(bind=candidate)
        _engine = candidate
        SessionLocal.configure(bind=_engine)
    except Exception:
        raise RuntimeError(
            "Failed to initialize the database. Verify the redacted URL "
            "shape postgresql+psycopg://<user>:<password>@127.0.0.1:5432/<db> "
            "and that the configured role owns the target schema."
        ) from None


def get_db():
    """Yield one SQLAlchemy session per request and always close it.

    FastAPI calls this generator through `Depends(get_db)` for each
    request, so the yielded session lives for the full request/response
    lifecycle. The `finally` clause always closes the session to release
    pool resources, even if the handler raises. `init_db()` must have
    already bound `SessionLocal` for this dependency to return a usable
    session; the guard below fires only when `get_db()` is invoked before
    the lifespan has run.
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine is not initialized. init_db() must have run "
            "before get_db() — the FastAPI lifespan calls init_db() at "
            "application startup, and tests must enter TestClient(app) as "
            "a context manager so that lifespan executes."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
