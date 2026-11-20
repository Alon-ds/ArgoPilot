"""In-process cell cache, freshness, retry and safe stale fallback policy."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from zoneinfo import ZoneInfo

from config import Settings
from models import DailyForecast, Forecast
from provider import OpenMeteo, ProviderUnavailable

type Cell = tuple[int, int]


def cell_for(lat: float, lon: float) -> Cell:
    # Decimal prevents binary floating point from moving exact decimal cell boundaries.
    return tuple(
        int((Decimal(str(value)) * 10).to_integral_value(rounding=ROUND_FLOOR))
        for value in (lat, lon)
    )


@dataclass(frozen=True)
class CacheEntry:
    fetched_at: datetime
    days: tuple[DailyForecast, ...]


class ForecastService:
    def __init__(self, provider: OpenMeteo, settings: Settings, clock: Callable[[], datetime]):
        self.provider = provider
        self.settings = settings
        self.clock = clock
        self.timezone = ZoneInfo(settings.forecast_timezone)
        self.cache: dict[Cell, CacheEntry] = {}
        self.inflight: dict[Cell, asyncio.Task[CacheEntry]] = {}

    def _covered_days(self, entry: CacheEntry, count: int) -> list[DailyForecast]:
        today = self.clock().astimezone(self.timezone).date()
        by_date = {day.date: day for day in entry.days}
        dates = [today + timedelta(days=i) for i in range(count)]
        return [by_date[day] for day in dates] if all(day in by_date for day in dates) else []

    async def get(self, lat: float, lon: float, days: int) -> Forecast:
        cell = cell_for(lat, lon)
        entry = self.cache.get(cell)
        if entry is not None:
            age = (self.clock() - entry.fetched_at).total_seconds()
            if 0 <= age < self.settings.cache_freshness_seconds and self._covered_days(entry, days):
                return self._response(lat, lon, entry, days, stale=False)

        # One refresh per cell; other cells never wait behind this provider request.
        task = self.inflight.get(cell)
        if task is None:
            task = asyncio.create_task(self._refresh(cell))
            self.inflight[cell] = task
            task.add_done_callback(lambda finished: self._refresh_finished(cell, finished))
        try:
            entry = await asyncio.shield(task)
            return self._response(lat, lon, entry, days, stale=False)
        except ProviderUnavailable:
            entry = self.cache.get(cell)
            if entry is not None:
                age = (self.clock() - entry.fetched_at).total_seconds()
                if 0 <= age <= self.settings.stale_max_age_seconds and self._covered_days(
                    entry, days
                ):
                    return self._response(lat, lon, entry, days, stale=True)
            raise ProviderUnavailable("No usable forecast is available") from None

    def _refresh_finished(self, cell: Cell, task: asyncio.Task[CacheEntry]) -> None:
        self.inflight.pop(cell, None)
        if not task.cancelled():
            # Retrieve exceptions even when every waiting HTTP client has disconnected.
            task.exception()

    async def _refresh(self, cell: Cell) -> CacheEntry:
        for _ in range(self.settings.provider_retries + 1):
            try:
                today = self.clock().astimezone(self.timezone).date()
                days = await self.provider.fetch(cell[0] / 10, cell[1] / 10, today)
                entry = CacheEntry(fetched_at=self.clock().astimezone(UTC), days=days)
                # Refuse a response that crossed local midnight and lost today's full week.
                if len(self._covered_days(entry, 7)) != 7:
                    raise ProviderUnavailable("Forecast no longer covers the current week")
                self.cache[cell] = entry
                return entry
            except ProviderUnavailable:
                continue
        raise ProviderUnavailable("Open-Meteo failed after all attempts")

    def _response(self, lat: float, lon: float, entry: CacheEntry, count: int, *, stale: bool):
        days = self._covered_days(entry, count)
        if len(days) != count:
            raise ProviderUnavailable("Cached forecast does not cover the requested dates")
        return Forecast(lat=lat, lon=lon, fetched_at=entry.fetched_at, stale=stale, days=days)

    async def close(self) -> None:
        tasks = list(self.inflight.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
