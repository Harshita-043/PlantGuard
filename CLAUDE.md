# PlantGuard AI — Repository Notes

The repository contains a React/Vite frontend and a FastAPI backend. Consult `PROJECT_BRAIN/11_AUDIT.md` for the verified implementation status and `MANUAL_SETUP.md` for current local setup.

## Current boundaries

- Do not implement or modify the ML track in an application task. Root `ml/` artifacts exist, but the application does not load them for inference.
- Do not return fabricated plant diagnoses, severity, confidence, evidence, or health scores. Analysis endpoints are intentionally unavailable until real inference is integrated.
- The agentic core has contracts/components but no production capability handlers. Never add arbitrary command, code, SQL, filesystem, network, model, or storage execution.
- There is no verified authentication, authorization, plant/scan persistence, migration history, or object-storage implementation.
- Frontend data must come from FastAPI. Do not replace missing backend services with hardcoded sample user or plant records.

## Project documentation

`PROJECT_BRAIN/` records verified architecture and contracts. Update `PROJECT_BRAIN/12_CHANGELOG.md` for material changes. Keep all manual run/setup steps in the single `MANUAL_SETUP.md` file.

## Tooling

- Frontend: pnpm is declared in `frontend/package.json`; scripts are in that package's `package.json`.
- Backend dependencies: `backend/requirements.txt`.
- Preserve existing user worktree changes and model artifacts. Do not commit automatically.

PLANTGUARD AI — IMPLEMENTATION RULES

This repository is the source of truth.

Before modifying anything:
1. Inspect git status.
2. Inspect the relevant existing files.
3. Read the relevant project brain documentation.
4. Understand existing architecture and contracts.
5. Do not recreate existing functionality.
6. Do not overwrite or delete user work without explicit justification.

Core rules:
- Implement only the requested phase.
- Do not jump ahead.
- Do not silently implement future phases.
- Do not create speculative architecture.
- Do not create duplicate services, routes, models, schemas, utilities, or documentation.
- Do not fabricate ML predictions, plant diagnoses, users, database records, evidence, providers, or production results.
- Do not create mock production services.
- Test-only fakes are allowed only where explicitly required for isolated testing.
- Unsupported capabilities must fail clearly rather than pretending to work.
- Preserve existing ML artifacts.
- Never retrain, modify, replace, or overwrite existing ML model weights unless explicitly instructed in the ML integration phase.
- Never claim a capability is implemented unless the code and tests demonstrate it.
- Keep frontend/backend/API contracts synchronized.
- Keep secrets out of source control.
- Keep .env.example complete with safe placeholders for every real environment variable.
- Keep MANUAL_SETUP.md as the single source of truth for manual setup actions.
- Update project brain documentation only when the implementation changes the documented architecture/state.
- Update PROJECT_BRAIN/12_CHANGELOG.md for meaningful completed phases.
- Prefer small, production-oriented changes over large rewrites.

At the end of every phase:
1. Run relevant tests.
2. Run relevant type/lint/build checks where available.
3. Inspect git diff.
4. Verify no unrelated files changed.
5. Report:
   - implemented
   - files changed
   - tests/checks passed
   - known limitations
   - manual actions required
   - next recommended phase
6. STOP.

Do not automatically continue to the next phase.