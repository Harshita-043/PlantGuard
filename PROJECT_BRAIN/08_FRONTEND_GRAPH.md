# Frontend — Verified State

The app is under `frontend/client/`, uses React Router, and is served by Vite on port 8080. Actual routes are:

- `/` and `/dashboard`: shell/dashboard empty state; user statistics and weather are not shown as real data.
- `/plants`: empty state; no plant API exists.
- `/scan`: image upload UI calls `POST /api/v1/analyze/image`. The backend currently returns `503` because ML inference is not integrated.
- `/scan/results/:scanId`: requests the analysis API, but persistence/retrieval is unavailable.
- `/history`, `/recommendations`, `/weather`, `/chat`, `/profile`, `/settings`: shell placeholders; no corresponding functional APIs exist.
- Unknown paths render `NotFound`.

The shared TypeScript response types live in `frontend/shared/api.ts`. The API client is `frontend/client/lib/api.ts`; it uses `VITE_API_URL` when configured and otherwise targets the current origin. There is no authentication state or protected route system. The UI must not infer that account, scan history, recommendations, or diagnosis works when those APIs are absent.
