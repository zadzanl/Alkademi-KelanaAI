"""Small, provider-free primitives for phase-one authentication."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy.orm import Session as DbSession

from backend.models.session import Session
from backend.models.user import User

_password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$yHlvMGQ1Ktd65kOnzkBFCA$4D6rX6LEqqhyQP3Ob5Zd16v0+x9QqKUyroB5HyoWfr8"


def normalize_username(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def new_session(db: DbSession, user: User, ttl_seconds: int) -> tuple[Session, str]:
    raw_token = secrets.token_urlsafe(32)
    record = Session(
        user_id=user.id,
        token_digest=hashlib.sha256(raw_token.encode("ascii")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, raw_token


def session_for_token(db: DbSession, raw_token: str | None) -> Session | None:
    if not raw_token:
        return None
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    record = db.query(Session).filter(Session.token_digest == digest).first()
    if record is None or record.revoked_at is not None:
        return None
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return None
    return record