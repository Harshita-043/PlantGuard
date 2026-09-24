# Verified Architecture

## Current application

- `frontend/` is a React + TypeScript + Vite single-page application. Its current routes are a dashboard, plant list, image scan, scan results, and shell placeholders. The dashboard and plant pages now identify missing backend data instead of displaying invented records.
- `backend/app/main.py` exposes FastAPI health, scan, image analysis, and agentic routes. `/api/ping`, `/api/demo`, and `/` return static health/demo responses. Scan and analysis operations return an unavailable response because real inference and persistence are not integrated.
- `backend/app/services/interfaces/` contains application service contracts. They are not a production ML integration.
- `backend/app/agent/` contains planning, validation, command, execution, and response contracts/components. It has no registered production capability handlers; the HTTP endpoint is disabled.
- `backend/app/llm/` contains provider abstractions. Provider adapters are not a verified, active product capability; mock provider selection is rejected.
- `backend/app/models/` and `backend/migrations/` define a PostgreSQL analysis metadata schema and initial Alembic migration. Analysis/scan APIs do not yet read or write this schema. No plant/user models, object storage, authentication, or ownership enforcement are implemented.

## Runtime and configuration

- Backend dependencies are listed in `backend/requirements.txt`; run the API from `backend/` with `uvicorn app.main:app --reload --port 8000`.
- Frontend dependencies are declared in `frontend/package.json`; the package declares pnpm as its package manager. Vite runs on port 8080.
- Backend CORS defaults to `http://localhost:8080` and can be configured through `BACKEND_CORS_ORIGINS`.
- Image uploads are size-limited, checked against supported MIME and decoded image formats, and held only in a generated file inside an OS temporary directory for the duration of validation/processing. The temporary directory is removed on all exits. No image is retained; analysis still returns unavailable until real inference is integrated.

## Verified boundaries

The root `ml/` directory contains model artifacts, but no application inference code loads or verifies those artifacts. Do not claim model integration or modify those artifacts in application work.

Future RAG, recommendations, weather, authentication, persistence, storage, and production deployment remain unimplemented unless code and runtime evidence establish otherwise.
