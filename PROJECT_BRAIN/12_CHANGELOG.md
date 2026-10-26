# PlantGuard AI Changelog

## 2026-09-25 — Isolated ML runtime foundation (Phase 9)

- Added an isolated, pinned SAM2/CLIP runtime manifest targeting Python 3.12.10; ML packages remain out of the FastAPI backend environment.
- Repaired standalone SAM2 configuration path resolution, filled missing generator settings with documented upstream API defaults, added safe CPU fallback, and added a load-only SAM2 smoke command.
- Changed CLIP loading to require the bundled safetensors file with strict `ViT-B-32` state-dict matching; no registry-download fallback is used.
- Replaced client-filename temporary paths in the standalone image endpoint with generated temporary names and decoded JPEG/PNG/WebP validation capped at 10 MiB.
- Model load could not be tested on this host: Python 3.12, WSL, PyTorch, SAM2, OpenCLIP, and GPU tooling are unavailable. Checkpoint hashes remained unchanged.

## 2026-09-25 — Authenticated image persistence lifecycle

- Connected `POST /api/v1/analyze/image` to the configured existing object-storage provider after validating the uploaded image; the client filename is not used for temporary or object paths.
- Added a required private object reference to Analysis and migration `0004_analysis_storage_reference` (reversible, with no backfill); the live database is at this revision.
- Added owner-scoped pending analysis retrieval and history. The API returns lifecycle metadata only; ML results remain unavailable.
- Updated the scan, result, and history views to use the existing JWT session and show the pending/unavailable state without fabricated diagnosis data.
- Verification: full backend suite 113 passed, 1 skipped; frontend typecheck passed. Vitest could not start under this Windows environment (`spawn EPERM`).

## 2026-09-24 — Repository audit correction

The preceding phase summaries contain implementation claims that were not supported by the current source/runtime and are superseded by [11_AUDIT.md](11_AUDIT.md). Current verified changes:

- Removed fabricated analysis from active API paths; scan and image analysis now report unavailable until real inference exists, and video analysis is explicitly not implemented.
- Disabled agentic HTTP analysis pending real handlers; rejected mock provider selection in the application LLM factory.
- Tightened default CORS, removed unused database schema/module code and dependencies, fixed environment settings, and cleaned `.gitignore`.
- Repaired frontend syntax and type errors and replaced hardcoded sample plant/user/health/weather values with accurate empty/unavailable states.
- Removed eight unreferenced root-level phase/storage summary guides that contradicted the verified implementation.
- Updated architecture, frontend, API, agent, audit, and manual setup documentation to the verified checkout state.

The older entries below are historical claims from earlier phases, not proof that those features remain integrated. Use the current audit and architecture documents for status.

## [Unreleased]
### Added
- Added a PostgreSQL analysis metadata model, SQLAlchemy session configuration, and an initial reversible Alembic migration. No API persistence or seed data was added.
- A local PostgreSQL server/database and `DATABASE_URL` are required to apply the migration; see `MANUAL_SETUP.md`.
- Added bounded local temporary handling for image uploads: JPEG, PNG, and WebP are validated against their actual decoded format, with generated filenames and cleanup on every exit path. Analysis remains unavailable without real inference.
- Added a provider-independent object storage interface and a private local filesystem adapter. It stores generated or validated safe object keys, content, content type, and string metadata atomically. It is not integrated into application upload or persistence flows.
- Added a Cloudflare R2 production adapter behind the existing storage interface using boto3's S3-compatible API. Provider selection is explicit; R2 requires bucket, HTTPS endpoint, and backend-only credentials and never falls back to local storage. R2 keys use a fixed `plantguard/` namespace. The local adapter remains available.
- Added a Supabase Storage adapter behind the existing interface using its S3-compatible API. Provider selection is explicit, credentials are backend-only, keys use the fixed `plantguard/` namespace, and the adapter is not connected to API workflows. Local and R2 adapters remain available.
- Added a `users` table in a reversible Alembic migration and backend email/password registration, login, and authenticated identity endpoints. Passwords use Argon2id; login issues expiring JWT bearer tokens. No seed users or ownership checks were added.

### Changed
- Updated pinned backend runtime dependencies for Python 3.14, including Pillow, NumPy, Pydantic, and FastAPI.

