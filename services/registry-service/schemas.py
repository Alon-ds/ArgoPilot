"""Request validation and response models for the registry API."""

from datetime import date
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]

# Drip geometry decides how long the system must run to deliver a given depth,
# so an out-of-range spacing produces a runtime no grower can act on rather
# than a visible error: 11 m emitter spacing on a 1111 m2 plot yields 101
# emitters and a 28-day run for one day's refill. Bounds cover field drip
# (0.2-0.6 m emitters) through orchard laterals, and reject the rest.
# Only the request models are bounded. The response model keeps PositiveNumber
# so plots stored before this rule existed stay readable instead of failing
# their own GET.
EmitterSpacing = Annotated[float, Field(gt=0, le=2, allow_inf_nan=False)]
RowSpacing = Annotated[float, Field(gt=0, le=5, allow_inf_nan=False)]

# How full the soil-water bucket is assumed to be on day one, as a percent of
# field capacity. Lets a grower who knows the field is partly dry start the
# projection below full instead of the 100 default; a sensor feed would later
# replace this. 0 = empty (irrigate immediately), 100 = full.
SoilPercent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchModel(InputModel):
    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self


class FarmCreate(InputModel):
    name: Name


class FarmPatch(PatchModel):
    name: Name | None = None


class Farm(BaseModel):
    id: UUID
    name: Name


class PlantingDateModel(InputModel):
    @model_validator(mode="after")
    def reject_future_planting_date(self) -> Self:
        planting_date = getattr(self, "planting_date", None)
        if planting_date is not None and planting_date > date.today():
            raise ValueError("planting_date must not be in the future")
        return self


class PlotCreate(PlantingDateModel):
    farm_id: UUID
    name: Name
    area_m2: PositiveNumber
    crop_id: Name
    planting_date: date
    soil_id: Name
    row_spacing_m: RowSpacing
    emitter_spacing_m: EmitterSpacing
    emitter_id: Name
    lat: Latitude
    lon: Longitude
    initial_soil_pct: SoilPercent = 100


class PlotPatch(PatchModel, PlantingDateModel):
    farm_id: UUID | None = None
    name: Name | None = None
    area_m2: PositiveNumber | None = None
    crop_id: Name | None = None
    planting_date: date | None = None
    soil_id: Name | None = None
    row_spacing_m: RowSpacing | None = None
    emitter_spacing_m: EmitterSpacing | None = None
    emitter_id: Name | None = None
    lat: Latitude | None = None
    lon: Longitude | None = None


class Plot(BaseModel):
    id: UUID
    farm_id: UUID
    name: Name
    area_m2: PositiveNumber
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: PositiveNumber
    emitter_spacing_m: PositiveNumber
    emitter_id: str
    lat: Latitude
    lon: Longitude
    initial_soil_pct: SoilPercent


class Crop(BaseModel):
    id: str
    name: str


class Soil(BaseModel):
    id: str
    name: str
    available_water_mm_per_m: int


class Emitter(BaseModel):
    id: str
    name: str
    flow_lph: float
