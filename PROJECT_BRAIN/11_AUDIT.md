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
| Object storage | LOCAL, SUPABASE, AND R2 ADAPTERS IMPLEMENTED, NOT INTEGRATED | `backend/app/storage/` defines a provider-independent interface with local, Supabase Storage S3-compatible, and Cloudflare R2 S3-compatible adapters. No current route/service uses them; uploads remain temporary. No public access or signed URL flow exists. |
| Authentication | BACKEND FOUNDATION IMPLEMENTED | Email/password registration and login use the `users` table, Argon2id hashes, and expiring JWT bearer tokens. `/api/v1/auth/me` resolves authenticated identity. No frontend login UI, refresh/revocation, or account recovery exists. |
| Authorization/ownership | NOT IMPLEMENTED | Only `/api/v1/auth/me` requires authentication. Analysis, scan, and storage operations are not protected and have no owner checks. |
| RAG/recommendations/weather | MISSING | No application implementation verified. |

## Changes made

- Removed fabricated ML results from active scan and analysis service paths. Unsupported scan/analysis operations now return explicit unavailable responses.
- Added PostgreSQL/SQLAlchemy/Alembic foundation for analysis metadata only; no API writes or fabricated rows were added.
- Added a provider-independent object storage contract and a private local development adapter with safe generated keys, metadata, and atomic writes. It is not connected to current upload, scan, analysis, or database flows.
- Added a Cloudflare R2 adapter behind the existing storage interface, with explicit provider configuration, a fixed object namespace, private bucket setup instructions, and Botocore Stubber tests. No API flow uses it.
- Added a Supabase Storage adapter behind the same interface, with explicit provider configuration, S3 endpoint/region/backend credentials, path-style requests, and Botocore Stubber tests. Local remains independent of cloud credentials; R2 remains supported but is not required. No API flow uses any adapter.
- Added email/password auth with Argon2id, expiring JWT bearer tokens, generic login failures, a current-user dependency/endpoint, and a reversible users-table migration. No accounts are seeded, and no unrelated API is protected in this phase.
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
- `HealthResponse` lives in `backend/app/schemas/health.py` and is exported by the `app.schemas` package; `app.main` imports successfully. The analysis health route is `/api/v1/analyze/health` and returns 503 while inference is unavailable. The prior 404 came from mounting the router at `/api/v1` while the health route omitted the `/analyze` segment. After adding local object storage tests, the full backend suite passes (56 tests).
- Read-only live PostgreSQL verification succeeded: `postgresql-x64-18` is running, the database connection succeeds, `public.analyses` exists, and `alembic current` reports `0001_initial_analysis`. No rows were inserted and no migration was run during this verification. The earlier statement that the stopped `postgresql-x64-17` service prevented live checks was stale; service `postgresql-x64-18` is running.
- The upload tests passed in the Python 3.14 virtual environment after installing declared dependencies. Focused tests cover the local storage adapter; no authenticated ownership or cloud-provider integration tests exist.
- Local adapter tests passed (22) and R2 SDK Stubber tests passed (19). Full backend suite passed (75); tests do not require live R2 credentials or a real bucket. No authenticated ownership or live cloud integration tests exist.
- Supabase adapter tests use Botocore Stubber and do not require credentials or a live project. Live Supabase connectivity and authenticated ownership are not verified.
- Authentication tests use an isolated SQLite database and cover registration, duplicate/invalid input, hashing, login failures, token expiry, current identity, protected endpoint rejection, and secret leakage. The PostgreSQL connectivity test is opt-in and skipped unless `TEST_DATABASE_URL` is set.
- Authentication migration chain has `0002_users` as the head; offline Alembic upgrade SQL generation succeeded. The new migration was not applied to a live database in this phase.
- Full backend suite: 107 passed, 1 skipped. The skip is the opt-in PostgreSQL connectivity test because `TEST_DATABASE_URL` was not set. `app.main` import and `git diff --check` passed.

## Remaining verified blockers

Real ML integration, analysis/scan persistence workflows, storage integration, frontend authentication, authorization/ownership checks, account recovery, scan history, and production capability handlers are absent. The database schema/migration foundation does not enable analysis persistence by itself. The frontend is consequently a shell and cannot deliver plant-health results.
