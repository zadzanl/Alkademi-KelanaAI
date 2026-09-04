# KelanaAI

KelanaAI is a travel planning application with an integrated AI assistant, built for users in Indonesia.

## Project Structure

```text
kelana-ai/
├── backend/
│   ├── main.py                 # FastAPI app, schemas, and route handlers
│   ├── database.py             # engine/session lifecycle, init_db()
│   ├── models/
│   │   ├── __init__.py
│   │   └── trip.py             # Trip mapping (14-column schema)
│   ├── requirements.txt        # Exact API, persistence, and AI dependency pins
│   └── services/
│       ├── trip_service.py     # Deterministic trip rules
│       └── ai_service.py       # Provider-neutral AI recommendation (OpenRouter/Bedrock)
├── tests/
│   ├── test_api.py             # TestClient API regressions
│   ├── test_trip_service.py    # Service regressions
│   └── test_ai_service.py      # AI provider selection/parsing unit tests
└── frontend/                   # Next.js planner UI
  ├── src/app/actions.ts      # Server Action; FastAPI stays server-to-server
  └── scripts/focused-checks.ts
```

## Requirements

- Python 3 (3.10+ recommended for `datetime.fromisoformat`).
- FastAPI 0.141.1
- Uvicorn 0.52.3 with standard reload extras
- httpx 0.28.1 for FastAPI TestClient
- PostgreSQL 18+ (locally installed; see Setup).
- SQLAlchemy 2.0.52
- `psycopg[binary]` 3.3.4
- python-dotenv 1.2.3
- boto3 1.43.4 (Amazon Bedrock fallback provider)
- argon2-cffi 25.1.0 (Argon2id password hashing)

## Setup

Run all commands from the repository root.

### 1. Install PostgreSQL locally

Use the official EDB Windows installer. Check pgAdmin opens and can connect.

Create the database and a least-privileged login role in pgAdmin's Query Tool (or `psql`):

```sql
CREATE DATABASE kelanaai;
CREATE USER kelana_app WITH PASSWORD '<your-own-password>';
GRANT ALL PRIVILEGES ON DATABASE kelanaai TO kelana_app;
```

If your target PostgreSQL reports `permission denied for schema public` on first app startup, have the database owner grant schema access inside the target database (the role used above is just an example):

```sql
GRANT USAGE, CREATE ON SCHEMA public TO kelana_app;
```

Check: connecting with the new role, e.g. `psql -U kelana_app -d kelanaai -c "select 1;"`, returns `1`.

### 2. Create the local environment

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m pip check
```

### 3. Create a root `.env`

The `.env` file is gitignor-ed.

```text
DATABASE_URL=postgresql+psycopg://<user>:<password>@127.0.0.1:5432/kelanaai
ENVIRONMENT=development
AUTH_SESSION_COOKIE=kelana_session
AUTH_SESSION_TTL_SECONDS=604800
```

A `DATABASE_URL` env variable is required. The application will not start without a value (`RuntimeError`).

Sessions expire after seven days by default; set a different positive `AUTH_SESSION_TTL_SECONDS` for local testing. Set `ENVIRONMENT=production` to mark the session cookie Secure.

Auth intentionally collects only a normalized username and password hash, stores only session-token digests, and is nowhere near full GDPR compliance.

To enable AI recommendations, add the provider variables you want to use. The app selects a provider at configuration time in this order:

1. **OpenRouter** selected when both `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are. Defaults to a free (currently `Dots3-Note Preview`) .
2. **Bedrock**: selected when OpenRouter is not configured and both `AWS_REGION` and `MODEL_ID` are non-empty. Currently deafults to `Amazon/Nova-Lite-1.0`

```text
# OpenRouter (primary)
OPENROUTER_API_KEY=<your-key>
OPENROUTER_MODEL=<model-name>

# Bedrock (fallback)
AWS_REGION=ap-southeast-2
MODEL_ID=amazon.nova-lite-v1:0
# Bedrock credentials are resolved automatically by boto3 (IAM roles,
# AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN, or
# AWS_BEARER_TOKEN_BEDROCK). They are NOT passed as aws_session_token.
```

If neither provider is completely configured, trip creation still succeeds and `ai_recommendation` is `null` (graceful degradation).

### 3a. Migrate the `trips` table (one-time, existing databases only)

`Base.metadata.create_all` creates tables but does **not** add columns to an existing table. If your `trips` table predates the AI column, run this idempotent statement once:

```sql
ALTER TABLE trips ADD COLUMN IF NOT EXISTS ai_recommendation TEXT;
```

Verify with `\d trips` (or an `information_schema.columns` query): `ai_recommendation` is nullable and has type `text`. The `IF NOT EXISTS` guard means the statement is safe to re-run.

### 3b. Migrate the keyed conversation request ledger

`Base.metadata.create_all()` creates missing registered tables but does not upgrade existing tables. Back up an existing PostgreSQL database, then run the additive ledger migration directly without calling `init_db()` first:

