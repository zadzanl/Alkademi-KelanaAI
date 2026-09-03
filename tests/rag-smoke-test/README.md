# RAG smoke trace

This folder runs one itinerary request through the existing RAG retrieval path and writes two inspection artifacts:

- `outputs/prompt.md` — input, provider status, AWS Knowledge Base chunks, Exa results, and the exact pre-LLM prompt.
- `outputs/output.md` — provider/model metadata and the generated itinerary.

## Run

From the repository root:

```powershell
.\tests\rag-smoke-test\run_rag_smoke.ps1
```

Live providers are used whenever their configuration is present. A missing, empty, timed-out, or unsuccessful source uses a deterministic fixture unless strict mode is requested:

```powershell
.\tests\rag-smoke-test\run_rag_smoke.ps1 --strict-live
```

Strict mode exits non-zero instead of using mock retrieval or mock generation. The script loads the repository `.env`, but never writes secret values or authorization headers to the artifacts.

The fixed scenario is a five-day June trip to Bali on a 15,000,000 IDR budget. Delete `outputs/prompt.md` and `outputs/output.md` before a new run if you want to avoid confusing old and new traces; each file includes a UUID run ID and UTC timestamps.
