"""The only module that understands Open-Meteo's request and response fields."""

import math
from datetime import date, timedelta

import httpx

from config import Settings
from models import DailyForecast


class ProviderUnavailable(Exception):
    """No complete, trustworthy provider forecast is available."""


class OpenMeteo:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client = client
        self.settings = settings

    async def fetch(self, lat: float, lon: float, today: date) -> tuple[DailyForecast, ...]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "et0_fao_evapotranspiration,rain_sum",
            "forecast_days": 7,
            "timezone": self.settings.forecast_timezone,
            "precipitation_unit": "mm",
        }
        if key := self.settings.open_meteo_api_key.get_secret_value():
            params["apikey"] = key
        try:
            response = await self.client.get(
                f"{str(self.settings.open_meteo_base_url).rstrip('/')}/v1/forecast",
                params=params,
                timeout=self.settings.provider_timeout_seconds,
            )
            response.raise_for_status()
            return self._parse(response.json(), today)
        except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError) as exc:
            # Never expose response bodies, request URLs, or the optional API key.
            raise ProviderUnavailable("Open-Meteo did not return a complete forecast") from exc

    @staticmethod
    def _parse(body: object, today: date) -> tuple[DailyForecast, ...]:
        if not isinstance(body, dict):
            raise ValueError("Expected JSON object")
        daily = body["daily"]
        units = body["daily_units"]
        if not isinstance(daily, dict) or not isinstance(units, dict):
            raise ValueError("Missing daily data or units")
        if any(units.get(field) != "mm" for field in ("et0_fao_evapotranspiration", "rain_sum")):
            raise ValueError("Daily depths must be millimetres")
        dates = daily["time"]
        et0 = daily["et0_fao_evapotranspiration"]
        rain = daily["rain_sum"]
        if not all(isinstance(values, list) and len(values) == 7 for values in (dates, et0, rain)):
            raise ValueError("All seven days must be present")
        expected = [today + timedelta(days=i) for i in range(7)]
        if dates != [day.isoformat() for day in expected]:
            raise ValueError("Expected seven ordered, unique dates starting today")
        for value in (*et0, *rain):
            # bool is an int subclass; strings and null must never be coerced to water depths.
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid daily depth")
        return tuple(
            DailyForecast(date=day, et0_mm=evaporation, rain_mm=precipitation)
            for day, evaporation, precipitation in zip(expected, et0, rain, strict=True)
        )
