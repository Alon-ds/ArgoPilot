"""Local HTTP contracts; no imports from other services."""

from datetime import date
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class IrrigationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"  # bucket stayed above the half-capacity trigger
    SCHEDULED = "SCHEDULED"        # a new irrigation cycle starts this day
    CONTINUING = "CONTINUING"      # an earlier cycle still has water to deliver
    COMPLETED = "COMPLETED"        # the cycle reached capacity on this day


class Plot(BaseModel):
    id: UUID
    crop_id: Literal["tomato", "bell-pepper", "test"]
    planting_date: date
    soil_id: str = Field(min_length=1)
    emitter_id: str = Field(min_length=1)
    area_m2: Positive
    row_spacing_m: Positive
    emitter_spacing_m: Positive
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)
    # Assumed day-one soil-water level as a percent of field capacity. Defaults
    # to a full bucket when an older registry omits it.
    initial_soil_pct: float = Field(ge=0, le=100, default=100, allow_inf_nan=False)


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
    # litres / run_minutes are what is SCHEDULED for this day (capped by the
    # daily runtime limit), not the full cycle demand. The *_required fields
    # hold the full demand and the *_remaining fields what is still unmet.
    litres: Nonnegative
    run_minutes: int = Field(ge=0)
    stale: bool
    bucket_before_mm: Nonnegative  # soil water at the start of the day, before irrigation
    bucket_mm: Nonnegative         # soil water at the end of the day
    bucket_pct: Nonnegative        # bucket_mm as a percent of field capacity (0-100)
    required_litres: Nonnegative
    required_run_minutes: int = Field(ge=0)
    remaining_litres: Nonnegative
    remaining_run_minutes: int = Field(ge=0)
    irrigation_in_progress: bool   # an unfinished cycle carries into the next day
    irrigation_status: IrrigationStatus
    capacity_warning: bool         # the system cannot outpace the crop's daily demand


class Plan(BaseModel):
    plot_id: UUID
    days: list[PlanDay]
