"""Planner API. Launch with uvicorn main:app --factory --port 8002."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import Settings
from engine import project
from models import Plan
from upstream import PlotNotFound, UpstreamUnavailable, inputs


def create_app(settings: Settings | None = None, *, transport=None,
               today: Callable[[], date] | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    clock = today or (lambda: datetime.now(ZoneInfo(settings.planner_timezone)).date())

    @asynccontextmanager
    async def lifespan(api):
        async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds,
                                     transport=transport) as client:
            api.state.client = client
            yield

    api = FastAPI(title="AgroPilot planner", lifespan=lifespan)

    @api.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(status_code=422, content={
            "code": "VALIDATION", "detail": "Invalid request parameters."})

    @api.exception_handler(PlotNotFound)
    async def plot_not_found(request, exc):
        return JSONResponse(status_code=404, content={
            "code": "NOT_FOUND", "detail": "Plot not found."})

    @api.exception_handler(UpstreamUnavailable)
    async def upstream_unavailable(request, exc):
        return JSONResponse(status_code=503, content={
            "code": "UPSTREAM_UNAVAILABLE",
            "detail": f"{exc.service} unavailable or returned invalid data."})

    @api.get("/health")
    async def health():
        return {"status": "ok"}

    @api.get("/v1/plots/{plot_id}/plan", response_model=Plan)
    async def plan(plot_id: UUID, days: int = Query(default=7, ge=1, le=7)):
        values = await inputs(api.state.client, settings, plot_id, days, clock())
        try:
            return project(*values)
        except (ValueError, ArithmeticError) as exc:
            # Even finite upstream values can overflow during arithmetic.
            raise UpstreamUnavailable("registry-service/weather-service calculation") from exc

    return api


def app():
    return create_app()
