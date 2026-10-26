# Manual setup

This file records only setup supported by the current repository. The app is a frontend and API shell; backend email/password authentication is available, but frontend auth, authorization/ownership, real plant analysis, API analysis persistence, and upload-to-storage integration are not. Local, Supabase Storage, and Cloudflare R2 adapters can be selected through the storage factory, but current API routes do not call them. PostgreSQL stores the initial analysis schema and authentication users.

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

   `alembic upgrade head` applies the analysis and user-table migrations; no seed users are created. To roll back only the user-table migration in a disposable development database, run `alembic downgrade 0001_initial_analysis`; this removes all account records. `alembic downgrade base` also removes the analyses table and its data. Never downgrade a database with data you need.

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
- Registration, login, and authenticated identity lookup are implemented at `/api/v1/auth/register`, `/api/v1/auth/login`, and `/api/v1/auth/me`. The SPA has no login UI/token handling. Plant records, scan history, account recovery/email verification, authorization/ownership, and uploaded-media persistence are not implemented. The analysis schema is not yet used by API routes.
- PostgreSQL and Alembic are required for account registration/login and to apply the analysis schema. Set `JWT_SECRET_KEY` before using login; cloud storage credentials, an LLM account, and an LLM API key are not required for local development.

## Configure backend authentication

1. In `backend/.env`, set `JWT_SECRET_KEY` to a unique random secret. Generate one from `backend/` with:

   ```powershell
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Keep the generated value only in `backend/.env` or the deployment secret store. Do not commit it or send it in chat. `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` defaults to `30` and can be adjusted up to 1440 minutes.
2. Install the current backend requirements and apply migrations from `backend/`:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   alembic upgrade head
   ```

   The new migration creates the `users` table; it inserts no accounts. Ensure `DATABASE_URL` points at the intended PostgreSQL database.
3. Registration accepts an email and a 12–128 character password. Login returns an access token. Send it as `Authorization: Bearer <token>` to `GET /api/v1/auth/me`. The client must discard the token on logout and after expiry; this backend does not issue refresh tokens or provide server-side token revocation.

The auth routes are backend-only at this stage; the current frontend has no login/register form or secure token handling. The signing key must contain at least 32 bytes; login and authenticated identity return `503` when it is absent or too short.

## Storage configuration

### Local development

Use the default `OBJECT_STORAGE_PROVIDER=local`. Local storage requires no Supabase or R2 account or credentials. Its root defaults to `.local-storage` under the backend working directory and is ignored by Git.

### Supabase production storage adapter

Supabase Storage is not used by the current upload or analysis endpoints. Configuring it only enables backend adapter use and the round-trip verification below; API uploads remain temporary.

1. Create or select a Supabase project.
2. Create a **private** Storage bucket in the project. Do not enable public access or public URLs.
3. In Storage S3 configuration, enable the S3 protocol and generate server-side S3 access keys. Copy the endpoint and region shown there. Supabase documents that these credentials provide full S3 access across buckets and bypass Storage RLS; keep them only in the backend environment and do not store user data until ownership controls are implemented. See [Supabase S3 authentication](https://supabase.com/docs/guides/storage/s3/authentication).
4. Copy `.env.example` to `backend/.env` if needed and set:

   ```dotenv
   OBJECT_STORAGE_PROVIDER=supabase
   SUPABASE_STORAGE_ENDPOINT=https://<PROJECT_REF>.storage.supabase.co/storage/v1/s3
   SUPABASE_STORAGE_REGION=<region-from-supabase-s3-settings>
   SUPABASE_STORAGE_BUCKET=<private-bucket-name>
   SUPABASE_STORAGE_ACCESS_KEY_ID=<server-side-s3-access-key-id>
   SUPABASE_STORAGE_SECRET_ACCESS_KEY=<server-side-s3-secret-access-key>
   ```

   Use the direct storage hostname and endpoint path from the Supabase S3 settings. Replace placeholders locally; do not put real credentials in source control or chat. The adapter requires every Supabase setting and does not fall back to local storage. The configured bucket is not verified until the round-trip check succeeds.
5. From `backend/`, run this round-trip verification. It writes under a generated key and deletes the object afterward:

   ```powershell
   @'
   from app.storage import create_object_storage

   storage = create_object_storage()
   key = None
   try:
       key = storage.put(b"plantguard-r2-check", content_type="text/plain")
       assert storage.exists(key)
       assert storage.get(key).content == b"plantguard-r2-check"
       print("Configured object storage round trip passed")
   finally:
       if key is not None:
           storage.delete(key)
   '@ | .\.venv\Scripts\python.exe -
   ```

Supabase's S3 API uses path-style requests and the project region configured in the dashboard. See [Supabase S3 compatibility](https://supabase.com/docs/guides/storage/s3/compatibility). Do not use local selection as a production fallback.

### Optional Cloudflare R2 adapter

R2 remains supported but is not required. It is not used by current API routes. To select it, use `OBJECT_STORAGE_PROVIDER=r2` and configure `R2_BUCKET_NAME`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`. Keep the bucket private and credentials backend-only; R2 configuration does not silently fall back to local storage.

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
- [ ] Install/start PostgreSQL, create `plantguard`, configure `DATABASE_URL`, and run `alembic upgrade head` (creates `analyses` and `users`).
- [ ] Generate and configure a private `JWT_SECRET_KEY` in `backend/.env` before testing login.
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
- Implement authorization/ownership checks and frontend authentication/token handling before storing user-owned data.
- Integrate the private storage adapter with a defined upload lifecycle and secure access checks before retaining media.
- Configure production CORS origins, secrets, provider credentials (only if an active provider is integrated), deployment, monitoring, and operational backups.

## Required when ML is integrated

The root `ml/` directory contains artifacts, but application compatibility and inference were not verified. When real ML code is provided, inspect its actual preprocessing, outputs, dependencies, and artifact requirements before documenting or configuring paths/devices. Do not alter model artifacts as part of this application setup.
