"""Database migration and backfill utilities for scope-trips-to-users.

Provides idempotent schema migration, verification, legacy backfill, constraint
enforcement, and rollback functions for adding `user_id` to the `trips` table.
"""

from typing import Any
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from backend.models.user import User

_LEDGER_TABLE = "conversation_message_requests"
_LEDGER_COLUMNS = {
    "id": ("bigint", "NO"), "user_id": ("integer", "NO"), "conversation_id": ("bigint", "NO"),
    "key_digest": ("character varying", "NO"), "content_digest": ("character varying", "NO"), "status": ("character varying", "NO"),
    "user_message_id": ("bigint", "NO"), "assistant_message_id": ("bigint", "YES"), "claim_token": ("character varying", "YES"),
    "lease_expires_at": ("timestamp with time zone", "YES"), "created_at": ("timestamp with time zone", "NO"),
    "updated_at": ("timestamp with time zone", "NO"), "completed_at": ("timestamp with time zone", "YES"),
}


def _with_transaction(bind: Any, operation):
    """Engine owns its transaction; Connection and Session callers retain ownership.

    A Session is rolled back on failure so its PostgreSQL transaction is not
    left aborted and accidentally reused by its caller.
    """
    if isinstance(bind, Engine):
        with bind.begin() as conn:
            return operation(conn)
    if isinstance(bind, Session):
        try:
            result = operation(bind)
            bind.commit()
            return result
        except Exception:
            bind.rollback()
            raise
    if isinstance(bind, Connection):
        return operation(bind)
    raise TypeError("Expected a SQLAlchemy Engine, Connection, or Session.")


class _ExistingBind:
    def __init__(self, bind): self.bind = bind
    def __enter__(self): return self.bind
    def __exit__(self, *args): return False


