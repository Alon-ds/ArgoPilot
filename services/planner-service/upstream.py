"""Validated registry/weather HTTP boundaries. Never substitute missing data."""

from datetime import date, timedelta
from math import isclose
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import BaseModel, ValidationError

from config import Settings
from models import Emitter, Forecast, Plot, Soil


class UpstreamUnavailable(Exception):
    def __init__(self, service: str):
        self.service = service


class PlotNotFound(Exception):
    pass


async def fetch[T: BaseModel](client: httpx.AsyncClient, base: str, path: str,
                              model: type[T], service: str, *, params=None,
                              plot_lookup=False) -> T:
    try:
        response = await client.get(base.rstrip("/") + path, params=params)
        if plot_lookup and response.status_code == 404:
            raise PlotNotFound
        response.raise_for_status()
        return model.model_validate(response.json())
    except (httpx.HTTPError, ValueError, ValidationError) as exc:
        raise UpstreamUnavailable(service) from exc


async def inputs(client: httpx.AsyncClient, settings: Settings, plot_id: UUID,
                 days: int, today: date) -> tuple[Plot, Soil, Emitter, Forecast]:
    registry = str(settings.registry_url)
    plot = await fetch(client, registry, f"/v1/plots/{plot_id}", Plot,
                       "registry-service", plot_lookup=True)
    if plot.id != plot_id or plot.planting_date > today:
        raise UpstreamUnavailable("registry-service")
    soil = await fetch(client, registry, f"/v1/soils/{quote(plot.soil_id, safe='')}",
                       Soil, "registry-service")
    emitter = await fetch(client, registry, f"/v1/emitters/{quote(plot.emitter_id, safe='')}",
                          Emitter, "registry-service")
    if soil.id != plot.soil_id or emitter.id != plot.emitter_id:
        raise UpstreamUnavailable("registry-service")
    forecast = await fetch(client, str(settings.weather_url), "/v1/forecast", Forecast,
                           "weather-service", params={"lat": plot.lat, "lon": plot.lon, "days": days})
    if not (isclose(forecast.lat, plot.lat, rel_tol=0, abs_tol=1e-7)
            and isclose(forecast.lon, plot.lon, rel_tol=0, abs_tol=1e-7)):
        raise UpstreamUnavailable("weather-service")
    expected = [today + timedelta(days=i) for i in range(days)]
    # Extra future days are harmless; missing, duplicate, reordered/old days are not.
    if [day.date for day in forecast.days[:days]] != expected:
        raise UpstreamUnavailable("weather-service")
    forecast = forecast.model_copy(update={"days": forecast.days[:days]})
    return plot, soil, emitter, forecast
