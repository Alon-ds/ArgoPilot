---
name: registry-api
description: Use when adding, changing, reviewing, or testing any AgroPilot registry-service endpoint, schema, validation rule, or HTTP error contract. Covers farms, plots, catalog reads (crops, soils, emitters), and the farm summary route.
---

# Registry API conventions

Before writing any code, read the existing router file and integration tests for the resource you're changing. Check the service README for any undocumented behavior.

## Route structure

- All resource routes live under `/v1`.
- `GET /health` stays at its documented path — never move it.
- List responses are always JSON arrays. An empty result is `200 []`, never `404`.
- Return only the fields the agreed spec lists. Any extra field can become a dependency for other services.

## PATCH behavior

Update only fields explicitly provided in the request body. Omitted fields must stay unchanged. An empty body `{}` is a valid no-op — return the current state unchanged. This matters because clients send only the diff they care about.

## Error format — RFC 9457

Every error uses `application/problem+json`. Never return FastAPI's default `{"detail": ...}` body. Use the shared error handler already in the service.

| HTTP status | Stable `code` | When |
| --- | --- | --- |
| 422 | `VALIDATION` | Invalid request body, malformed UUID, or unknown foreign key |
| 404 | `NOT_FOUND` | Requested resource does not exist |
| 409 | `CONFLICT` | Operation conflicts with existing state (duplicate name, farm has plots) |
| 503 | `UNAVAILABLE` | Database unreachable — include `Retry-After: 5` |
| 405 | `METHOD_NOT_ALLOWED` | Verb not supported — include `Allow` header |

Example unknown-farm response:
```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Farm not found.",
  "instance": "/v1/farms/00000000-0000-0000-0000-000000000000",
  "code": "NOT_FOUND"
}
```

## Tests — always required

Cover every new endpoint and code path before the branch merges. For each route, test:
1. The happy path (correct status, body, and content-type).
2. Each failure case: malformed UUID, unknown ID, conflict, and database unavailable.
3. Assert `content-type: application/problem+json` and the stable `code` field on every error.

If the spec is silent about behavior — a status code, a field, an edge case — **ask before implementing**. Inventing behavior forces every consumer to adapt later.

## Running tests

```bash
cd services/registry-service
uv run --no-sync python -m pytest --cov --cov-report=term
```

Coverage must stay at **100% lines and branches** (`fail_under = 100` in `pyproject.toml`). CI enforces this on every PR.
