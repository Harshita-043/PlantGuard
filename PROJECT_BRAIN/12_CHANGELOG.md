# PlantGuard AI Changelog

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