```powershell
@'
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from backend.migrations import migrate_conversation_message_requests_schema, verify_conversation_message_requests_schema
load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
try:
  with engine.begin() as conn: print(migrate_conversation_message_requests_schema(conn))
  with engine.connect() as conn: print(verify_conversation_message_requests_schema(conn))
  with engine.begin() as conn: print(migrate_conversation_message_requests_schema(conn))
  with engine.connect() as conn: print(verify_conversation_message_requests_schema(conn))
finally:
  engine.dispose()
'@ | python -
```

The second migration must report `created: False` and both verification calls must report `verified: True`. Partial or incompatible tables fail closed; existing keyless messages are never backfilled. Prerequisites are existing `public.users`, `public.conversations`, and `public.messages` tables. The verifier checks the identity metadata, timestamp defaults, named constraint definitions, four cascading foreign keys, nullable assistant linkage, exact index columns, and partial `status = 'processing'` predicate. Completed rows are retained indefinitely and cascade with their user or conversation. The server-only `CHAT_IDEMPOTENCY_ENABLED` and public `NEXT_PUBLIC_CHAT_IDEMPOTENCY_ENABLED` flags both default to `false`; disable the server flag first during rollback, then the public flag. Do not drop the ledger after keyed traffic.

For a separate fresh-bootstrap smoke test, use an empty database containing the prerequisite tables, import `backend.main`, enter `TestClient(app)` (or call `init_db()`), and then run the same catalog verifier. This is separate evidence from the existing-schema migration path; `create_all()` creates registered missing tables but never upgrades partial tables.

### 4. Run the API

```bash
uvicorn backend.main:app --reload
```

Check <http://127.0.0.1:8000/docs>; `GET /health` returns `{"status":"OK"}`.

### 5. Run the frontend locally

In a second PowerShell window:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
# .env.local must contain: API_URL=http://127.0.0.1:8000
npm run dev
```

The browser UI is at <http://localhost:3000>. `API_URL` is server-only; do not rename it to `NEXT_PUBLIC_API_URL` or put credentials in it.

For concurrent development, keep `uvicorn backend.main:app --reload` running in the repository-root window and `npm run dev` running from `frontend/`. Verify the API first with `Invoke-RestMethod http://127.0.0.1:8000/health`, which must return `status: OK`.

If FastAPI is stopped, the planner keeps submitted values and shows a reachability error. Restart `uvicorn backend.main:app --reload`, confirm `/health`, then use **Try again**; no browser restart or data reset is required.

Focused frontend checks use only Node 24's built-in test runner and the pinned TypeScript toolchain:

```powershell
cd frontend
npm run check:focused
npm run lint
npm run build
```

The implemented interface uses Instrument Serif for display text and Source Sans 3 for body/interface text. Non-null AI recommendations are rendered as provider-agnostic Markdown with raw HTML disabled and link/image URL schemes filtered. The current bundled Borobudur hero image is local; the approved seven-addition static landmark index remains pending its per-file provenance and derivative gates.

`.agents/skills/impeccable/` and root `skills-lock.json` are intentionally local-only ignored tooling. This diverges from upstream tracking guidance so machine-specific agent skills and lock state are not product source; verify with `git check-ignore -v .agents/skills/impeccable/SKILL.md`.

## API Examples

### Welcome

```bash
curl http://127.0.0.1:8000/
```

```json
{"message":"Welcome to KelanaAI"}
```

### Health

```bash
curl http://127.0.0.1:8000/health
```

```json
{"status":"OK"}
```

### Create a trip example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/trips -H "Content-Type: application/json" -d '{"destination":"Japan","country":"Japan","days":5,"budget":1500,"currency":"USD","travel_month":"December"}'
```

```json
{"id":1,"destination":"Japan","country":"Japan","days":5,"budget":1500.0,"currency":"USD","travel_month":"December","daily_budget":300.0,"travel_season":"Peak Season","category":"Standard","recommended_places":["Tokyo Tower","Shibuya","Mount Fuji"],"recommended_transportation":"Train","created_at":"2026-08-20T11:00:00+00:00","ai_recommendation":"## Japan in 5 days\n\nA practical itinerary..."}
```

`ai_recommendation` can be NULL. When a provider is configured and returns text, it holds a Markdown narrative; when no provider is configured or the provider fails, it is `null`.

### List saved trips (newest first, paginated)

```bash
curl http://127.0.0.1:8000/api/v1/trips
```

```json
{"items":[{"id":1,...}],"total":1,"page":1,"page_size":10}
```

The optional `page` and `page_size` query parameters default to `1` and `10`; `page_size` is capped at `100`. Items are ordered by descending ID, and pages beyond the available results return an empty `items` array with the correct `total`.

### Retrieve one saved trip

```bash
curl http://127.0.0.1:8000/api/v1/trips/1
```

```json
{"id":1,...}
```

### Update trip budget

Only the `budget` field is mutable. Updating it recomputes `daily_budget`, `category`, `recommended_places`, and `recommended_transportation`. `created_at` is server-generated and strictly immutable; `ai_recommendation` is preserved exactly as stored at creation time (the AI provider is never invoked on a budget update).

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/trips/1 -H "Content-Type: application/json" -d '{"budget":700}'
```

