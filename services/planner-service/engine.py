"""Pure deterministic multi-day projection. Policy is in irrigation-calc-reference."""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil, isclose

from models import Emitter, Forecast, IrrigationStatus, Plan, PlanDay, Plot, Soil

DEFAULT_MAX_DAILY_MINUTES = 1440  # 24 h; the caller may pass an operational ceiling


def _minutes(litres: float, emitter_count: Fraction, flow_lph: float) -> int:
    """Runtime to deliver `litres`, rounded up, via exact rational arithmetic."""
    if litres <= 0:
        return 0
    return ceil(Fraction(str(litres)) / emitter_count / Fraction(str(flow_lph)) * 60)


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

# Synthetic demo crop. It ignores weather ET0 and drains a fixed fraction of
# the current bucket per day, to make the irrigation trigger easy to see in a
# short forecast. It reports that drain as et0_mm with kc=1.0 so the displayed
# ET0 x Kc equals the actual soil change. root_m matches a tomato so the
# capacity is in the same ballpark as a real plot.
TEST_CROP_ID = "test"
TEST_DAILY_FRACTION = 0.15
TEST_ROOT_M = 0.7


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


def project(plot: Plot, soil: Soil, emitter: Emitter, forecast: Forecast,
            max_daily_minutes: int = DEFAULT_MAX_DAILY_MINUTES) -> Plan:
    """Project a multi-day irrigation plan.

    A drip system runs at most `max_daily_minutes` a day, so a refill that needs
    more is split: each day delivers what fits, the bucket rises only by the
    water actually scheduled, and the deficit carries into the next day while
    rain and crop use keep changing the balance. An irrigation cycle starts when
    the bucket drops below half capacity and continues (even above half) until
    the bucket is full again.
    """
    is_test = plot.crop_id == TEST_CROP_ID
    root_m = TEST_ROOT_M if is_test else CROPS[plot.crop_id].root_m
    capacity = soil.available_water_mm_per_m * root_m
    threshold = capacity / 2
    bucket = capacity * plot.initial_soil_pct / 100
    # Exact decimal-rational hydraulic arithmetic avoids a spurious extra minute
    # at integral runtimes (e.g. binary float 3780.0000000000005).
    area = Fraction(str(plot.area_m2))
    emitter_count = area / (
        Fraction(str(plot.row_spacing_m)) * Fraction(str(plot.emitter_spacing_m))
    )
    total_flow_lph = emitter_count * Fraction(str(emitter.flow_lph))  # litres/hour
    daily_capacity_f = total_flow_lph * max_daily_minutes / 60        # litres/day the drip can deliver
    daily_capacity_litres = float(daily_capacity_f)
    irrigation_active = False
    result = []
    for day in forecast.days:
        if is_test:
            # Drain a fixed fraction of the current bucket. Report that drain as
            # et0_mm with kc=1 so the displayed ET0 x Kc matches the soil change.
            et0_mm, kc = bucket * TEST_DAILY_FRACTION, 1.0
        else:
            et0_mm = day.et0_mm
            kc = crop_kc(plot.crop_id, (day.date - plot.planting_date).days)
        etc = et0_mm * kc
        bucket_before = bucket
        # Daily balance, clamped: soil cannot exceed capacity nor fall below 0.
        projected = min(capacity, max(0.0, bucket + day.rain_mm - etc))
        # A new cycle starts strictly below half capacity; an active one keeps
        # going until the bucket is full, even if rain lifts it back above half.
        started = projected < threshold and not isclose(
            projected, threshold, rel_tol=1e-12, abs_tol=1e-9)
        prev_active = irrigation_active  # was a cycle already running yesterday?
        active = irrigation_active or started

        required_litres = scheduled_litres = remaining_litres = 0.0
        completed = False
        if active:
            required_litres = max(0.0, capacity - projected) * plot.area_m2
            capped = Fraction(str(required_litres)) > daily_capacity_f
            if capped:
                scheduled_litres = daily_capacity_litres
                scheduled_minutes = max_daily_minutes
            else:
                scheduled_litres = required_litres
                scheduled_minutes = _minutes(scheduled_litres, emitter_count, emitter.flow_lph)
            bucket = min(capacity, projected + scheduled_litres / plot.area_m2)
            remaining_litres = max(0.0, (capacity - bucket) * plot.area_m2)
            completed = isclose(remaining_litres, 0.0, abs_tol=1e-6)
            irrigation_active = not completed
        else:
            bucket = projected
            scheduled_minutes = 0
            irrigation_active = False

        if scheduled_litres > 0:
            scheduled_minutes = max(1, scheduled_minutes)
        # Hydraulic capacity warning: a full day of pumping cannot even match the
        # crop's own daily use, so the bucket can never recover under these inputs.
        capacity_warning = active and not completed and daily_capacity_litres <= etc * plot.area_m2
        if not active:
            status = IrrigationStatus.NOT_REQUIRED
        elif completed:
            status = IrrigationStatus.COMPLETED
        elif prev_active:
            status = IrrigationStatus.CONTINUING  # an earlier cycle still has water to deliver
        else:
            status = IrrigationStatus.SCHEDULED   # a new cycle opens today

        result.append(PlanDay(
            date=day.date, et0_mm=et0_mm, kc=kc,
            litres=scheduled_litres, run_minutes=scheduled_minutes, stale=forecast.stale,
            bucket_before_mm=bucket_before, bucket_mm=bucket, bucket_pct=bucket / capacity * 100,
            required_litres=required_litres,
            required_run_minutes=_minutes(required_litres, emitter_count, emitter.flow_lph),
            remaining_litres=remaining_litres,
            remaining_run_minutes=_minutes(remaining_litres, emitter_count, emitter.flow_lph),
            irrigation_in_progress=irrigation_active, irrigation_status=status,
            capacity_warning=capacity_warning))
    return Plan(plot_id=plot.id, days=result)
