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
│   │   └── trip.py             # Trip mapping (13-column birth schema)
│   ├── requirements.txt        # Exact API and persistence dependency pins
│   └── services/
│       └── trip_service.py     # Deterministic trip rules
├── tests/
│   ├── test_api.py             # TestClient API regressions
│   └── test_trip_service.py    # Service regressions
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

A `DATABASE_URL` env variable is required. The application refuses to start without a value and prints a one-line `RuntimeError`.

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
{"id":1,"destination":"Japan","country":"Japan","days":5,"budget":1500.0,"currency":"USD","travel_month":"December","daily_budget":300.0,"travel_season":"Peak Season","category":"Standard","recommended_places":["Tokyo Tower","Shibuya","Mount Fuji"],"recommended_transportation":"Train","created_at":"2026-08-20T11:00:00+00:00"}
```

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

## Manual Restart Smoke

After `uvicorn` starts once and create `trips` table, you can verify:

1. Note the `id` and `created_at` of a successfully POSTed trip.
2. Stop and restart `uvicorn` with the same `.env`.
3. `GET /api/v1/trips/{id}` with the captured ID. The response is identical to the original, including `created_at`.

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
- `v0.4.0` — Current working change: PostgreSQL persistence plus ordered reads.
