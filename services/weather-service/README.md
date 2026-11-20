# Weather service

Independent FastAPI service for FR-2.3–2.8 and NFR-2.3 in
[P2](https://github.com/alonitac/OzVeruach26/blob/main/tasks/p2.md).
It knows coordinates and dates only, keeps forecasts in process memory, and
communicates with Open-Meteo over HTTP using httpx. No database or imports from
other services.

## Run

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).
Run all commands from this directory:

```sh
uv sync --frozen
# Optional: copy safe examples and customize locally. Never commit .env.
cp .env.example .env
uv run --frozen uvicorn main:app --host 127.0.0.1 --port 8001 --no-access-log
```

For the integration stack, use `--port 18001` (registry `18000`, planner `18002`).
The host and port are uvicorn command-line deployment options. Access logging is
disabled to avoid pipe backpressure during load tests. There is one cache per
worker; use one worker when measuring shared-cache behavior. Restarting empties it.

All application settings live in `config.py` using pydantic-settings. Process
environment variables override `.env`; safe defaults allow startup without a
local `.env`. Invalid settings fail during startup before accepting requests.
Tests and the isolated benchmark explicitly disable `.env` loading.

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `OPEN_METEO_BASE_URL` | `https://api.open-meteo.com` | Provider origin; adapter appends `/v1/forecast` |
| `OPEN_METEO_API_KEY` | empty | Omitted from request when empty; optional paid API key |
| `FORECAST_TIMEZONE` | `Asia/Jerusalem` | IANA timezone for daily boundaries and provider requests; must match planner |
| `PROVIDER_TIMEOUT_SECONDS` | `5` | Positive httpx timeout for each request phase, per attempt |
| `PROVIDER_RETRIES` | `2` | Additional attempts after the first (0–10 allowed) |
| `CACHE_FRESHNESS_SECONDS` | `10800` | Fresh for strictly less than 3 hours |
| `STALE_MAX_AGE_SECONDS` | `86400` | Maximum total age of stale data; at least the freshness interval |
| `RETRY_AFTER_SECONDS` | `60` | Positive `Retry-After` value on HTTP 503 |

The free endpoint needs no key. For paid Open-Meteo, set the appropriate customer
origin and API key; no code change is required. A provider with a different wire
format needs its own adapter. Timezone names require system IANA timezone data
(normally installed on macOS/Linux; install the OS `tzdata` package if absent).

## HTTP contract

```sh
curl 'http://127.0.0.1:8001/v1/forecast?lat=31.25&lon=34.79&days=2'
```

```json
{
  "lat": 31.25,
  "lon": 34.79,
  "source": "open-meteo",
  "fetched_at": "2026-11-19T06:00:00Z",
  "stale": false,
  "days": [
    {"date": "2026-11-19", "et0_mm": 3.1, "rain_mm": 0.0},
    {"date": "2026-11-20", "et0_mm": 2.8, "rain_mm": 4.2}
  ]
}
```

`lat` and `lon` echo the requested coordinates. They are required finite numbers
in inclusive ranges −90..90 and −180..180. `days` is an integer 1..7, default 7.
Dates start today in `FORECAST_TIMEZONE`. `fetched_at` is an aware UTC timestamp
recorded after a successful, validated provider fetch; serving stale data never
changes it. OpenAPI is at `/docs` and `/openapi.json`.

Invalid or missing query parameters return HTTP 422:

```json
{"code": "VALIDATION", "detail": "lat: -90..90; lon: -180..180; days: 1..7"}
```

An unusable provider response with no eligible cached forecast returns HTTP 503,
with `Retry-After: 60` by default:

```json
{"code": "UNAVAILABLE", "detail": "Open-Meteo forecast is unavailable"}
```

`GET /health` returns HTTP 200, `{"status":"ok"}`. This reports service liveness;
it does not call the provider or claim upstream availability.

## Daily variables and units

