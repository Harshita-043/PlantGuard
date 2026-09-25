# Dependency Sources

The checked-in manifests are authoritative for declared application dependencies:

- Frontend: `frontend/package.json` and `frontend/pnpm-lock.yaml`; `package.json` declares pnpm. An npm lockfile is also present, so lockfile consistency should be reviewed before dependency changes.
- Backend: `backend/requirements.txt`.
- Root ML artifacts have separate requirements/runtime needs that are not integrated into the backend application and are outside this application audit.

The current backend manifest includes FastAPI, Pydantic, pydantic-settings, Pillow, NumPy, multipart form support, SQLAlchemy, Alembic, Psycopg 3 with its binary distribution, and boto3 for the Supabase Storage and Cloudflare R2 S3-compatible adapters. Persistence packages support the initial analysis schema; database and object storage are not wired into API workflows.

Do not treat package presence as evidence that a capability is implemented. Do not introduce dependencies for future features during stabilization.

## Python compatibility

Backend pins target Python 3.14. Pillow, NumPy, Pydantic, and the PostgreSQL driver are pinned to releases with Python 3.14 wheels. Reinstall `backend/requirements.txt` in a Python 3.14 virtual environment after changing these pins.