def verify_conversation_message_requests_schema(bind: Any) -> dict[str, Any]:
    """Verify the ledger using read-only, schema-qualified PostgreSQL catalogs."""
    context = bind.connect() if isinstance(bind, Engine) else _ExistingBind(bind)
    with context as conn:
        if conn.execute(text("SELECT to_regclass('public.conversation_message_requests')")).scalar() is None:
            raise RuntimeError("conversation_message_requests table is missing")
        rows = conn.execute(text("""SELECT column_name, data_type, is_nullable,
            character_maximum_length, column_default, is_identity, identity_generation
            FROM information_schema.columns WHERE table_schema='public' AND table_name=:table
            ORDER BY ordinal_position"""), {"table": _LEDGER_TABLE}).fetchall()
        column_rows = rows
        actual = {r[0]: r for r in column_rows}
        if len(column_rows) != len(_LEDGER_COLUMNS) or {r[0]: (r[1], r[2]) for r in column_rows} != _LEDGER_COLUMNS:
            raise RuntimeError("Incompatible conversation_message_requests columns")
        for name, length in {"key_digest": 64, "content_digest": 64, "status": 16, "claim_token": 64}.items():
            if actual[name][3] != length:
                raise RuntimeError("Incompatible ledger column length")
        if actual["id"][4] is not None or tuple(actual["id"][5:7]) != ("YES", "BY DEFAULT"):
            raise RuntimeError("Ledger id must be BIGINT BY DEFAULT identity")
        for name in ("created_at", "updated_at"):
            default = actual[name][4] or ""
            if "now" not in default.lower() and "current_timestamp" not in default.lower():
                raise RuntimeError("Ledger timestamp default is missing")
        rows = conn.execute(text("""SELECT c.conname, c.contype, pg_get_constraintdef(c.oid, true)
            FROM pg_catalog.pg_constraint c JOIN pg_catalog.pg_class t ON t.oid=c.conrelid
            JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname='public' AND t.relname=:table"""), {"table": _LEDGER_TABLE}).fetchall()
        defs = {r[0]: (r[1], r[2]) for r in rows}
        norm = lambda value: " ".join(value.lower().split()).replace('"', '')
        if not any(v[0] == 'p' and norm(v[1]) == 'primary key (id)' for v in defs.values()):
            raise RuntimeError("Incompatible ledger primary key")
        expected = {
            "uq_conversation_message_requests_owner_key": ("u", "UNIQUE (user_id, conversation_id, key_digest)"),
            "uq_conversation_message_requests_user_message": ("u", "UNIQUE (user_message_id)"),
            "uq_conversation_message_requests_assistant_message": ("u", "UNIQUE (assistant_message_id)"),
            "ck_conversation_message_requests_status": ("c", "CHECK (status::text = ANY (ARRAY['processing'::character varying, 'completed'::character varying]::text[]))"),
            "ck_conversation_message_requests_state": ("c", "CHECK (status::text = 'processing'::text AND claim_token IS NOT NULL AND lease_expires_at IS NOT NULL AND assistant_message_id IS NULL AND completed_at IS NULL OR status::text = 'completed'::text AND assistant_message_id IS NOT NULL AND claim_token IS NULL AND lease_expires_at IS NULL AND completed_at IS NOT NULL)"),
        }
        if any(name not in defs or defs[name][0] != kind or norm(defs[name][1]) != norm(definition) for name, (kind, definition) in expected.items()):
            raise RuntimeError("Incompatible ledger constraints")
        fks = conn.execute(text("""SELECT c.conname, c.confrelid::regclass::text, c.confdeltype,
            pg_get_constraintdef(c.oid, true) FROM pg_catalog.pg_constraint c
            JOIN pg_catalog.pg_class t ON t.oid=c.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname='public' AND t.relname=:table AND c.contype='f'"""), {"table": _LEDGER_TABLE}).fetchall()
        targets = {"fk_conversation_message_requests_user_id": "users", "fk_conversation_message_requests_conversation_id": "conversations", "fk_conversation_message_requests_user_message_id": "messages", "fk_conversation_message_requests_assistant_message_id": "messages"}
        if len(fks) != 4 or any(r[0] not in targets or r[1] != targets[r[0]] or r[2] != 'c' or 'ON DELETE CASCADE' not in r[3] for r in fks):
            raise RuntimeError("Incompatible ledger foreign keys")
        indexes = conn.execute(text("""SELECT i.relname, pg_get_indexdef(i.oid), pg_get_expr(x.indpred, x.indrelid)
            FROM pg_catalog.pg_class t JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_catalog.pg_index x ON x.indrelid=t.oid JOIN pg_catalog.pg_class i ON i.oid=x.indexrelid
            WHERE n.nspname='public' AND t.relname=:table"""), {"table": _LEDGER_TABLE}).fetchall()
        idx = {r[0]: r for r in indexes}
        conversation = idx.get("ix_conversation_message_requests_conversation_id")
        lease = idx.get("ix_conversation_message_requests_processing_lease")
        if not conversation or '(conversation_id)' not in norm(conversation[1]) or not lease or '(lease_expires_at)' not in norm(lease[1]) or norm(lease[2] or '') != "((status)::text = 'processing'::text)":
            raise RuntimeError("Incompatible ledger indexes")
        return {"table": _LEDGER_TABLE, "columns": len(column_rows), "verified": True}


