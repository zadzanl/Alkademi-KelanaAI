# KelanaAI Frontend

The implemented frontend is a pinned Next.js App Router client for the KelanaAI trip planner. It keeps FastAPI server-to-server behind a same-origin Server Action and does not change the backend contract.

## Local development

Start FastAPI from the repository root and verify its health:

```powershell
uvicorn backend.main:app --reload
Invoke-RestMethod http://127.0.0.1:8000/health
```

The health response must report `status: OK`. In a second PowerShell window:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
# Set API_URL=http://127.0.0.1:8000 in .env.local
npm run dev
```

Open <http://localhost:3000>. `API_URL` is server-only; do not rename it to `NEXT_PUBLIC_API_URL` or place credentials in it.

Use `/auth` to register or sign in. Next.js server actions explicitly copy the
FastAPI `Set-Cookie` session pair into an HttpOnly, SameSite=Lax cookie and
forward it on later server-side auth requests; the raw token never enters
action state or rendered markup. Trips and conversations are private: every
trip CRUD and chat endpoint requires the session cookie and is scoped to the
signed-in user.

If FastAPI stops, restart `uvicorn backend.main:app --reload`, recheck `/health`, and press **Try again**. Submitted values remain available.

## Verification

```powershell
npm run check:focused
npm run lint
npm run build
```

## Current interface contract

- Six controlled request fields are submitted through the Next.js Server Action; successful results preserve the backend's fourteen response fields.
- `/trips` reads the paginated list envelope (`items`, `total`, `page`, `page_size`), shows newest-first results in pages of 10 by default, and keeps the page number in `?page=N`; the API caps `page_size` at 100.
- `TRIP_REQUEST_TIMEOUT_MS = 120_000` is the inner server-side FastAPI fetch timeout. Its 120,000 ms ceiling is separate from the backend/provider's approximately 15-second ceiling.
- Non-null AI recommendations render as one provider-agnostic Markdown document. Raw HTML stays disabled and link/image URL schemes are filtered.
- Instrument Serif is the display face and Source Sans 3 is the body/interface face. The visual system uses warm paper, tinted ink, and restrained rules; note the token-name drift — `--terracotta` currently holds teal and `--indigo` holds slate, so treat utility names as labels, not colors. A dark theme with a static night-sky canvas is available via the header toggle.
- The home page runs an eight-landmark licensed carousel (Borobudur hero plus seven index landmarks, `src/app/landmarks.ts`; per-file provenance in `ATTRIBUTIONS.md`).
- `/chat` hosts the conversational travel assistant with multi-turn memory; `/trips` and `/trips/[id]` are private to the signed-in user.

No runtime image service, remote image configuration, destination matching, result imagery, image API field, backend change, or package change is part of the approved image scope.

## Status

The 2026-08-26 final-revision handoff completed; subsequent changes (trip history, authentication, pagination, ownership, RAG comparison UI, conversational assistant, shared header, dark mode) landed via the archived OpenSpec changes. See the root `AGENTS.md` and `openspec/changes/archive/` for current truth.

They were intentionally outside Phase 0's documentation-only edits. Task 5.2 owns verification of the Borobudur derivative; task 5.3 owns its manifest/ledger record; task 5.4 owns the bounded page integration while preserving the current global tokens and font setup. Before implementation proceeds, capture these incumbent files in the implementing change or otherwise establish explicit worktree ownership so later edits do not lose them.

## Deployment boundary

The current unauthenticated Server Action/API path is suitable for local integration only. Add deployment-grade authentication/authorization and rate limiting in a separate approved change before exposing it as an abuse boundary.
