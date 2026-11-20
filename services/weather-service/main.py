"""Run with uvicorn main:app --port 8001 --no-access-log."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import Settings
from forecast import ForecastService
from models import ErrorResponse, Forecast
from provider import OpenMeteo, ProviderUnavailable


def create_app(
    settings: Settings | None = None,
    provider_client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Fail on invalid configuration before accepting traffic.
        config = settings if settings is not None else Settings()
        client = provider_client if provider_client is not None else httpx.AsyncClient()
        app.state.settings = config
        app.state.forecasts = ForecastService(
            OpenMeteo(client, config),
            config,
            clock or (lambda: datetime.now(ZoneInfo(config.forecast_timezone))),
        )
        try:
            yield
        finally:
            await app.state.forecasts.close()
            if provider_client is None:
                await client.aclose()

    app = FastAPI(title="AgroPilot weather-service", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_query(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION", "detail": "lat: -90..90; lon: -180..180; days: 1..7"},
        )

    @app.exception_handler(ProviderUnavailable)
    async def unavailable(request: Request, exc: ProviderUnavailable):
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": str(request.app.state.settings.retry_after_seconds)},
            content={"code": "UNAVAILABLE", "detail": "Open-Meteo forecast is unavailable"},
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get(
        "/v1/forecast",
        response_model=Forecast,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def forecast(
        request: Request,
        lat: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)],
        lon: Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)],
        days: Annotated[int, Query(ge=1, le=7)] = 7,
    ):
        return await request.app.state.forecasts.get(lat, lon, days)

    return app


app = create_app()
