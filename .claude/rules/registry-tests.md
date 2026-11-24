---
globs: services/registry-service/tests/**
---

Registry tests must keep **100% line and branch coverage** — this is enforced by
`fail_under = 100` in `pyproject.toml` and checked by CI on every PR.

- Every new endpoint or code path needs a corresponding test before the branch is merged.
- Use `IsolatedAsyncioTestCase` with the existing `setUp` pattern (isolated SQLite per test).
- Assert the HTTP status, `content-type: application/problem+json`, the stable `code` field, and any required headers (e.g. `Allow`, `Retry-After`).
- Never mock the database — test against the real SQLite engine to catch schema and query issues.
- Run locally before pushing:

```bash
cd services/registry-service
uv run --no-sync python -m pytest --cov --cov-report=term
```
