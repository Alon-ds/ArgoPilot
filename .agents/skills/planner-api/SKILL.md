---
name: planner-api
description: Use when adding, changing, reviewing, or testing the AgroPilot planner-service: irrigation plan calculation, crop curves, soil bucket, upstream Registry/Weather calls, or the plan HTTP contract.
---

# Planner API conventions

Read `services/planner-service/README.md` and the
[FAO-56 research](../../../services/planner-service/docs/research/fao56.md) before
changing calculation logic. Load the `irrigation-calc-reference` skill when
touching crop stages, bucket arithmetic, or emitter runtime.

## HTTP contract

```
GET /v1/plots/{plot_uuid}/plan?days=7
```

`days` accepts 1–7. Response is a `Plan` object — never a bare list.

| HTTP status | Stable code | When |
| --- | --- | --- |
| 404 | `NOT_FOUND` | Plot does not exist in Registry |
| 422 | `VALIDATION` | Invalid `plot_uuid` or `days` parameter |
| 503 | `UPSTREAM_UNAVAILABLE` | Registry or Weather returned an error or invalid data |

The `detail` field on a 503 names the failing upstream:
`"registry-service unavailable or returned invalid data."` or
`"weather-service unavailable or returned invalid data."`

## Upstream rules

- Registry and Weather are called once each per plan request. No retries — each upstream owns its own retry logic.
- Every upstream response is validated with Pydantic before use. A validation failure raises `UpstreamUnavailable`, not a 500.
- Planner rejects: plot IDs that don't match, coordinates that differ by more than 1e-7°, forecast gaps/reorder/missing dates, non-finite values, and future planting dates.
- A `plot_id` mismatch between request and Registry response also raises `UpstreamUnavailable("registry-service")`.

## Calculation invariants

- The plan always starts today (server timezone) with a **full soil bucket**.
- Water carries forward across forecast days only — no database writes.
- `litres` and `run_minutes` are zero when irrigation is not needed.
- `run_minutes` uses `math.ceil` via exact rational arithmetic to avoid floating-point boundary errors.
- The `stale` field mirrors the Weather service stale flag for every day.

## Verification

```bash
cd services/planner-service
uv sync --locked
uv run python -m pytest
```
