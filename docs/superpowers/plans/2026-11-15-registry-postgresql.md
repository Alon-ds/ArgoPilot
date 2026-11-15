# Registry PostgreSQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Registry API against SQLite locally and PostgreSQL when `DATABASE_URL` selects it, without changing its public HTTP contract.

**Architecture:** SQLAlchemy Core owns the table definitions, database engines, and parameterized queries. FastAPI routers retain request validation and response schemas, then obtain a transaction-scoped SQLAlchemy connection. A pydantic-settings configuration module chooses the database URL and protects tests from a developer's `.env`.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy Core, pydantic-settings, psycopg, SQLite, PostgreSQL, uv, unittest.

**Spec:** `docs/superpowers/specs/2026-11-15-registry-postgresql-design.md`

## Global Constraints

- SQLite remains the default for local development when `DATABASE_URL` is absent.
- PostgreSQL is selected solely through `DATABASE_URL`.
- Every database operation goes through SQLAlchemy.
- Routes retain their paths, response schemas, HTTP status codes, `application/problem+json` responses, stable error codes, and `Retry-After: 5` for `503`.
- Each service setting belongs in one `config.py` and has a committed `.env.example`. Real `.env` files remain untracked.
- PostgreSQL must have a documented bootstrap command that creates the schema and loads the existing 15 seed rows.
- PostgreSQL integration tests run in CI.

## Review Focus

- An absent SQLite file must still produce `503 UNAVAILABLE` with `Retry-After: 5`.
- A malformed database URL must stop the service with a clear configuration error.
- A duplicate plot created concurrently must leave one row and return the existing `409 CONFLICT` contract for the rejected request.
- A failed write must roll back in both SQLite and PostgreSQL.
- Existing local `registry.db` data must remain readable when SQLite is selected.

---

## File structure

- Create `services/registry-service/config.py` for settings and database URL resolution.
- Create `services/registry-service/tables.py` for SQLAlchemy `MetaData`, tables, constraints, and seed-row constants.
- Modify `services/registry-service/database.py` for engine creation, transactional connections, result mapping, and error normalization.
- Modify `services/registry-service/farms.py`, `plots.py`, and `catalogs.py` to use SQLAlchemy Core statements.
- Modify `services/registry-service/errors.py` for SQLAlchemy and PostgreSQL driver failures.
- Create `services/registry-service/bootstrap.py` for schema creation and seeding.
- Create `services/registry-service/.env.example` and `.claude/settings.json`.
- Modify `services/registry-service/seed_registry.sh`, `README.md`, `pyproject.toml`, `uv.lock`, `benchmark.py`, and `.github/workflows/registry-tests.yml`.
- Modify `services/registry-service/tests/test_api.py` and create `services/registry-service/tests/test_postgres.py`.

### Task 1: Configuration and SQLAlchemy schema

**Files:**
- Create: `services/registry-service/config.py`
- Create: `services/registry-service/tables.py`
- Create: `services/registry-service/.env.example`
- Modify: `services/registry-service/pyproject.toml`
- Modify: `services/registry-service/uv.lock`
- Create: `.claude/settings.json`
- Test: `services/registry-service/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.database_url: str`, `metadata: MetaData`, and SQLAlchemy table objects for farms, plots, crops, soils, and emitters.
- Consumes: `DATABASE_URL` from the process environment or local `.env`.

- [ ] Write tests that prove absent `DATABASE_URL` resolves to the existing SQLite file, a supplied PostgreSQL URL wins over `.env`, and an invalid URL fails during settings creation.
- [ ] Run the new configuration tests and confirm they fail because the settings module does not exist.
- [ ] Add `sqlalchemy`, `pydantic-settings`, and PostgreSQL driver dependencies, then regenerate the lock file.
- [ ] Implement `Settings` in `config.py` and the SQLAlchemy Core table metadata in `tables.py`. Preserve the P1 column names, primary keys, foreign keys, and plot-name uniqueness within a farm.
- [ ] Add `.env.example` with a safe SQLite URL and a commented PostgreSQL example. Add `.claude/settings.json` with the required denial rule for `.env` reads.
- [ ] Run `uv run python -m unittest tests.test_config -v` and confirm it passes.
- [ ] Commit configuration and schema definitions.

### Task 2: Database layer and route migration