def migrate_conversation_message_requests_schema(bind: Any) -> dict[str, Any]:
    """Create the additive ledger atomically; existing drift fails closed."""
    def operation(conn):
        prerequisites = set(conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users','conversations','messages')")).scalars().all())
        if prerequisites != {"users", "conversations", "messages"}:
            raise RuntimeError("users, conversations, and messages must exist before ledger migration")
        if conn.execute(text("SELECT to_regclass('public.conversation_message_requests')")).scalar() is not None:
            verify_conversation_message_requests_schema(conn)
            return {"created": False, "verified": True}
        conn.execute(text("""CREATE TABLE public.conversation_message_requests (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, user_id INTEGER NOT NULL, conversation_id BIGINT NOT NULL,
            key_digest VARCHAR(64) NOT NULL, content_digest VARCHAR(64) NOT NULL, status VARCHAR(16) NOT NULL,
            user_message_id BIGINT NOT NULL, assistant_message_id BIGINT, claim_token VARCHAR(64), lease_expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), completed_at TIMESTAMPTZ,
            CONSTRAINT fk_conversation_message_requests_user_id FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE,
            CONSTRAINT fk_conversation_message_requests_conversation_id FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE,
            CONSTRAINT fk_conversation_message_requests_user_message_id FOREIGN KEY (user_message_id) REFERENCES public.messages(id) ON DELETE CASCADE,
            CONSTRAINT fk_conversation_message_requests_assistant_message_id FOREIGN KEY (assistant_message_id) REFERENCES public.messages(id) ON DELETE CASCADE,
            CONSTRAINT uq_conversation_message_requests_owner_key UNIQUE (user_id, conversation_id, key_digest),
            CONSTRAINT uq_conversation_message_requests_user_message UNIQUE (user_message_id), CONSTRAINT uq_conversation_message_requests_assistant_message UNIQUE (assistant_message_id),
            CONSTRAINT ck_conversation_message_requests_status CHECK (status IN ('processing','completed')),
            CONSTRAINT ck_conversation_message_requests_state CHECK ((status='processing' AND claim_token IS NOT NULL AND lease_expires_at IS NOT NULL AND assistant_message_id IS NULL AND completed_at IS NULL) OR (status='completed' AND assistant_message_id IS NOT NULL AND claim_token IS NULL AND lease_expires_at IS NULL AND completed_at IS NOT NULL))
        )"""))
        conn.execute(text("CREATE INDEX ix_conversation_message_requests_conversation_id ON public.conversation_message_requests (conversation_id)"))
        conn.execute(text("CREATE INDEX ix_conversation_message_requests_processing_lease ON public.conversation_message_requests (lease_expires_at) WHERE status = 'processing'"))
        return {"created": True, "verified": False}
    return _with_transaction(bind, operation)


def migrate_trips_schema(db: Session) -> None:
    """Idempotently add nullable user_id column, foreign key, and composite index to trips."""
    db.execute(text("""
        DO $$
        BEGIN
            -- 1. Add nullable user_id column if not exists
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'trips' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE trips ADD COLUMN user_id INTEGER;
            END IF;

            -- 2. Add foreign key constraint if not exists
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'trips'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'user_id'
            ) THEN
                ALTER TABLE trips 
                ADD CONSTRAINT fk_trips_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            END IF;

            -- 3. Add composite index on (user_id, id) if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'trips' AND indexname = 'ix_trips_user_id_id'
            ) THEN
                CREATE INDEX ix_trips_user_id_id ON trips(user_id, id);
            END IF;
        END $$;
    """))
    db.commit()


def verify_trips_ownership(db: Session) -> dict[str, Any]:
    """Inspect and report the ownership status of all rows in the trips table."""
    total = db.execute(text("SELECT COUNT(*) FROM trips")).scalar() or 0
    owned = db.execute(text("SELECT COUNT(*) FROM trips WHERE user_id IS NOT NULL")).scalar() or 0
    unowned_rows = db.execute(text("SELECT id FROM trips WHERE user_id IS NULL ORDER BY id ASC")).fetchall()
    unowned_ids = [row[0] for row in unowned_rows]

    return {
        "total": total,
        "owned": owned,
        "unowned": len(unowned_ids),
        "unowned_ids": unowned_ids,
    }


def backfill_legacy_trips(db: Session, target_user_id: int) -> int:
    """Assign all unowned trips (user_id IS NULL) to a specified existing user account.
    
    Raises ValueError if target_user_id does not exist in the users table.
    Returns the number of rows backfilled.
    """
    user_exists = db.query(User).filter(User.id == target_user_id).first()
    if not user_exists:
        raise ValueError(f"Target user with ID {target_user_id} does not exist.")

    result = db.execute(
        text("UPDATE trips SET user_id = :user_id WHERE user_id IS NULL"),
        {"user_id": target_user_id},
    )
    db.commit()
    return result.rowcount


def enforce_trips_user_id_non_null(db: Session) -> None:
    """Enforce NOT NULL on trips.user_id after verifying zero unowned rows exist.
    
    Raises RuntimeError if any unowned rows remain in the table.
    """
    stats = verify_trips_ownership(db)
    if stats["unowned"] > 0:
        raise RuntimeError(
            f"Cannot enforce NOT NULL: {stats['unowned']} unowned trips remain (IDs: {stats['unowned_ids']}). "
            "Please backfill unowned trips before enforcing constraint."
        )

    db.execute(text("ALTER TABLE trips ALTER COLUMN user_id SET NOT NULL;"))
    db.commit()


def rollback_trips_user_id_migration(db: Session) -> None:
    """Roll back trips user_id schema changes idempotently."""
    db.execute(text("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            -- 1. Drop NOT NULL constraint if present
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'trips' AND column_name = 'user_id' AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE trips ALTER COLUMN user_id DROP NOT NULL;
            END IF;

            -- 2. Drop composite index if exists
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'trips' AND indexname = 'ix_trips_user_id_id'
            ) THEN
                DROP INDEX ix_trips_user_id_id;
            END IF;

            -- 3. Drop all foreign key constraints on trips.user_id if any exist
            FOR r IN (
                SELECT tc.constraint_name 
                FROM information_schema.table_constraints tc 
                JOIN information_schema.key_column_usage kcu 
                  ON tc.constraint_name = kcu.constraint_name 
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'trips' 
                  AND tc.constraint_type = 'FOREIGN KEY' 
                  AND kcu.column_name = 'user_id'
            ) LOOP
                EXECUTE 'ALTER TABLE trips DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
            END LOOP;

            -- 4. Drop column user_id if exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'trips' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE trips DROP COLUMN user_id;
            END IF;
        END $$;
    """))
    db.commit()


def migrate_knowledge_documents_schema(bind: Any) -> None:
    """Idempotently create knowledge_documents table, constraints, and indexes.

    Accepts an Engine, Session, or Connection instance.
    """
    from sqlalchemy.engine import Connection, Engine

    ddl = text("""
        DO $$
        BEGIN
            -- 1. Create table if not exists
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                s3_key VARCHAR NOT NULL,
                original_filename VARCHAR NOT NULL,
                content_type VARCHAR NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256_hash VARCHAR NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
            );

            -- 2. Add foreign key constraint if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'knowledge_documents'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'user_id'
            ) THEN
                ALTER TABLE knowledge_documents 
                ADD CONSTRAINT fk_knowledge_documents_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            END IF;

            -- 3. Add unique constraint on s3_key if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                WHERE tc.table_name = 'knowledge_documents'
                  AND tc.constraint_type = 'UNIQUE'
                  AND tc.constraint_name = 'uq_knowledge_documents_s3_key'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'knowledge_documents' AND indexname = 'uq_knowledge_documents_s3_key'
            ) THEN
                BEGIN
                    ALTER TABLE knowledge_documents ADD CONSTRAINT uq_knowledge_documents_s3_key UNIQUE (s3_key);
                EXCEPTION
                    WHEN duplicate_table OR duplicate_object THEN
                        NULL;
                END;
            END IF;

            -- 4. Create indexes idempotently
            CREATE INDEX IF NOT EXISTS ix_knowledge_documents_user_id ON knowledge_documents(user_id);
            CREATE INDEX IF NOT EXISTS ix_knowledge_documents_s3_key ON knowledge_documents(s3_key);
            CREATE INDEX IF NOT EXISTS ix_knowledge_documents_sha256_hash ON knowledge_documents(sha256_hash);
            CREATE INDEX IF NOT EXISTS ix_knowledge_documents_user_id_id ON knowledge_documents(user_id, id);
        END $$;
    """)

    if isinstance(bind, Engine):
        with bind.begin() as conn:
            conn.execute(ddl)
    elif isinstance(bind, Session):
        bind.execute(ddl)
        bind.commit()
    elif isinstance(bind, Connection):
        bind.execute(ddl)
    else:
        with bind.connect() as conn:
            with conn.begin():
                conn.execute(ddl)

