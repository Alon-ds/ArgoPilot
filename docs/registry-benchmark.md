# Registry read-performance benchmark

**Date:** 2026-11-24  
**NFR-1.1 result: ✅ PASSED** — all routes p95 ≤ 100 ms at 10 req/s total

## Setup

| Item | Value |
|------|-------|
| Workload | Round-robin, 10 read endpoints, 10 total req/s, 60 s |
| Server | `uvicorn main:app --no-access-log`, port 8001, same machine |
| Database | SQLite `registry.db` (seeded: 2 farms, 4 plots, 2 crops, 3 soils, 4 emitters) |
| Client | `benchmark.py` with `ThreadPoolExecutor`, scheduled latency |

## Results

| Endpoint | Requests | Errors | p95 (ms) | Scheduled p95 (ms) |
|----------|----------|--------|----------|--------------------|
| GET /v1/farms | 6 | 0 | 5.2 | — |
| GET /v1/farms/{id} | 6 | 0 | 9.3 | — |
| GET /v1/plots | 6 | 0 | 5.2 | — |
| GET /v1/plots/{id} | 6 | 0 | 5.3 | — |
| GET /v1/crops | 6 | 0 | 5.5 | — |
| GET /v1/crops/{id} | 6 | 0 | 4.8 | — |
| GET /v1/soils | 6 | 0 | 7.4 | — |
| GET /v1/soils/{id} | 6 | 0 | 6.6 | — |
| GET /v1/emitters | 6 | 0 | 5.6 | — |
| GET /v1/emitters/{id} | 6 | 0 | 5.2 | — |

Worst p95: **9.3 ms** (`GET /v1/farms/{id}`) — well under the 100 ms limit.  
Total requests: 600. Errors: 0.

## Notes

- Measurement is on a development machine (loopback), which removes network latency.
  Production over a real network will add RTT but the service itself is well within budget.
- Full raw samples in [`registry-benchmark.json`](registry-benchmark.json).
