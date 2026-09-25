# Verified Architecture

## Current application

- `frontend/` is a React + TypeScript + Vite single-page application. It has login/register, authenticated dashboard, plant list, image scan, scan lifecycle detail, and owner-scoped analysis history routes; other product areas remain shell placeholders. The dashboard and plant pages identify missing backend data instead of displaying invented records.
- `backend/app/main.py` exposes FastAPI health, scan, image analysis, and agentic routes. `/api/ping`, `/api/demo`, and `/` return static health/demo responses. `POST /api/v1/analyze/image` persists a validated private image and a pending owner-scoped Analysis record. Real inference and result generation remain unavailable.
- `backend/app/services/interfaces/` contains application service contracts. They are not a production ML integration.
- `backend/app/agent/` contains planning, validation, command, execution, and response contracts/components. It has no registered production capability handlers; the HTTP endpoint is disabled.
- `backend/app/llm/` contains provider abstractions. Provider adapters are not a verified, active product capability; mock provider selection is rejected.
- `backend/app/models/` and `backend/migrations/` define PostgreSQL users and analyses. Each Analysis has a required user foreign key, validated image metadata, status/timestamps, and a unique private object key; the live migration head is `0004_analysis_storage_reference`. Authenticated image creation uses the database and existing storage factory. Retrieval and history are owner-filtered server-side; lifecycle responses omit owner IDs, storage keys, and ML results. `backend/app/storage/` defines the provider-independent contract with local, Supabase Storage S3-compatible, and Cloudflare R2 S3-compatible adapters.

## Runtime and configuration

- Backend dependencies are listed in `backend/requirements.txt`; run the API from `backend/` with `uvicorn app.main:app --reload --port 8000`.
- Frontend dependencies are declared in `frontend/package.json`; the package declares pnpm as its package manager. Vite runs on port 8080.
- Backend CORS defaults to `http://localhost:8080` and can be configured through `BACKEND_CORS_ORIGINS`. Storage adapter selection is explicit through `OBJECT_STORAGE_PROVIDER` (`local`, `supabase`, or `r2`); an unset or incomplete selection fails when the factory is used, without switching providers. Local is selected in the environment example and does not require cloud credentials.
- Authentication uses Argon2id password hashes and short-lived JWT bearer tokens. Configure `JWT_SECRET_KEY` and `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`; registration, login, and `/api/v1/auth/me` use the database. The SPA sends the session token to authenticated scan, retrieval, and history endpoints.
- Image uploads are limited to 10 MiB and checked against both declared MIME type and decoded JPEG/PNG/WebP content in a generated temporary directory, which is removed after validation. Only validated bytes are written through the explicitly selected object-storage adapter. New records stay `pending`, with `result_available: false`; no inference is run and no diagnosis is fabricated.

## Verified boundaries

The root `ml/` directory contains model artifacts, but no application inference code loads or verifies those artifacts. Do not claim model integration or modify those artifacts in application work. Supabase Storage and R2 use their private S3-compatible APIs only; no public bucket, signed URL, or direct frontend storage access exists. The upload route uses whichever backend provider is selected by configuration; live cloud credentials/bucket connectivity have not been verified by this phase.

Future real ML inference, RAG, recommendations, plants, deletion/retention lifecycle, and production deployment remain unimplemented unless code and runtime evidence establish otherwise.