```json
{"id":1,"destination":"Japan","country":"Japan","days":5,"budget":700.0,"currency":"USD","travel_month":"December","daily_budget":140.0,"travel_season":"Peak Season","category":"Backpacker","recommended_places":["Tokyo Tower","Shibuya","Mount Fuji"],"recommended_transportation":"Bus","created_at":"2026-08-20T11:00:00+00:00","ai_recommendation":"## Japan in 5 days\n\nA practical itinerary..."}
```

### Delete a trip

```bash
curl -i -X DELETE http://127.0.0.1:8000/api/v1/trips/1
```

HTTP 204 No Content with an empty body.

### Recommended places

```bash
curl http://127.0.0.1:8000/api/v1/recommendations
```

```json
["Tokyo Tower","Shibuya","Mount Fuji"]
```

### Transportations

```bash
curl http://127.0.0.1:8000/api/v1/transportations
```

```json
["Bus","Train","Flight"]
```

### Validation failure

Non-positive `days` are rejected with HTTP 422:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/trips -H "Content-Type: application/json" -d '{"destination":"Japan","country":"Japan","days":0,"budget":1500,"currency":"USD","travel_month":"December"}'
```

Oversized string inputs are also rejected with HTTP 422: `destination` (>100), `country` (>100), `currency` (>10), and `travel_month` (>20) characters.

## AI Recommendation Provider Checks

The AI service reads provider config from environment variables only; it never hard-codes a model.

### Logging and secrets

Provider errors are logged with `error_type=config_error` or `error_type=runtime_error`. Logs never contain the API key, credentials, prompt payload, or raw HTTP request. The values `OPENROUTER_API_KEY`, `AWS_BEARER_TOKEN_BEDROCK`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` are never emitted to any log.

## Manual Restart Smoketest

After `uvicorn` starts once and create `trips` table, you can verify:

1. Note the `id` and `created_at` of a successfully POSTed trip.
2. Stop and restart `uvicorn` with the same `.env`.
3. `GET /api/v1/trips/{id}` with the captured ID. The response is identical to the original, including `created_at`.

## Database Migration & Legacy Backfill (scope-trips-to-users)

The `trips` table now includes a non-null `user_id` foreign key referencing `users(id)` and a composite index on `(user_id, id)`.

Migration operations are provided in `backend/migrations.py`:

```python
from backend.database import SessionLocal
from backend.migrations import (
    migrate_trips_schema,
    verify_trips_ownership,
    backfill_legacy_trips,
    enforce_trips_user_id_non_null,
    rollback_trips_user_id_migration,
)

db = SessionLocal()

# 1. Add nullable user_id column, foreign key, and composite index
migrate_trips_schema(db)

# 2. Check ownership stats
stats = verify_trips_ownership(db)
print("Ownership status:", stats)

# 3. Backfill legacy unowned trips to designated first account (e.g. target_user_id=1)
if stats["unowned"] > 0:
    backfilled = backfill_legacy_trips(db, target_user_id=1)
    print(f"Backfilled {backfilled} legacy trips")

# 4. Enforce NOT NULL constraint after verifying zero unowned rows
enforce_trips_user_id_non_null(db)

db.close()
```

### Rollback Runbook

To roll back the `user_id` migration:

```python
from backend.database import SessionLocal
from backend.migrations import rollback_trips_user_id_migration

db = SessionLocal()
rollback_trips_user_id_migration(db)
db.close()
```

## Known Limitations

- PUT and DELETE are available for trip budgets, but there is no `updated_at` tracking.
- Schema changes require manual/runbook migrations via `backend/migrations.py` (no Alembic yet); `create_all` is create-only.
- AI inference is synchronous with a 15-second provider timeout on `POST /api/v1/trips`; the call runs before the trip row is persisted. No retries, runtime failover, or streaming.
- Authentication is phase-one prototype infrastructure (pseudonymous username/password, Argon2id, database session tokens). There is no rate limiting, password recovery, email verification, account deletion, or data export (not GDPR certified).
- All trip CRUD operations (`POST`, `GET`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`) require an active authenticated session cookie (`kelana_session`). Unauthenticated requests return HTTP 401.

## Tests

Run all regressions from the repository root with the environment activated:

```bash
python -m unittest discover -s tests -v
```

Run frontend focused checks and build from `frontend/`:

```bash
npm run check:focused
npm run lint
npm run build
```

## Release

- `v0.1.0` — Initial console-based Trip Summary Generator.
- `v0.2.0` — Holiday season classification.
- `v0.3.0` — FastAPI REST cut-over committed as `dfafa81` (untagged).
- `v0.4.0` — PostgreSQL persistence plus ordered reads.
- `v0.5.0` — AI recommendation column (`ai_recommendation`) via OpenRouter/Bedrock.
- `v0.6.0` — Phase-one User Authentication (`users` and `sessions` tables).
- `v0.7.0` — Owner-Scoped Trips (`scope-trips-to-users`: private user history, migration & backfill runbook, cookie forwarding).

