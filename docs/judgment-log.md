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

## 2026-11-26 — Multi-day irrigation with a daily runtime cap

- **What the coding AI agent proposed:** Replace the planner's instantaneous full
  refill (a plot needing 10 days of runtime showed 100% soil the same day) with a
  per-day runtime cap, proportional bucket update, and deficit carryover across the
  forecast; latch a started cycle so it keeps irrigating above the half trigger until
  the bucket is full; warn when a full pumping day cannot match daily ETc demand.
- **What I decided:** Adopt it. Daily cap default 1440 min, configurable via
  `MAX_DAILY_RUNTIME_MINUTES`; status enum `NOT_REQUIRED/SCHEDULED/CONTINUING/COMPLETED`;
  new PlanDay fields for before/required/remaining water and the capacity warning.
- **Why:** The old model reported water the system physically cannot deliver in a day,
  which is misleading for hot, high-demand plots (the Eilat demo). Capping runtime and
  carrying the deficit models what the drip can actually do.
- **Alternatives considered:** (a) Keep instantaneous refill and only warn — rejected,
  still reports impossible same-day soil. (b) Fixed runtime subtraction each day without
  re-applying weather — rejected, drifts from the real balance. (c) Persist bucket state
  between requests — rejected, the service is deliberately stateless per request.
- **Limitations / Phase 2:** The daily cap and multi-day carryover are an engineering
  extension, not a P2 or FAO-56 requirement, and are documented as such in the skill and
  README. `initial_soil_pct` is a grower-entered estimate, to be replaced by a sensor feed
  in a later phase; the forecast horizon is seven days, so a longer cycle reports that it
  continues beyond the horizon rather than resolving it.

These new entries describe the agent's implemented choices, not a claim that the
author has reviewed every file. The author should review them before submission.
