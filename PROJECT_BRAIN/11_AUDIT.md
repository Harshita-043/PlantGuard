# Repository Audit — 2026-09-24

This audit describes the checked-out repository after the stabilization changes in this worktree. The starting worktree already contained user edits in backend configuration/startup, ML service interfaces, agent contracts/API, and project documentation; those edits were preserved and reviewed while this audit continued.

## Verified status

| Component | Status | Evidence |
| --- | --- | --- |
| Frontend shell and routing | PARTIALLY IMPLEMENTED | Vite/React routes compile after repairing TSX and import errors; several routes remain placeholders. |
| Frontend API integration | PARTIALLY IMPLEMENTED | Image request client targets FastAPI. Scan request returns 503 because inference is unavailable. History and plants have no APIs. |
| FastAPI health/demo | IMPLEMENTED | `/`, `/api/ping`, and `/api/demo` are static endpoints. |
| Plant analysis API | NOT YET INTEGRATED | Image analysis is disabled with 503; video is disabled with 501. |
| Agentic core | PARTIALLY IMPLEMENTED | Component/contracts exist, but no production handlers; HTTP route is disabled. |
| LLM | PARTIALLY IMPLEMENTED | Provider adapters and an abstraction exist; no active product workflow, and mock selection is rejected. |
| ML inference | NOT YET INTEGRATED | App ML files were mock/demo implementations. Root model artifacts are not loaded by the application. |
| Database persistence | FOUNDATION IMPLEMENTED | One analysis metadata model, SQLAlchemy session configuration, and an initial reversible Alembic migration exist. API persistence is not wired. |
| Object storage | MISSING | No provider implementation or upload/access boundary found. |
| Authentication/authorization | MISSING | No login, session/token flow, protected API dependency, or ownership checks found. |
| RAG/recommendations/weather | MISSING | No application implementation verified. |

## Changes made

- Removed fabricated ML results from active scan and analysis service paths. Unsupported scan/analysis operations now return explicit unavailable responses.
- Added PostgreSQL/SQLAlchemy/Alembic foundation for analysis metadata only; no API writes or fabricated rows were added.
- Disabled the agentic endpoint pending a real capability implementation; rejected mock LLM provider selection.
- Restricted default CORS to the local Vite origin and removed the unused database schema/module scaffold and its dependencies.
- Added the missing `pydantic-settings` runtime requirement and removed duplicate/unused settings fields.
- Repaired frontend syntax, API imports/path, image overlay loading, and TypeScript issues. Replaced hardcoded dashboard/plant/account/history data with honest unavailable/empty states.
- Replaced stale environment examples and architecture/agent status documentation; added centralized manual setup instructions.
- Removed eight unreferenced root-level phase/storage summary guides that contradicted the verified implementation.

## Checks and limits

- Frontend `npm.cmd run typecheck`: passed.
- Frontend `npm.cmd test`: passed (1 file, 5 tests).
- Frontend `npm.cmd run build`: passed for client and server. Vite emitted config-loader compatibility warnings (`__dirname` and extensionless imports).
- Backend `python -m pytest -q -p no:cacheprovider app/agent/tests app/llm/tests` with `DEBUG=false`: passed (13 tests). Pydantic deprecation warnings remain.
- Database metadata and live PostgreSQL connection tests: passed (3).
- Alembic initial migration was applied to the configured PostgreSQL database; `alembic current` reports `0001_initial_analysis`, and the `analyses` table is present. Offline downgrade SQL was generated; destructive rollback was not run against the configured database.
- `HealthResponse` lives in `backend/app/schemas/health.py` and is exported by the `app.schemas` package; `app.main` imports successfully. The analysis health route is `/api/v1/analyze/health` and returns 503 while inference is unavailable. The prior 404 came from mounting the router at `/api/v1` while the health route omitted the `/analyze` segment. The full backend suite now passes (34 tests).
- Read-only live PostgreSQL verification succeeded: `postgresql-x64-18` is running, the database connection succeeds, `public.analyses` exists, and `alembic current` reports `0001_initial_analysis`. No rows were inserted and no migration was run during this verification. The earlier statement that the stopped `postgresql-x64-17` service prevented live checks was stale; service `postgresql-x64-18` is running.
- The upload tests passed in the Python 3.14 virtual environment after installing declared dependencies. No authenticated ownership, object storage, or live provider integration tests exist.

## Remaining verified blockers

Real ML integration, API persistence workflows, object storage, authentication/authorization, scan history, and production capability handlers are absent. The database schema/migration foundation does not enable persistence by itself. The frontend is consequently a shell and cannot deliver plant-health results.
