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
└── frontend/
    └── .gitkeep                # Placeholder; no frontend yet
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

**Check**: connecting with the new role, e.g. `psql -U kelana_app -d kelanaai -c "select 1;"`, returns `1`.

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
```

A `DATABASE_URL` env variable is required. The application will not start without a value (`RuntimeError`).

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

Empty values count as absent. If neither provider is completely configured, trip creation still succeeds and `ai_recommendation` is `null` (graceful degradation). If OpenRouter is selected but fails at runtime, the app does **not** fall back to Bedrock for that trip — selection is configuration-time only.

> ⚠️ `.env` must not contain the typo `AWS_REGION=ap-shoutheast-2`. The correct region value is `ap-southeast-2`; the Bedrock key is region-scoped.

### 3a. Migrate the `trips` table (one-time, existing databases only)

`Base.metadata.create_all` creates tables but does **not** add columns to an existing table. If your `trips` table predates the AI column, run this idempotent statement once:

```sql
ALTER TABLE trips ADD COLUMN IF NOT EXISTS ai_recommendation TEXT;
```

Verify with `\d trips` (or an `information_schema.columns` query): `ai_recommendation` is nullable and has type `text`. The `IF NOT EXISTS` guard means the statement is safe to re-run.

### 4. Run the API

```bash
uvicorn backend.main:app --reload
```

Check <http://127.0.0.1:8000/docs>; `GET /health` returns `{"status":"OK"}`.

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

### List saved trips (ascending ID)

```bash
curl http://127.0.0.1:8000/api/v1/trips
```

```json
[
  {"id":1,...}
]
```

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

## Known Limitations

- PUT and DELETE are available for trip budgets, but there is no `updated_at` tracking.
- Schema changes require a manual `ALTER TABLE` (no migration framework yet); `create_all` is create-only.
- AI inference is synchronous with a 15-second provider timeout on `POST /api/v1/trips`; the call runs before the trip row is persisted. No retries, runtime failover, or streaming.
- The AI prompt (should) includes an injection-isolation instruction (via Openrouter's built-in filters).
- No frontend, authentication, or chatbot (the conversational assistant is a future phase). Markdown rendering in the frontend is deferred.

## Tests

Run all regressions from the repository root with the environment activated:

```bash
python -m unittest discover -s tests -v
```

Run only the API regressions:

```bash
python -m unittest discover -s tests -p "test_api.py" -v
```

## Release

- `v0.1.0` — Initial console-based Trip Summary Generator.
- `v0.2.0` — Holiday season classification.
- `v0.3.0` — FastAPI REST cut-over committed as `dfafa81` (untagged).
- `v0.4.0` — PostgreSQL persistence plus ordered reads.
- `v0.5.0` — Current working change: AI recommendation column (`ai_recommendation`) via OpenRouter/Bedrock.