The [Open-Meteo daily parameter documentation](https://open-meteo.com/en/docs#daily-parameter-definition)
defines both selected variables in millimetres:

| Adapter field | Public field | Meaning |
| --- | --- | --- |
| `et0_fao_evapotranspiration` | `et0_mm` | Daily reference evapotranspiration for well-watered grass |
| `rain_sum` | `rain_mm` | Daily rain sum |

Rain is the provider's rain variable; it is not total precipitation, which also
includes showers and snowfall. The request explicitly selects millimetres,
seven forecast days, and the configured timezone. The adapter verifies reported
units. Provider field names stay within `provider.py` in production code.

## Cache and failure policy

The cache key is `(floor(lat × 10), floor(lon × 10))`, calculated using decimal
arithmetic so exact decimal boundaries remain stable. The provider is queried
at the southwest cell boundary: `31.21` and `31.29` share latitude `31.2`, while
`-0.01` and `-0.09` share `-0.1`. Exact maximum coordinates remain valid.
The request's original coordinates are still echoed in the public response.

Every fetch obtains and validates a full seven-day forecast even if the caller
asks for one day. Validation requires seven consecutive unique dates starting
today, equal-length arrays, millimetre units, and finite, nonnegative JSON
numbers for every value. Missing days, nulls, numeric strings, booleans, negative
depths, NaN and infinity invalidate the whole response. Zero is accepted only
when the provider actually supplied zero. No padding, interpolation, default
water values, or partial-success responses are used.

A cached forecast is fresh for less than 3 hours, provided it covers every
requested date. Concurrent refreshes for one cell share one in-flight fetch;
other cells fetch independently. A cancelled HTTP caller does not cancel that
shared fetch. The service closes pending work and its httpx client at shutdown.

Timeouts, network errors, error status codes, non-JSON bodies, and invalid daily
data receive two retries (three total attempts) by default. After failure, the
last good forecast is served with `stale: true` only if its total age is at most
24 hours **and** it covers all requested dates. Retries never overwrite good
data with bad data. An older forecast, a missing final day after midnight, or a
cell without prior data returns 503. Data that expires while retries run is
checked again before fallback.

The 24-hour cap permits a brief provider outage while limiting use of outdated
rain/ET0 in irrigation decisions. It is a total age limit, not 24 additional
hours after freshness. At local midnight a cached seven-day forecast may still
cover six requested days, but cannot answer a seven-day request without a new
fetch. The same timezone is used for the clock and provider; timestamps remain
UTC even when dates use Jerusalem time.

The cache is process-local and currently retains one last successful entry per
requested cell until restart. It is intended for a bounded set of plot locations;
arbitrary public coordinate traffic would need an eviction/size policy.

## Verification

```sh
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv lock --check --offline
```

The suite uses a real FastAPI application and httpx mock transport only at the
external provider boundary. It covers the schema, ranges, floor cells including
negative coordinates, seven-day caching, concurrent requests, freshness and
stale boundaries, retries and recovery, malformed/missing/nonfinite data, unit
mismatches, date coverage, and Jerusalem/UTC midnight disagreement. No live API
or `.env` secrets are needed for tests. Final local run: **59 tests passed**.

Reproducible NFR-2.3 benchmark over real loopback HTTP, not in-process ASGI timing:

```sh
uv run --frozen python benchmark.py --requests 100 --rps 10
# Optional: benchmark an existing live-provider server after warming its cache.
uv run --frozen python benchmark.py --url http://127.0.0.1:18001 --requests 100 --rps 10
```

The default benchmark starts separate uvicorn weather/provider processes on
temporary free loopback ports, disables their access logs, warms exactly once,
then schedules requests at 10/second. It validates every HTTP response and the
unchanged cached payload, verifies the provider saw only the warmup call, and
exits nonzero if p95 exceeds 100 ms or the provider is called during measurement.
Processes are cleaned up afterward. Live-server mode checks identical cached
responses but cannot independently instrument provider calls.

Measured 2026-11-19, macOS arm64, Python 3.12.11, 100 measured requests at 10 rps:

| Mode | p50 | p95 | Maximum | Provider calls during measurement |
| --- | --- | --- | --- | --- |
| Separate local provider + real weather HTTP | 2.523 ms | 7.555 ms | 36.455 ms | 0 (1 warmup) |
| Real Open-Meteo-backed service, warm cache | 3.477 ms | 6.385 ms | 17.463 ms | Not independently instrumented |

Both meet p95 ≤100 ms. These are local measurements, not a production guarantee.
The live smoke check also confirmed a seven-day Open-Meteo response starting on
the Jerusalem date, a shared cell's one-day/seven-day requests using the same
fetch timestamp, health, and invalid-coordinate handling.

Audit all locked runtime and development packages without resolving new versions:

```sh
uv export --locked --all-groups --no-emit-project --format requirements-txt |
  uv tool run pip-audit --no-deps --disable-pip -r /dev/stdin
```

The lock check succeeded and the 2026-11-19 audit reported **no known vulnerabilities**.
In restricted environments, prefix uv commands with
`UV_CACHE_DIR=/private/tmp/argopilot-weather-uv-cache`; local HTTP binding and
dependency/audit downloads may require network permission.
