# RUN_GUIDE – PlantGuard AI (Windows)

## Prerequisites
- Windows 11 with PowerShell
- Git, Docker Desktop (WSL 2 backend), Python 3.12, Node 20 installed and available in `PATH`

## 1. Clone the repository
```powershell
git clone https://github.com/your-org/plantguard-ai.git
cd "C:\Users\Asus\PLANTGUARD AI"
```

## 2. Set up environment variables
```powershell
copy .env.example .env
# Edit .env and set at least:
# DATABASE_URL=postgresql+psycopg://plantguard:plantguard@localhost:5432/plantguard
# SUPABASE_STORAGE_ACCESS_KEY_ID=…
# SUPABASE_STORAGE_SECRET_ACCESS_KEY=…
```

## 3. Backend virtual environment & dependencies
```powershell
python -m venv venv_ml
.\venv_ml\Scripts\Activate.ps1
pip install -r backend/requirements.txt
pip install -r backend/requirements-ml.txt
```

## 4. Database migration (first run only)
```powershell
alembic -c backend/alembic.ini upgrade head
```

## 5. Start the full stack with Docker Compose
```powershell
docker compose up -d
```
- PostgreSQL → `localhost:5432`
- Backend API → `localhost:8000`
- Frontend dev server → `localhost:5173`
- Frontend production (nginx) → `http://localhost`

## 6. Verify services
```powershell
curl http://localhost:8000/health
curl http://localhost:8000/ready
```
Both should return JSON with `"status":"ready"` (or `"degraded"` if an optional model failed).

## 7. Run backend tests
```powershell
.\venv_ml\Scripts\Activate.ps1
pytest -q backend/app/tests
```

## 8. Frontend development workflow
```powershell
cd frontend
npm install          # one‑time
npm run dev          # hot‑reload dev server on http://localhost:5173
```

## 9. Build frontend for production
```powershell
cd frontend
npm run build
# Built assets appear in ./frontend/dist and are served by the nginx container.
```

## 10. Switch inference profile (optional)
Set `PLANTGUARD_INFERENCE_PROFILE` in `.env` to `cpu`, `cuda`, or `auto`, then restart the backend:
```powershell
docker compose restart backend
```

## 11. Clean up
```powershell
docker compose down -v   # stop containers and remove volumes
Remove-Item -Recurse -Force .\venv_ml
```

*All commands are PowerShell syntax. Adjust paths if you use a different shell.*

