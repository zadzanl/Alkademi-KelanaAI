# AGENTS.md — KelanaAI

## Project

*KelanaAI* is a travel planning application with an integrated AI assistant, built for users in Indonesia. The repository is in its earliest stage: the only implemented feature is a Python console-based **Trip Summary Generator** (`backend/main.py`). Keep scope focused on the current baseline; do not introduce mechanics, frameworks, or directories that lack a requirement.

## Product Vision (End Goal)

The end goal is a "just figure it out" travel planner: the user says **"where I would like to go"** and the app (including its AI agents) works out the rest with no hassle.

- **Input:** trip destination, trip time/duration, and budget (in **IDR**).
- **Output:** a rough travel style classification — `"backpack/budget"`, `"mediocre"`, or `"luxury"`.
- **Chatbot:** a ChatGPT-like conversational assistant for trip-related questions — a significant, first-class feature of the app, not an add-on.
- **AI inference:** Amazon Bedrock as the AI inference provider.
- **Hosting:** AWS infrastructure (exact services/degree **to be determined**).

This vision is the destination, **not** the current scope. Do not build toward it ahead of requirement — the Trip Summary Generator baseline must stand on its own first. Treat AWS Bedrock, AWS hosting, and the chatbot as future phases gated behind explicit requirements and OpenSpec changes.

## Efficiency Mode (Required)

Be a lazy senior engineer: efficient, but never careless. After understanding the request and tracing the affected flow, stop at the first option that works:

1. Does this actually need to be built? If no, do not build it (YAGNI: You Ain't Gonna Need It).
2. Is the user solving the right problem, or patching a symptom while the real bug laughs from two files over?
3. Is there already something in this codebase that does this? Because you'd be amazed how often there is. Check whether an existing repository pattern or helper exists. Use the standard library, platform, or an installed dependency. Do not install new dependencies without asking.
4. Do the user's ideas, strategies, or code account for blind spots, weak assumptions, and structural flaws?
5. Is this overengineered for what's actually needed? Write the smallest correct, readable change.
6. Is this request safe, boring, and exactly what a committee of middle managers would approve — and if so, is there a sharper version hiding underneath?

Prefer deletion, boring solutions, no new dependencies, no unrequested abstractions, and the fewest line changes possible. Fix bugs at their shared root cause after checking all callers. 

This never permits skipping retrieval, trust-boundary validation, data-loss prevention, security, accessibility, requested work, or the orchestration and verification workflow below. 

Leave one smallest runnable regression check for non-trivial logic; document a deliberate known ceiling with a file header comment and its upgrade path.

## Standard Working Method

1. Clarify the requested outcome and inspect the affected files before editing.
2. Check `openspec/changes/` for an active change affecting your area.
3. For non-trivial work, retrieve context first; keep exploration, planning, implementation, and review as bounded, non-overlapping steps. Confirm material changes to behaviour, scope, architecture, data, cost, or risk before implementing.
4. Use OpenSpec to propose, implement, and archive material changes (`openspec new change`, `openspec instructions <artifact>`, `openspec instructions apply`, `openspec archive`). Keep implementation small, reversible, and directly traceable to approved requirements.
5. Verify each change with focused checks, then broader relevant checks when practical. Report exactly what was and was not verified — no unverified positive claims.

## Architecture and Code Rules

- `backend/` holds the Python console application; `backend/main.py` is the entry point.
- `frontend/` is a placeholder (`.gitkeep`) — no frontend implementation yet.
- Python 3, **standard library only** — no third-party packages without explicit approval.
- Keep presentation logic in importable functions (`print_trip_summary(...)`) with a `main()` + `if __name__ == "__main__":` guard, so logic stays testable and later extraction is mechanical.
- Do not add a frontend framework, web server, database, packaging/CI, AI integration, or AWS deployment **yet** — those are Product Vision phases (see above) gated behind explicit requirements and their own OpenSpec changes.

## OpenSpec Notes

- The active change is `openspec/changes/trip-summary-generator/` with `proposal.md`, `design.md`, `specs/trip-summary/spec.md`, and `tasks.md` (7/9 tasks done; git commit/tag tasks remain).
- This project does **not** have an `openspec/worklog-template.md` or a worklog convention yet. If you start multi-session work, create a simple `worklog.md` in the change directory recording stopping point, next step, blockers, and last verification.
- `openspec/` is currently listed in `.gitignore`, so change artifacts are local-only unless that decision is revisited.

## Current State

| Area | Status |
| :--- | :--- |
| Project structure | ✅ `backend/`, `frontend/.gitkeep`, `README.md` created |
| Trip Summary Generator | ✅ Implemented and verified in `backend/main.py` |
| OpenSpec change | ⚠️ `trip-summary-generator` — 7/9 tasks complete; git commit + `v0.1.0` tag pending (user handling git) |
| Git release | ⬜ Feature commit and `v0.1.0` tag not yet pushed |
| Tests | ⬜ No automated tests; manual run + import smoke test done |
| Frontend | ⬜ Placeholder only |
| AI integration / chatbot | ⬜ Not started — future phase per Product Vision |
| AWS hosting | ⬜ Not started — services/degree TBD per Product Vision |

The project is at its first feature. Work right now is establishing the baseline and release hygiene. The AI assistant (hosted on AWS Bedrock), chatbot, and AWS hosting described in the Product Vision are explicit future phases, not current work.

## Project Vocabulary

- **KelanaAI**: the product — travel planning app with an integrated AI assistant, for users in Indonesia.
- **Trip Summary Generator**: the console feature that collects `destination`, `country`, `days` (int), `budget` (float), `currency`, and `travel_month`, then prints a formatted summary.
- **Travel style**: the end-goal rough classification of a trip — `"backpack/budget"`, `"mediocre"`, or `"luxury"` — derived from destination, time/duration, and IDR budget.
- **Amazon Bedrock**: the planned AI inference provider for the assistant/chatbot.
- **Chatbot**: the planned ChatGPT-like conversational assistant for trip questions — a first-class future feature.

### Before You Start Any Task

1. Read [`README.md`](./README.md) and skim `backend/main.py`.
2. Check `openspec/changes/` for any active change affecting your area.
3. If you touch OpenSpec artifacts, run `openspec validate` afterward.

## Quick References

- [README](./README.md)
- [Console app entry point](./backend/main.py)
- [Active change: trip-summary-generator](./openspec/changes/trip-summary-generator/)
- [OpenSpec configuration](./openspec/config.yaml)

*CRITICAL: Keep AGENTS.md updated as the project evolves. AGENTS.md is the first file any new agent or contributor should read.*
