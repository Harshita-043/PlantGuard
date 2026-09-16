# PlantGuard AI Changelog

## [Unreleased]
### Added
- Initial project structure with frontend and ML components
- Basic Express.js backend with health check endpoints
- Trained EfficientNetV2-B0 model for plant disease classification (38 classes)
- Comprehensive UI component library using Radix UI and Tailwind CSS
- PROJECT_BRAIN documentation system for single source of truth

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

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
- Documentation to reflect current implementation state

### Fixed
- Missing API-ML integration
- Missing persistence layer (database)
- Missing core plant scanning functionality
- Tight coupling between application and ML models
- Hard-coded assumptions about number of leaves
- Lack of environment-based configuration for ML mode
- Inconsistent error handling and validation
- Missing dynamic leaf detection visualization

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

# How to Read This Changelog
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
Versions follow Semantic Versioning (MAJOR.MINOR.PATCH).

## Types of Changes
- **Added**: New features
- **Changed**: Modifications to existing functionality
- **Fixed**: Bug fixes
- **Removed**: Removed features
- **Security**: Security-related changes
- **Deprecated**: Deprecated features