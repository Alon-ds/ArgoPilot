"""Pure deterministic single-Kc projection. Policy is in irrigation-calc-reference."""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil, isclose

from models import Emitter, Forecast, Plan, PlanDay, Plot, Soil


@dataclass(frozen=True)
class Crop:
    initial: int
    development: int
    middle: int
    late: int
    kc_initial: float
    kc_middle: float
    kc_end: float
    root_m: float


CROPS = {
    "tomato": Crop(30, 40, 45, 30, .6, 1.15, .8, .7),
    "bell-pepper": Crop(30, 35, 40, 20, .6, 1.05, .9, .5),
}


def crop_kc(crop_id: str, age_days: int) -> float:
    crop = CROPS[crop_id]
    if age_days < 0:
        raise ValueError("Planting date is in the future")
    if age_days <= crop.initial:
        return crop.kc_initial
    development_end = crop.initial + crop.development
    if age_days < development_end:
        fraction = (age_days - crop.initial) / crop.development
        return crop.kc_initial + fraction * (crop.kc_middle - crop.kc_initial)
    middle_end = development_end + crop.middle
    if age_days <= middle_end:
        return crop.kc_middle
    fraction = min(1, (age_days - middle_end) / crop.late)
    return crop.kc_middle + fraction * (crop.kc_end - crop.kc_middle)


def project(plot: Plot, soil: Soil, emitter: Emitter, forecast: Forecast) -> Plan:
    capacity = soil.available_water_mm_per_m * CROPS[plot.crop_id].root_m
    bucket = capacity * plot.initial_soil_pct / 100
    # Exact decimal-rational hydraulic arithmetic avoids a spurious extra minute
    # at integral runtimes (e.g. binary float 3780.0000000000005).
    emitter_count = Fraction(str(plot.area_m2)) / (
        Fraction(str(plot.row_spacing_m)) * Fraction(str(plot.emitter_spacing_m))
    )
    result = []
    for day in forecast.days:
        kc = crop_kc(plot.crop_id, (day.date - plot.planting_date).days)
        projected = min(capacity, bucket + day.rain_mm - day.et0_mm * kc)
        # Tolerate floating point noise at the exact half-capacity boundary.
        irrigate = projected < capacity / 2 and not isclose(
            projected, capacity / 2, rel_tol=1e-12, abs_tol=1e-9
        )
        depth = capacity - projected if irrigate else 0.0
        litres = depth * plot.area_m2
        minutes = Fraction(str(litres)) / emitter_count / Fraction(str(emitter.flow_lph)) * 60
        runtime = ceil(minutes) if minutes else 0
        if litres > 0:
            runtime = max(1, runtime)
        bucket = capacity if irrigate else max(0, projected)
        result.append(PlanDay(date=day.date, et0_mm=day.et0_mm, kc=kc,
                              litres=litres, run_minutes=runtime,
                              stale=forecast.stale, bucket_mm=bucket,
                              bucket_pct=bucket / capacity * 100))
    return Plan(plot_id=plot.id, days=result)
