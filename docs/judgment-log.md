# Judgment log

This log records decisions made while building `registry-service` with a coding AI agent.

## 2026-11-01 — Keep the first service small

- **What the coding AI agent suggested:** Start with a FastAPI service exposing a `/health` endpoint.
- **What I decided:** Keep that minimal scope for the first implementation.
- **Why:** A health endpoint gives us a concrete, easy-to-check running service while leaving domain and persistence decisions for a later iteration.

## 2026-11-01 — Use Uvicorn through the project environment

- **What the coding AI agent suggested:** Run the service as the `uvicorn` module with `main:app`, using the service's `.venv` and working directory.
- **What I decided:** Use that approach in the VS Code debug configuration and document `uv sync` followed by `uv run uvicorn`.
- **Why:** The project environment provides the declared FastAPI and Uvicorn dependencies, and `main:app` makes the application entry point explicit and reproducible.

## 2026-11-07 — Use explicit SQLite transactions for plot validation

- **What the coding AI agent suggested:** Check references and plot-name uniqueness inside the same write transaction as the change.
- **Implemented choice (agent; for author review):** Use `BEGIN IMMEDIATE` for plot writes and farm deletion/update, parameterized SQL values, and foreign-key enforcement on every connection.
- **Why:** Concurrent writes cannot invalidate the checks between reading and writing. A failed validation rolls back the transaction. The service opens an existing database instead of silently creating an empty one.

## 2026-11-07 — Define unspecified error and PATCH behavior

- **What the coding AI agent suggested:** Give unsupported methods a distinct `METHOD_NOT_ALLOWED` code and distinguish omitted PATCH fields from explicit nulls.
- **Implemented choice (agent; for author review):** Return 405 with `METHOD_NOT_ALLOWED`; preserve omitted fields, reject explicit nulls, and accept an empty PATCH as a no-op.
- **Why:** The task specifies HTTP 405 without an application code. The selected code describes that condition. Required database fields cannot store nulls, while omission must preserve existing values.

These new entries describe the agent's implemented choices, not a claim that the
author has reviewed every file. The author should review them before submission.
