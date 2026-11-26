# Planner service

Deterministic implementation of FR-2.9–2.14. Independent FastAPI service;
registry and weather are accessed over HTTP only. No database or AI model.

**Each request starts today's soil bucket at the plot's `initial_soil_pct` of
field capacity (default 100 = full).** This is a stateless forecast scenario, not
a measurement or an irrigation history. A new request tomorrow resets the bucket
to that same percent; it must not be presented as measured soil moisture or
confirmation that past irrigation happened. Water is carried across the forecast
days only, never written back.

## Run and configure

From `services/planner-service`:

```sh
uv sync --locked
cp .env.example .env
uv run uvicorn main:app --factory --host 127.0.0.1 --port 8002
```

`config.py` uses pydantic-settings. Required `REGISTRY_URL` and `WEATHER_URL`
must be HTTP(S) URLs and are validated before startup completes. Optional
`UPSTREAM_TIMEOUT_SECONDS` defaults to 5 (positive finite seconds, applied to
each HTTP phase), `PLANNER_TIMEZONE` defaults to `Asia/Jerusalem` (valid IANA
zone, determines today), `MAX_DAILY_RUNTIME_MINUTES` defaults to 1440 (1–1440;
the per-day drip runtime cap). `.env.example` lists every setting; environment
variables override `.env`. Missing required settings cause a startup validation
error. There are no automatic retries; each upstream call has a bounded timeout.

## API and integration

`GET /health` returns `{"status":"ok"}` for planner liveness, independently
of upstream availability. `/docs` exposes OpenAPI.

`GET /v1/plots/{UUID}/plan?days=7` accepts 1–7 days, default 7, starting today.
For example, mid-season tomato with soil 100 mm/m, area1000 m², row1.5 m,
emitter.4 m at1 L/h and daily ET0=6/rain0 produces days whose bucket falls until
a cycle starts below half capacity:

```json
{
  "plot_id": "12345678-1234-1234-1234-123456789012",
  "days": [
    {"date":"2026-11-19","et0_mm":6.0,"kc":1.15,"litres":0.0,"run_minutes":0,"stale":false,
     "bucket_mm":63.1,"bucket_before_mm":70.0,"required_litres":0.0,"required_run_minutes":0,
     "remaining_litres":0.0,"remaining_run_minutes":0,"irrigation_in_progress":false,
     "irrigation_status":"NOT_REQUIRED","capacity_warning":false}
  ]
}
```

Per day: `bucket_before_mm` is the morning bucket before weather and irrigation;
`bucket_mm` is the evening bucket after both. `required_litres`/`required_run_minutes`
are the full deficit; `litres`/`run_minutes` are what was actually scheduled today
(capped at the daily runtime limit); `remaining_litres`/`remaining_run_minutes` are
what still carries into tomorrow. `irrigation_in_progress` is true while a cycle is
unfinished at day's end. `irrigation_status` is one of `NOT_REQUIRED`, `SCHEDULED`
(cycle starts today), `CONTINUING` (cycle begun earlier), `COMPLETED`. `capacity_warning`
is true when a full pumping day cannot even match the crop's own daily ETc demand.

Numbers are JSON numbers; floats are not presentation-rounded. Stale weather
propagates to every returned day. The weather cache controls stale age policy.

Errors use top-level `code` and `detail`: bad days/UUID ->422 `VALIDATION`;
registry plot404 ->404 `NOT_FOUND`; timeout, connection/status/JSON errors,
missing/invalid data ->503 `UPSTREAM_UNAVAILABLE` naming the responsible
service. Soil/emitter404 is an upstream integrity error, not unknown plot.
No fallback plan, invented weather, or default zeros are returned.

Registry calls: `GET /v1/plots/{id}`, then `GET /v1/soils/{soil_id}` and
`GET /v1/emitters/{emitter_id}`. Returned IDs must match the request/references.
Weather: `GET /v1/forecast?lat={plot.lat}&lon={plot.lon}&days={days}`.
Returned lat/lon must match within 1e-7 degrees (serialization tolerance),
and every requested date must be contiguous, ordered, and start today.
Cached forecasts must echo the requested coordinates, not the grid cell center.
Soil water capacity and flow/spacings/area must be finite and positive;
weather ET0/rain must be finite/nonnegative and stale must be a JSON boolean.

**Frontend integration:** label the result a projection from the plot's entered
starting soil moisture; show `bucket_mm` as projected water storage. When
`irrigation_in_progress` is true, show the cycle as scheduled-today plus
remaining-water rather than a single run. Show today's row first, mark stale rows
next to their values, and display service-specific error detail.
Frontend work is part of P2 and is handled by the main task's frontend owner;
this planner's assigned directories do not include the frontend.

## Calculation policy and research provenance

The [reference skill](../../.agents/skills/irrigation-calc-reference/SKILL.md)
is the calculation contract, including three hand examples and units.
[Existing research](docs/research/fao56.md) is preserved unchanged.

Selected Mediterranean stages: tomato30/40/45/30 days, Kc.6/1.15/.8, root.7 m;
bell-pepper30/35/40/20, Kc.6/1.05/.9, root.5 m. Linear development/late curves;
planting day age0. After total age145/125, Kc clamps at.8/.9 indefinitely.
Future planting dates and unsupported crop IDs cause registry-specific503.
There is no inferred harvest date. Capacity is soil water mm/m times root m.
Daily net rainfall/demand updates the bucket, caps at capacity, then irrigates
strictly below half to refill fully. A started cycle latches: it keeps irrigating
on later days even once the bucket is back above half, until it is full again.
This mandated policy is not FAO's crop-specific depletion fraction or Annex8's
complete dual-Kc model. Emitter count=area/(row spacing*emitter spacing),
volume=depth*area; runtime=ceil(volume/count/flow*60).

**Engineering extension (not a P2 or FAO-56 requirement):** a drip runs at most
`MAX_DAILY_RUNTIME_MINUTES` (default1440) per day; the day's deficit above that
cap carries to the next day, where rain and ETc are re-applied before the cycle
continues. This replaces the old instantaneous full refill. See the skill for the
hand examples, numeric tolerance and limits.

The full [P2 assignment](https://raw.githubusercontent.com/alonitac/OzVeruach26/main/tasks/p2.md)
and Matt Pocock's [research skill source](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/research/SKILL.md)
were fetched and read. The main task installed `research` and `frontend-design`
repo-locally through the official skill installer and launched a fresh research
agent, Euler, to verify FAO claims. Its supplemental findings are tracked in
[fao56-verification.md](docs/research/fao56-verification.md); that verification
workflow is in progress independently of this implementation. The original
research remains preserved. Implementation used the pre-existing research,
checked against FAO primary Chapters6/8, plus the user's explicit policies.
Superpowers TDD, verification,
and writing-skills reference guidance were used. No claim is made of independent
agent pressure-testing of the skill; its hand cases are checked by engine tests.

## Verify

```sh
uv run --no-env-file pytest --cov=config --cov=models --cov=engine --cov=upstream --cov=main --cov-report=term-missing
uv run --no-env-file ruff check .
```

Tests use injected settings with `_env_file=None`, deterministic dates and real
HTTP-client serialization through MockTransport, without contacting other
services or reading `.env`. They cover stages, bucket carryover/refill/saturation,
runtime, repeatability, stale propagation, identity checks, dates, corrupt bodies,
timeouts, connection/status failures and missing inputs. Live integration
requires independently running registry/weather services with valid contracts.
