# AgroPilot

AgroPilot is a full-stack irrigation planning system for agricultural plots.
It combines a registry of farms and plots, validated weather forecasts, a
deterministic FAO-56-based irrigation planner, and a server-rendered web UI.

The project was built as a service-oriented application: each backend service
has a clear responsibility and communicates with the others over HTTP. The
frontend never exposes internal service URLs to the browser.

## Project links

- Repository: <https://github.com/Alon-ds/ArgoPilot>
- GitHub Actions: <https://github.com/Alon-ds/ArgoPilot/actions>
- Assignment documentation: [P2 verification](docs/p2-verification.md)
- Hebrew explanation for presentation: [P2 walkthrough](docs/p2-walkthrough-he.md)

There is currently no public production deployment configured for this
repository. The website is available locally at
<http://localhost:3000> after starting the frontend and its backend services.

## What the system does

1. The **Registry service** stores farms, plots, soils, crops, and emitters.
2. The **Weather service** retrieves and validates Open-Meteo forecasts and
   caches them for a short period.
3. The **Planner service** combines plot data and weather data to calculate a
   seven-day irrigation plan using deterministic FAO-56 water-balance logic.
4. The **Frontend** displays farms, plots, today's recommendation, the
   seven-day plan, stale-data warnings, and dependency health.

The planner intentionally starts each request with a full soil-water bucket.
This is an explicit simulation assumption: it does not claim to measure real
soil moisture and does not persist irrigation history.

## Where to start

Services live under `services/`. P2 adds independent weather, irrigation planning,
and frontend services to the registry. Python services communicate over HTTP.

```bash
cd services/registry-service
uv sync
cp .env.example .env
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/health. A running service returns `{"status": "ok"}`.

For the complete web experience, start all four services and then open
<http://localhost:3000>:

```bash
# Terminal 1
cd services/registry-service
uv sync
cp .env.example .env
uv run python -m seed
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd services/weather-service
uv sync
cp .env.example .env
uv run uvicorn main:app --host 127.0.0.1 --port 8001

# Terminal 3
cd services/planner-service
uv sync
cp .env.example .env
uv run uvicorn main:app --host 127.0.0.1 --port 8002

# Terminal 4
cd services/frontend
npm ci
cp .env.example .env.local
npm run dev
```

The frontend reads `REGISTRY_URL`, `WEATHER_URL`, and `PLANNER_URL` from
`services/frontend/.env.local`. The backend URLs are server-side settings and
are not sent to the browser.

## P2 services

| Service | Port | Purpose | Setup |
| --- | --- | --- | --- |
| Registry | 8000 | Plots and catalogs; SQLite/PostgreSQL | [README](services/registry-service/README.md) |
| Weather | 8001 | Validated Open-Meteo forecasts and cache | [README](services/weather-service/README.md) |
| Planner | 8002 | Deterministic daily irrigation projection | [README](services/planner-service/README.md) |
| Frontend | 3000 | Farm list and daily plan | [README](services/frontend/README.md) |

Run each in its own terminal and virtual environment. Copy each service's
`.env.example` to its local environment file as described by its README; never
commit secrets. Planner requires REGISTRY_URL and WEATHER_URL; the frontend also
requires PLANNER_URL. Its server makes the backend calls.

The planner starts with a full soil bucket as an explicit simulation assumption;
it does not measure actual soil moisture or remember real irrigation history.

## Quality and security checks

The repository is checked automatically by GitHub Actions:

- Python 3.12 and 3.13 test matrices
- Registry line and branch coverage enforced at 100%
- Weather and planner unit/integration tests
- PostgreSQL contract test and seed verification
- Frontend lint, production build, accessibility-oriented browser tests, and
  mobile viewport coverage at 375 × 667
- Dependency audit with `uv audit --locked --preview-features audit-command`
- Coverage HTML reports uploaded as CI artifacts

Run the main checks locally with:

```bash
cd services/registry-service && uv run pytest --cov=. --cov-branch
cd ../weather-service && uv run pytest
cd ../planner-service && uv run pytest
cd ../frontend && npm run lint && npm run build && npm test
```

For service-specific configuration, API examples, and troubleshooting, see
the README file inside each `services/*` directory.

Assignment evidence and explanation:

- [Design](docs/p2-design.md) and [implementation plan](docs/p2-plan.md)
- [Verification evidence and remaining limitations](docs/p2-verification.md)
- [Hebrew walkthrough for explaining the work](docs/p2-walkthrough-he.md)
