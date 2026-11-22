---
name: registry-api
description: Use when adding, changing, reviewing, or testing an AgroPilot registry-service endpoint, request or response schema, validation rule, or HTTP error contract. Includes registry farm, plot, and catalog API changes.
---

# Registry API conventions

Read the applicable task specification, then inspect the service README, existing routers and schemas, shared exception handlers, and integration tests. Ask for clarification when the specification leaves a public contract decision open.

- Put resource routes under `/v1`. Keep the existing `GET /health` operational probe at its documented path.
- Return only the fields in the agreed contract. Other services can come to depend on any field exposed by the API. List responses are JSON arrays. An empty list is `200` with `[]`.
- For `PATCH`, update only explicitly supplied fields and preserve omitted fields. Follow the existing schema rules for explicit nulls and empty updates.
- Reuse the service's shared RFC 9457 error handling. It keeps clients on one response format for router, validation, and database failures.

| HTTP status | Stable code | When it applies |
| --- | --- | --- |
| 422 | `VALIDATION` | Invalid request, including a malformed UUID |
| 404 | `NOT_FOUND` | A requested resource does not exist |
| 409 | `CONFLICT` | The operation conflicts with existing state |
| 503 | `UNAVAILABLE` | Registry database unavailable. Include `Retry-After`. |

Preserve other documented error behavior, such as `405 METHOD_NOT_ALLOWED` with `Allow`. Every error uses `application/problem+json`. An unknown farm example:

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

## Verify the HTTP contract

Cover success and every applicable failure at the HTTP boundary. Exercise the new or changed route itself, including errors produced by shared handlers. Assert the status, content type, stable code, and required headers. For example, a UUID-based database-backed read needs separate checks for malformed UUID, unknown ID, and database unavailability.

From `services/registry-service`, install the locked dependencies and run the
same pytest and coverage command used by the project's CI:

```bash
uv sync --locked --python 3.12
DATABASE_URL=sqlite:///registry.db \
  uv run --no-sync python -m pytest --cov --cov-report=term --cov-report=html
```

The suite includes pytest-native tests, and Registry coverage must remain at
100% for both lines and branches.
