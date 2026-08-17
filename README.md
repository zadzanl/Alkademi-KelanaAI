# KelanaAI

<!-- status: active | phase: REST API | sprint: week-1 | last_modified: 2026-08-18 | agent_notes: Replaces the console tutorial with the verified FastAPI workflow. | insights: Five API routes compose unchanged deterministic services; validation rejects non-positive days before division. -->

KelanaAI is a travel planning application with an integrated AI assistant, built for users in Indonesia. This repository currently provides a small FastAPI REST API with deterministic budget, season, place, and transportation recommendations.

## Project Structure

```text
kelana-ai/
├── backend/
│   ├── main.py                 # FastAPI app, schemas, and route handlers
│   ├── requirements.txt        # Exact API and test dependency pins
│   └── services/
│       └── trip_service.py     # Deterministic trip rules
├── tests/
│   ├── test_api.py             # TestClient API regressions
│   └── test_trip_service.py    # Service regressions
└── frontend/
    └── .gitkeep                # Placeholder; no frontend yet
```

## Requirements

- Python 3
- FastAPI 0.141.1
- Uvicorn 0.52.3 with standard reload extras
- httpx 0.28.1 for FastAPI TestClient

## Setup

Run all commands from the repository root.

Create the local environment:

```powershell
python -m venv backend/.venv
```

Activate it on Windows PowerShell:

```powershell
backend\.venv\Scripts\Activate.ps1
```

Or activate it on POSIX shells:

```bash
source backend/.venv/bin/activate
```

Install the pinned dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

## Run the API

Start Uvicorn from the repository root:

```bash
uvicorn backend.main:app --reload
```

Open the interactive Swagger UI at <http://127.0.0.1:8000/docs>.

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

### Create a trip

```bash
curl -X POST http://127.0.0.1:8000/api/v1/trips -H "Content-Type: application/json" -d '{"destination":"Japan","country":"Japan","days":5,"budget":1500,"currency":"USD","travel_month":"December"}'
```

```json
{"destination":"Japan","country":"Japan","days":5,"budget":1500.0,"currency":"USD","travel_month":"December","daily_budget":300.0,"travel_season":"Peak Season","category":"Standard","recommended_places":["Tokyo Tower","Shibuya","Mount Fuji"],"recommended_transportation":"Train"}
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

## Tests

Run all regressions from the repository root with the environment activated:

```bash
python -m unittest discover -s tests -v
```

Run only the API regressions:

```bash
python -m unittest discover -s tests -p "test_api.py" -v
```

## Known Limitations

- Travel-month classification is exact and case-sensitive: only `December` and `June` receive special seasons.
- Budget thresholds use the submitted numeric amount directly; currencies are not converted or normalized.
- Place recommendations are static and destination-independent.
- The transportation list is a static API-layer mirror of the current Backpacker, Standard, and Luxury service mappings.
- There is no persistence, authentication, frontend, AWS deployment, Bedrock integration, or chatbot yet.

## Release

- `v0.1.0` — Initial console-based Trip Summary Generator.
- Current working change — FastAPI REST cut-over and read-only recommendation lists.
