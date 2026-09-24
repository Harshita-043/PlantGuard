# Current API Contracts

The backend is FastAPI. `GET /docs` provides the generated OpenAPI document when the API is running. Frontend API calls use `VITE_API_URL` as the optional origin prefix.

## Available

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/` | API name, version, and docs path |
| GET | `/api/ping` | `{ "message": "pong" }` |
| GET | `/api/demo` | Static demo greeting |
| POST | `/api/v1/analyze/image` | Accepts JPEG, PNG, or WebP up to 10 MiB; validates actual image content in temporary local storage and removes it after processing. Returns `503` because real ML inference is not integrated. |
| POST | `/api/v1/analyze/video` | `501`; video analysis is not integrated |
| GET | `/api/v1/analyze/health` | `503` while the analysis service is unavailable |
| POST | `/api/v1/analyze/agentic/image` | `503`; no production capability handlers are registered |
| POST | `/api/scan` | `503`; scan persistence and real ML inference are unavailable |
| GET | `/api/scans` | `503`; history persistence is unavailable |
| GET | `/api/scans/{scan_id}` | `503`; scan persistence is unavailable |
| GET | `/api/scans/{scan_id}/report` | `503`; scan persistence is unavailable |
| GET | `/api/v1/analysis/{analysis_id}` | `503`; analysis persistence is unavailable |
| GET | `/api/v1/analyses` | `503`; analysis persistence is unavailable |

Unavailable analysis and scan routes return a JSON `detail` error. Image upload validation uses a generated temporary file and does not retain images. The client filename is ignored. Routes do not return fabricated predictions or sample user data. A database model/migration foundation exists, but these API routes do not use it yet. There is no login, authorization, ownership, plant CRUD, object storage, recommendation, weather, or chat API.

## Future contracts

Do not treat routes described in older planning material as implemented contracts. Add an API contract only when its route, request/response schema, service behavior, and tests exist.
