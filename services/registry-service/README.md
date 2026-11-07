# Registry service

FastAPI service for farms, agricultural plots, and read-only crop, soil, and emitter catalogs.

## Run locally

Prerequisites: Python 3.12+, `uv`, and the `sqlite3` command-line tool.
From the repository root:

```bash
cd services/registry-service
uv sync
```

For the first setup only, create the database:

```bash
bash seed_registry.sh
```

This **deletes and recreates** the target database. Do not rerun it to start the
service. It creates `registry.db` in the current directory with 2 farms, 4 plots,
2 crops, 3 soils, and 4 emitters. The service always opens the file in
`services/registry-service`, regardless of the process working directory.
An absent database returns `503` from database-backed routes; `/health` only
checks that the application is running.

Start the service from this directory:

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Check that the service is running at <http://127.0.0.1:8000/health>. It returns:

```json
{"status": "ok"}
```

The VS Code configuration in the repository root (`.vscode/launch.json`) can also start the service through Run and Debug.
Restart a running server after code changes, or use Uvicorn's `--reload` option
for development. Interactive API documentation: <http://127.0.0.1:8000/docs>.

## API

| Resource | List | Item | Create | Partial update | Delete |
|---|---|---|---|---|---|
| Farms | `GET /v1/farms` | `GET /v1/farms/{id}` | `POST /v1/farms` | `PATCH /v1/farms/{id}` | `DELETE /v1/farms/{id}` |
| Plots | `GET /v1/plots` | `GET /v1/plots/{id}` | `POST /v1/plots` | `PATCH /v1/plots/{id}` | `DELETE /v1/plots/{id}` |
| Crops | `GET /v1/crops` | `GET /v1/crops/{id}` | — | — | — |
| Soils | `GET /v1/soils` | `GET /v1/soils/{id}` | — | — | — |
| Emitters | `GET /v1/emitters` | `GET /v1/emitters/{id}` | — | — | — |

Filter plots with `GET /v1/plots?farm_id={uuid}`. Empty lists return `200` and `[]`.
Creation returns `201`, reads and updates return `200`, and deletion returns `204`
with no response body. Farm and plot IDs are generated UUIDs; catalog IDs are
strings such as `tomato`, `loam`, and `dripnet-pc-1.0`.

Create a farm:

```bash
curl -X POST http://127.0.0.1:8000/v1/farms \
  -H 'Content-Type: application/json' -d '{"name":"My farm"}'
```

Example plot body using the seeded farm and catalogs:

```json
{
  "farm_id": "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001",
  "name": "South block",
  "area_m2": 1000,
  "crop_id": "tomato",
  "planting_date": "2026-03-01",
  "soil_id": "loam",
  "row_spacing_m": 1.5,
  "emitter_spacing_m": 0.4,
  "emitter_id": "dripnet-pc-1.0",
  "lat": 31.25,
  "lon": 34.79
}
```

Send this body to `POST /v1/plots`. For `PATCH`, send only the fields to change;
omitted fields are preserved, explicit `null` values are rejected, and `{}` is a
successful no-op. Names are trimmed and must be nonempty. Area and spacings must
be finite and positive, planting dates must not be in the future (server local
date), and latitude/longitude must fall within ±90/±180. References must exist.
Plot names must be unique within a farm, including when moving a plot to another
farm. Farms with plots cannot be deleted.

## Errors

Errors use `application/problem+json` with `type`, `title`, `status`, `detail`,
`instance`, and `code`.

| Status | Code | Meaning |
|---|---|---|
| 422 | `VALIDATION` | Invalid input, malformed UUID, or nonexistent reference in a plot body |
| 404 | `NOT_FOUND` | Requested item or route does not exist |
| 409 | `CONFLICT` | Duplicate plot name in a farm, or deletion of a farm with plots |
| 503 | `UNAVAILABLE` | SQLite failure, including missing or corrupt database; includes `Retry-After: 5` |
| 405 | `METHOD_NOT_ALLOWED` | Unsupported method, including catalog writes; includes `Allow` |

`METHOD_NOT_ALLOWED` is the implementation choice for 405 because the task
does not specify its code. Looking up a missing item by URL returns 404;
referencing a missing item in plot input returns 422.

## Tests

From this directory, run:

```bash
uv run python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases populated from the SQL in `seed_registry.sh`.
They do not run the shell script or modify the local `registry.db`.

## Read performance

Start a separate server with the current code:

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8001 --no-access-log
```

In another terminal, from this directory:

```bash
uv run python benchmark.py --output ../../docs/registry-benchmark.json
```

This runs a 60-second, read-only HTTP workload at 10 total requests per second,
distributed equally across the list and item routes for all five resources.
Each route receives 60 requests. The report includes p95 for each route,
errors, timing from the scheduled request time, and raw samples.
The command fails if a route has errors or scheduled p95 exceeds 100 ms.
This measures a mixed workload on the seeded database, not 10 requests per
second to each individual route or performance on a larger dataset.

Measured results: [benchmark report](../../docs/registry-benchmark.md).
Implementation decisions: [judgment log](../../docs/judgment-log.md).
