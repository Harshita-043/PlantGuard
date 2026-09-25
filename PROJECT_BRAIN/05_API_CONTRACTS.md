# Current API Contracts

The backend is FastAPI. `GET /docs` provides the generated OpenAPI document when the API is running. Frontend API calls use `VITE_API_URL` as the optional origin prefix.

## Available

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/` | API name, version, and docs path |
| GET | `/api/ping` | `{ "message": "pong" }` |
| GET | `/api/demo` | Static demo greeting |
| POST | `/api/v1/analyze/image` | Requires authentication. Accepts validated JPEG, PNG, or WebP up to 10 MiB, stores the image privately through the configured `ObjectStorage` provider, and creates an owner-scoped `pending` Analysis record. Returns `201` lifecycle metadata with `result_available: false`; no inference result is fabricated. |
| POST | `/api/v1/analyze/video` | `501`; video analysis is not integrated |
| GET | `/api/v1/analyze/health` | `503` while the analysis service is unavailable |
| POST | `/api/v1/analyze/agentic/image` | `503`; no production capability handlers are registered |
| POST | `/api/scan` | `503`; scan persistence and real ML inference are unavailable |
| GET | `/api/scans` | `503`; history persistence is unavailable |
| GET | `/api/scans/{scan_id}` | `503`; scan persistence is unavailable |
| GET | `/api/scans/{scan_id}/report` | `503`; scan persistence is unavailable |
| GET | `/api/v1/analysis/{analysis_id}` | Requires authentication; returns lifecycle metadata only when the record belongs to the caller. Missing and foreign IDs both return `404`. |
| GET | `/api/v1/analyses` | Requires authentication; returns the caller's records newest first. Supports `skip` and `limit` (1–100). |
| POST | `/api/v1/auth/register` | Creates an account; accepts email/password and returns public user fields only. Password must be 12–128 characters. Duplicate email returns `409`. |
| POST | `/api/v1/auth/login` | Accepts email/password and returns a short-lived JWT bearer token. Invalid credentials return generic `401`. |
| GET | `/api/v1/auth/me` | Requires `Authorization: Bearer <token>` and returns the authenticated user's public identity. |

The image route validates actual decoded content in generated temporary storage, removes the temporary file, then writes through the configured provider selected by the existing storage factory. The client filename is ignored, and neither storage paths nor provider credentials are returned. The database stores the private object key, validated content type and size, owner, status, and timestamps. Image storage and analysis-record creation are transactional at the application boundary: a database failure triggers a best-effort object delete and a safe error. New records remain `pending`; inference and result retrieval are unavailable, and the lifecycle response contains no diagnosis, severity, confidence, masks, or Grad-CAM data. History and retrieval are server-side owner-scoped. Authentication uses Argon2id hashes and signed JWT bearer tokens; password hashes are excluded from response schemas. The older `/api/scan` and `/api/scans` routes remain unavailable. Plant CRUD, recommendations, weather, and chat APIs are not implemented.

## Future contracts

Do not treat routes described in older planning material as implemented contracts. Add an API contract only when its route, request/response schema, service behavior, and tests exist.