**Files:**
- Modify: `services/registry-service/database.py`
- Modify: `services/registry-service/farms.py`
- Modify: `services/registry-service/plots.py`
- Modify: `services/registry-service/catalogs.py`
- Modify: `services/registry-service/errors.py`
- Modify: `services/registry-service/tests/test_api.py`

**Interfaces:**
- Consumes: `Settings.database_url` and table objects from Task 1.
- Produces: transactional database connections and unchanged Registry endpoint responses.

- [ ] Extend the existing API tests with assertions for rollback after a failed create or patch, an unavailable SQLite database, and all existing problem-response headers.
- [ ] Run the affected API tests and confirm they fail against the incomplete SQLAlchemy layer.
- [ ] Replace `sqlite3.connect` with SQLAlchemy engine and transaction management. Return mapping rows so routers can keep producing dictionaries.
- [ ] Convert all farm, plot, and catalog statements to SQLAlchemy Core. Use bound parameters and table objects for every value and identifier.
- [ ] Preserve the existing duplicate-name and foreign-key behavior. Translate `IntegrityError` and connection failures to the existing HTTP error contracts.
- [ ] Run `uv run python -W error::ResourceWarning -m unittest discover -s tests -v` against SQLite and confirm all tests pass.
- [ ] Commit the SQLite-compatible SQLAlchemy migration.

### Task 3: PostgreSQL bootstrap and integration coverage

**Files:**
- Create: `services/registry-service/bootstrap.py`
- Modify: `services/registry-service/seed_registry.sh`
- Create: `services/registry-service/tests/test_postgres.py`
- Modify: `.github/workflows/registry-tests.yml`
- Modify: `services/registry-service/README.md`

**Interfaces:**
- Consumes: `DATABASE_URL`, SQLAlchemy `metadata`, and the shared seed constants.
- Produces: `python -m bootstrap`, which creates tables and inserts the 15 P1 seed rows into an empty PostgreSQL database.

- [ ] Write PostgreSQL integration tests that bootstrap an empty database, verify the 2 farms, 4 plots, 2 crops, 3 soils, and 4 emitters, then exercise list, item, create, patch, conflict, and unavailable-service API contracts.
- [ ] Run the integration tests against a PostgreSQL test URL and confirm they fail before the bootstrap exists.
- [ ] Implement `bootstrap.main() -> None`. It must create metadata tables and insert the seed rows transactionally. Make rerunning the command safe by rejecting nonempty tables with a clear message.
- [ ] Update the shell seed command to call the Python bootstrap for SQLite and retain its documented destructive behavior only where explicitly invoked.
- [ ] Add a PostgreSQL service container and `POSTGRES_TEST_DATABASE_URL` to GitHub Actions. Run SQLite tests and PostgreSQL integration tests as separate CI steps.
- [ ] Document local PostgreSQL setup, `.env`, bootstrap, and both supported database URLs in the Registry README.
- [ ] Run the SQLite suite and PostgreSQL suite. Confirm all route contracts match.
- [ ] Commit bootstrap, PostgreSQL tests, CI, and documentation.

### Task 4: Benchmark and final verification

**Files:**
- Modify: `services/registry-service/benchmark.py`
- Modify: `services/registry-service/README.md`
- Modify: `docs/registry-benchmark.md`
- Modify: `docs/registry-benchmark.json`

**Interfaces:**
- Consumes: a bootstrapped PostgreSQL `DATABASE_URL`.
- Produces: p95 measurements for Registry list and item GET requests at 10 requests per second.

- [ ] Add a benchmark case for PostgreSQL `GET /v1/farms`, `GET /v1/plots`, and item reads at 10 requests per second. Record sample count, p95, database URL type, and execution date without credentials.
- [ ] Run the benchmark against local PostgreSQL and confirm the measurements are recorded.
- [ ] Update the benchmark documentation with the commands, environment, measurements, and whether each p95 meets the 100 ms requirement.
- [ ] Run the full test suite, inspect `git diff --check`, and verify no `.env`, database file, or local virtual environment is staged.
- [ ] Commit benchmark evidence and final documentation.

## Self-review

FR-2.1 and NFR-2.1 are covered by Tasks 1 and 2. FR-2.2 is covered by Task 3. NFR-2.2 is covered by Task 4. The API stability requirements are covered by Tasks 2 and 3. Global environment configuration requirements are covered by Task 1. The plan deliberately excludes Weather, Planner, and Frontend because each is an independent P2 subsystem with its own design and implementation plan.
