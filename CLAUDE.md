# PlantGuard AI — Repository Notes

The repository contains a React/Vite frontend and a FastAPI backend. Consult `PROJECT_BRAIN/11_AUDIT.md` for the verified implementation status and `MANUAL_SETUP.md` for current local setup.

## Current boundaries

- Do not implement or modify the ML track in an application task. Root `ml/` artifacts exist, but the application does not load them for inference.
- Do not return fabricated plant diagnoses, severity, confidence, evidence, or health scores. Analysis endpoints are intentionally unavailable until real inference is integrated.
- The agentic core has contracts/components but no production capability handlers. Never add arbitrary command, code, SQL, filesystem, network, model, or storage execution.
- SQLAlchemy/PostgreSQL configuration and Alembic migrations provide the initial analysis metadata schema. Analysis/scan API persistence, plant CRUD, authentication/authorization, and object storage are still unavailable.
- Frontend data must come from FastAPI. Do not replace missing backend services with hardcoded sample user or plant records.

## Project documentation

`PROJECT_BRAIN/` records verified architecture and contracts. Update `PROJECT_BRAIN/12_CHANGELOG.md` for material changes. Keep all manual run/setup steps in the single `MANUAL_SETUP.md` file.

## Tooling

- Frontend: pnpm is declared in `frontend/package.json`; scripts are in that package's `package.json`.
- Backend dependencies: `backend/requirements.txt`.
- Preserve existing user worktree changes and model artifacts. Do not commit automatically.
