# Manual setup

This file records only setup supported by the current repository. The app is a frontend and API shell; real plant analysis and API persistence, authentication, and object storage are not available. A PostgreSQL schema/migration foundation exists, but no API currently writes analysis rows.

## Required now — local development

1. Install Python 3.14 and Node.js. The pinned backend dependencies target Python 3.14. Use pnpm for the frontend, as declared by `frontend/package.json`.
2. From the repository root, create a backend environment file:

   ```powershell
   Copy-Item .env.example backend/.env
   ```

   The defaults are local-only. Keep secrets out of source control. `.env` files are ignored.
3. Install backend dependencies and run FastAPI:

   ```powershell
   Set-Location backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

   PostgreSQL is required to apply or use the database foundation. Install and start a local PostgreSQL server, then create the development database:

   ```powershell
   createdb -U postgres plantguard
   ```

   Edit `backend/.env` and set `DATABASE_URL` to match your local PostgreSQL username, password, host, port, and database. The example uses `postgresql+psycopg://postgres:postgres@localhost:5432/plantguard`; replace these development credentials as needed. Then apply the initial schema:

   ```powershell
   alembic upgrade head
   ```

   To roll back this initial migration in a disposable development database, run `alembic downgrade base`; this drops the `analyses` table and its data. Back up data before rolling back any database that matters. The database setup creates schema only and adds no seed records.

   Start FastAPI after configuring the database:

   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

4. In another terminal, configure the frontend API origin and start Vite:

   ```powershell
   Set-Location frontend
   Copy-Item .env.example .env
   pnpm install
   pnpm dev
   ```

   The Vite UI runs on port `8080`. The example points it to FastAPI at `http://localhost:8000`; backend CORS allows the local Vite origin by default.

## Current functionality and limits

- `GET http://localhost:8000/api/ping` returns the health ping.
- `GET http://localhost:8000/docs` exposes FastAPI's generated API documentation.
- Image scan and agentic scan endpoints return `503` until actual ML inference is integrated. Video analysis returns `501`.
- Plant records, scan history, accounts, and uploaded-media persistence are not implemented. The analysis schema is not yet used by API routes.
- PostgreSQL and Alembic are required to apply the analysis schema. Object storage, an LLM account, and an API key are not required by active API behavior.

## Optional checks

Run these from their respective directories:

```powershell
# frontend
pnpm run typecheck
pnpm test
pnpm build

# backend
python -m pytest -q
```

The backend test suite requires pytest and a compatible TestClient dependency. Model metadata tests do not require PostgreSQL. To check a live database connection, set `TEST_DATABASE_URL` to a disposable PostgreSQL database before running `python -m pytest -q app/tests/test_database_models.py`. Apply or roll back migrations only against a database intended for that operation.

## Verification checklist

- [ ] Copy `.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`.
- [ ] Install/start PostgreSQL, create `plantguard`, configure `DATABASE_URL`, and run `alembic upgrade head`.
- [ ] Start FastAPI and confirm `GET /api/ping` returns `{"message":"pong"}`.
- [ ] Start Vite on port `8080` and confirm the frontend renders.
- [ ] Run frontend typecheck, tests, and build.
- [ ] Run the isolated backend agent/LLM tests in a compatible Python environment.
- [ ] Confirm image/agentic analysis reports unavailable and does not return a fabricated result.
- [ ] Confirm the database model test passes; run the optional PostgreSQL connection test when `TEST_DATABASE_URL` is configured.
- [ ] Before production, integrate real inference, analysis persistence workflows, authorization, and private media storage.

## Required before production

- Integrate verified ML inference before enabling image/video analysis.
- Add and test persistence API workflows before enabling plant or scan history.
- Implement authentication, authorization, and per-user ownership checks before storing user data.
- Implement private object storage and secure upload/access checks before retaining media.
- Configure production CORS origins, secrets, provider credentials (only if an active provider is integrated), deployment, monitoring, and operational backups.

## Required when ML is integrated

The root `ml/` directory contains artifacts, but application compatibility and inference were not verified. When real ML code is provided, inspect its actual preprocessing, outputs, dependencies, and artifact requirements before documenting or configuring paths/devices. Do not alter model artifacts as part of this application setup.
