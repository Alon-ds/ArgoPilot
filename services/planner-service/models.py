"""Local HTTP contracts; no imports from other services."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Plot(BaseModel):
    id: UUID
    crop_id: Literal["tomato", "bell-pepper"]
    planting_date: date
    soil_id: str = Field(min_length=1)
    emitter_id: str = Field(min_length=1)
    area_m2: Positive
    row_spacing_m: Positive
    emitter_spacing_m: Positive
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)


class Soil(BaseModel):
    id: str = Field(min_length=1)
    available_water_mm_per_m: Positive


class Emitter(BaseModel):
    id: str = Field(min_length=1)
    flow_lph: Positive


class ForecastDay(BaseModel):
    date: date
    et0_mm: Nonnegative
    rain_mm: Nonnegative


class Forecast(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)
    stale: StrictBool
    days: list[ForecastDay]


class PlanDay(BaseModel):
    date: date
    et0_mm: Nonnegative
    kc: Positive
    litres: Nonnegative
    run_minutes: int = Field(ge=0)
    stale: bool
    bucket_mm: Nonnegative


class Plan(BaseModel):
    plot_id: UUID
    days: list[PlanDay]
