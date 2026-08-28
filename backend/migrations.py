"""Database migration and backfill utilities for scope-trips-to-users.

Provides idempotent schema migration, verification, legacy backfill, constraint
enforcement, and rollback functions for adding `user_id` to the `trips` table.
"""

from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.user import User


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