### Verification
- Database metadata and live PostgreSQL connection tests passed (3).
- Initial Alembic migration applied successfully; current revision is `0001_initial_analysis` and the `analyses` table exists. Offline downgrade SQL was generated; destructive rollback was not run against the configured database.
- Focused upload tests passed (10) in the Python 3.14 environment after installing declared dependencies.
- Fixed the `app.schemas` package/module collision by moving the existing `HealthResponse` schema into `app/schemas/health.py` and exporting it from the package. `app.main` imports successfully.
- Database tests passed (3); upload tests passed (10); agent/LLM tests passed (13). Full backend suite: 32 passed, 1 skipped, 1 failed. The remaining failure is `test_analysis_health_endpoint` (expected 503, received 404), outside the schema import fix.
- Restored the analysis health route at `/api/v1/analyze/health`; it returns 503 with the existing explicit unavailable detail while real inference is not integrated. The API contract and existing test already described this behavior.
- Verified PostgreSQL read-only: service `postgresql-x64-18` is running, `public.analyses` exists, and the current Alembic revision is `0001_initial_analysis`. No database writes or migrations were performed.
- Re-ran checks: database tests 3 passed, upload tests 10 passed, agent/LLM tests 13 passed, analysis health endpoint test passed, and full backend suite 34 passed. Existing Pydantic, Starlette, and HTTP status deprecation warnings remain.
- Added focused object storage tests for generated and nested keys, traversal rejection, read/write/delete/exists behavior, binary and metadata preservation, write failures, and storage-root confinement.
- Focused local storage tests passed (22); full backend suite passed (56). The existing deprecation warnings remain.
- R2 adapter tests passed (19) using Botocore Stubber without real credentials. The full backend suite passed (75); existing Pydantic, Starlette, and HTTP status deprecation warnings remain. No live R2 bucket integration test was run.
- Added authentication with Argon2id password hashing, short-lived JWT bearer tokens, user registration/login/current-identity APIs, and a reversible `0002_users` migration. The migration chain head is `0002_users`; offline upgrade SQL generation passed and no live migration was applied. Authentication tests use isolated SQLite without seeded users.
- Authentication tests and database model tests passed (16); the opt-in PostgreSQL connectivity check was skipped because `TEST_DATABASE_URL` was unset. Full backend suite passed (107), with 1 opt-in database check skipped and 45 existing/new dependency deprecation warnings. `app.main` import passed.

- LLM Abstraction / Provider Layer (Prompt 5)
  - LLM service interface defining contract for LLM services
  - Provider adapter architecture for OpenAI, Anthropic, Groq, local (Ollama), and mock providers
  - LLM service factory for configuration-based provider instantiation
  - Configuration support through environment variables
  - Integration with Agentic Core for LLM-enhanced planning
  - Structured output generation with Pydantic schema validation
  - Comprehensive unit tests for all LLM components
- Updated documentation to reflect LLM abstraction layer

### Changed
- Updated AgentService to use LLM service for planning
- Updated OrchestratorComponent to include LLM service initialization
- Updated PlannerComponent to use LLM-enhanced planning with fallback to deterministic planning
- Updated core configuration to include LLM settings

### Fixed
- None

## [0.3.0] - 2026-09-24
### Added
- Agentic Core foundation with orchestrator, planner, validator, command builder, execution boundary, and result validator
- Agent service interface integrating with existing backend API
- New agentic API endpoint: POST /api/v1/analytic/agentic/image
- Deterministic validation layer preventing arbitrary code execution
- Safe execution boundary only invoking registered capability handlers
- Result validation ensuring operation results are trustworthy
- Zero frontend/backend contract changes required for agentic functionality
- True separation of concerns: agentic logic isolated in backend/app/agent/
- Extensible architecture allowing new capabilities via handler registration
- Deterministic planner generating structured plans from user requests
- Command builder converting validated plans to safe execution commands
- Execution boundary executing commands via registered handlers
- Result validator ensuring operation results are valid before use
- Orchestrator coordinating the complete workflow from request to response
- Comprehensive unit tests for all agentic components
- Updated documentation to reflect agentic core foundation

### Changed
- Updated architecture documentation to include agentic core layer
- Updated agent graph documentation to reflect completed agentic core foundation
- Updated technical decisions to reflect agentic core implementation

## [0.2.0] - 2026-09-16
### Added
- Service-oriented ML architecture with clearly defined interfaces for 7 ML stages
- Mock implementations for all ML services enabling full-stack development
- Environment-based configuration to switch between mock/real models (ML_MODE=mock/real)
- Complete backend rewrite from Express.js to FastAPI with proper routing, middleware, and error handling
- SQLAlchemy ORM models for PostgreSQL database (ready for migration)
- Comprehensive API endpoints for plant image and video analysis
- Dynamic leaf detection visualization in frontend (handles any number of leaves)
- Complete UI implementation including dashboard, scan page, results page, history, and settings
- Shared TypeScript interfaces between frontend and backend for type safety
- Plant analysis service orchestrator that chains all ML services together
- Proper separation of concerns: zero ML logic in API route handlers
- Zero frontend/backend contract changes required to switch from mock to real models
- Comprehensive unit tests for services and API endpoints
- Updated documentation to reflect service-oriented architecture

### Changed
- Backend framework from Express.js to FastAPI (as per 10_DECISIONS.md)
- ML integration approach from direct model imports to service-oriented architecture
- API structure from legacy endpoints to versioned API (/api/v1/)
- Project structure to isolate ML services in backend/app/services/
- Documentation to reflect current implementation state current implementation state

## [0.1.0] - 2026-09-09
### Added
- Project initialization with frontend (React/Vite) and ML model
- Basic backend API server with Express.js
- Plant disease classification model trained on PlantVillage dataset
- Initial PROJECT_BRAIN documentation files:
  - 00_MASTER.md
  - 01_ARCHITECTURE.md
  - 02_ML_GRAPH.md
  - 03_DATASETS.md
  - 04_MODEL_REGISTRY.md
  - 05_API_CONTRACTS.md
  - 06_RAG_GRAPH.md
  - 07_AGENT_GRAPH.md
  - 08_FRONTEND_GRAPH.md
  - 09_DEPENDENCIES.md
  - 10_DECISIONS.md
  - 11_AUDIT.md

### Changed
- N/A

### Fixed
- N/A
---
