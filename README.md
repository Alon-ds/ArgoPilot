# AgroPilot

AgroPilot helps a grower manage agricultural crops with modern AI. 


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

Assignment evidence and explanation:

- [Design](docs/p2-design.md) and [implementation plan](docs/p2-plan.md)
- [Verification evidence and remaining limitations](docs/p2-verification.md)
- [Hebrew walkthrough for explaining the work](docs/p2-walkthrough-he.md)
