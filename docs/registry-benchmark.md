# Registry read benchmark

Measured on 2026-11-07 against a local Uvicorn server on port 8001 and the seeded SQLite database.

Workload: 600 HTTP GET requests over 60 seconds at 10 total requests/second, round-robin across 10 routes (60 samples per route). Warm-up excluded. No HTTP errors.

| Endpoint | p95 (ms) | Scheduled p95 (ms) |
|---|---:|---:|
| `/v1/farms` | 9.69 | 14.96 |
| `/v1/farms/a9c1e4b2-6f70-4d8e-a144-3f8b5c904004` | 6.13 | 11.496 |
| `/v1/plots` | 7.132 | 11.71 |
| `/v1/plots/c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002` | 14.591 | 15.691 |
| `/v1/crops` | 6.146 | 10.585 |
| `/v1/crops/bell-pepper` | 7.028 | 12.117 |
| `/v1/soils` | 6.689 | 11.163 |
| `/v1/soils/clay-loam` | 6.411 | 11.607 |
| `/v1/emitters` | 5.468 | 10.401 |
| `/v1/emitters/dripnet-pc-0.6` | 6.81 | 12.019 |

All routes passed the 100 ms p95 threshold, including timing from scheduled dispatch.

Limitations: local machine, small seeded dataset, mixed workload at 10 total requests/second. This does not establish 10 requests/second per route, production capacity, or large-dataset performance. Percentiles use nearest rank.

Raw measurements and environment: [registry-benchmark.json](registry-benchmark.json).

Reproduce from `services/registry-service`: start `uv run uvicorn main:app --host 127.0.0.1 --port 8001 --no-access-log`, then run `uv run python benchmark.py --output ../../docs/registry-benchmark.json` in another terminal.
# P2 PostgreSQL benchmark

On November 15, 2026, a local run on macOS arm64 used Python 3.12.11,
PostgreSQL 15.15, and the 15 course seed rows. The client sent 600 HTTP
requests over 60 seconds, rotating across the ten list and item endpoints
at 10 requests per second total. There were zero errors. The worst per-route
p95 was 29.967 ms, or 37.478 ms including client scheduling delay. All ten
routes met the 100 ms target in this run.

With Uvicorn connected to the seeded PostgreSQL database, run from the service directory:

```bash
uv run python benchmark.py --database postgresql --base-url http://127.0.0.1:58001 --duration 60 --rate 10 --summary-only --output ../../docs/registry-postgresql-benchmark.json
```

See [the PostgreSQL measurement report](registry-postgresql-benchmark.json)
for the per-route results.
