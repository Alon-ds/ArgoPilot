"""Provider-independent public HTTP schema."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DailyForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    et0_mm: float = Field(ge=0, allow_inf_nan=False)
    rain_mm: float = Field(ge=0, allow_inf_nan=False)


class Forecast(BaseModel):
    lat: float
    lon: float
    source: Literal["open-meteo"] = "open-meteo"
    fetched_at: datetime
    stale: bool
    days: list[DailyForecast]


class ErrorResponse(BaseModel):
    code: str
    detail: str
