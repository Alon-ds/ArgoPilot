from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import models
from config import Settings
from engine import crop_kc, project
from main import create_app

TODAY = date(2026, 11, 19)
PLOT_ID = "12345678-1234-1234-1234-123456789012"


def _project(weather, *, pct=100, crop="tomato", soil_mm=100, area=1000,
             row=1.5, emitter=0.4, flow=1.0, max_daily=1440, age=80):
    """Run the real engine directly for deterministic multi-day scenarios."""
    plot = models.Plot(id=PLOT_ID, crop_id=crop, planting_date=str(TODAY - timedelta(days=age)),
                       soil_id="s", emitter_id="e", area_m2=area, row_spacing_m=row,
                       emitter_spacing_m=emitter, lat=31.25, lon=34.79, initial_soil_pct=pct)
    forecast = models.Forecast(lat=31.25, lon=34.79, stale=False,
                               days=[models.ForecastDay(**d) for d in weather])
    plan = project(plot, models.Soil(id="s", available_water_mm_per_m=soil_mm),
                   models.Emitter(id="e", flow_lph=flow), forecast, max_daily_minutes=max_daily)
    return [day.model_dump(mode="json") for day in plan.days]


@pytest.fixture
def upstream():
    return {
        "plot": {"id": PLOT_ID, "crop_id": "tomato", "planting_date": "2026-08-01",
                 "soil_id": "sand", "emitter_id": "drip", "area_m2": 1000,
                 "row_spacing_m": 1.5, "emitter_spacing_m": 0.4, "lat": 31.25, "lon": 34.79},
        "soil": {"id": "sand", "available_water_mm_per_m": 100},
        "emitter": {"id": "drip", "flow_lph": 1},
        "weather": {"lat": 31.25, "lon": 34.79, "stale": False,
                    "days": [{"date": str(TODAY + timedelta(days=i)),
                              "et0_mm": 7 / 1.15, "rain_mm": 0} for i in range(7)]},
    }


def client_for(upstream, failure=None):
    calls = []

    def handle(request):
        calls.append(request)
        assert request.extensions["timeout"]["read"] == 2
        path = request.url.path
        kind = ("weather" if path == "/v1/forecast" else "soil" if "/soils/" in path
                else "emitter" if "/emitters/" in path else "plot")
        if failure and failure[0] == kind:
            mode = failure[1]
            if mode == "timeout":
                raise httpx.ReadTimeout("test", request=request)
            if mode == "connect":
                raise httpx.ConnectError("test", request=request)
            if mode == "json":
                return httpx.Response(200, text="broken")
            return httpx.Response(mode, json={})
        return httpx.Response(200, json=upstream[kind])

    settings = Settings(_env_file=None, registry_url="http://registry",
                        weather_url="http://weather", upstream_timeout_seconds=2)
    app = create_app(settings, transport=httpx.MockTransport(handle), today=lambda: TODAY)
    return TestClient(app), calls


@pytest.mark.parametrize("crop,age,expected", [
    ("tomato", 0, .6), ("tomato", 30, .6), ("tomato", 50, .875),
    ("tomato", 70, 1.15), ("tomato", 115, 1.15),
    ("tomato", 130, .975), ("tomato", 145, .8), ("tomato", 500, .8),
    ("bell-pepper", 30, .6), ("bell-pepper", 47, .6 + .45 * 17 / 35),
    ("bell-pepper", 65, 1.05), ("bell-pepper", 105, 1.05),
    ("bell-pepper", 115, .975), ("bell-pepper", 125, .9), ("bell-pepper", 500, .9),
])
def test_crop_curve(crop, age, expected):
    assert crop_kc(crop, age) == pytest.approx(expected)


def test_bucket_threshold_refill_and_http_contract(upstream):
    # Keep all seven days mid-season.
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))
    client, calls = client_for(upstream)
    with client:
        response = client.get(f"/v1/plots/{PLOT_ID}/plan")
        assert response.status_code == 200
        data = response.json()
        assert data["plot_id"] == PLOT_ID
        days = data["days"]
        # Day 6 needs a 42 mm (42000 L) refill, but 1666.7 emitters x 1 L/h can
        # pump at most 40000 L in a 24 h day, so it is scheduled for 1440 min and
        # the bucket reaches only 68 mm. The 2000 L deficit carries to day 7,
        # which finishes the cycle in 324 min and reaches capacity.
        assert [d["bucket_mm"] for d in days] == pytest.approx([63, 56, 49, 42, 35, 68, 70])
        assert [d["run_minutes"] for d in days] == [0, 0, 0, 0, 0, 1440, 324]
        assert [d["litres"] for d in days] == pytest.approx([0, 0, 0, 0, 0, 40000, 9000])
        assert [d["required_litres"] for d in days] == pytest.approx([0, 0, 0, 0, 0, 42000, 9000])
        assert [d["remaining_litres"] for d in days] == pytest.approx([0, 0, 0, 0, 0, 2000, 0])
        assert [d["irrigation_status"] for d in days] == [
            "NOT_REQUIRED", "NOT_REQUIRED", "NOT_REQUIRED", "NOT_REQUIRED",
            "NOT_REQUIRED", "SCHEDULED", "COMPLETED"]
        assert days[5]["irrigation_in_progress"] is True   # carries into day 7
        assert days[6]["irrigation_in_progress"] is False  # cycle finished
        assert set(days[0]) == {
            "date", "et0_mm", "kc", "litres", "run_minutes", "stale",
            "bucket_before_mm", "bucket_mm", "bucket_pct",
            "required_litres", "required_run_minutes", "remaining_litres",
            "remaining_run_minutes", "irrigation_in_progress", "irrigation_status",
            "capacity_warning"}
        # Soil as a percent of field capacity (70 mm): 63 mm -> 90 %, partial -> 97 %, full -> 100 %.
        assert [d["bucket_pct"] for d in days] == pytest.approx([90, 80, 70, 60, 50, 97.142857, 100])
        assert client.get(f"/v1/plots/{PLOT_ID}/plan").json() == data
    forecast = next(r for r in calls if r.url.path == "/v1/forecast")
    assert dict(forecast.url.params) == {"lat": "31.25", "lon": "34.79", "days": "7"}
    assert {r.url.path for r in calls} == {f"/v1/plots/{PLOT_ID}", "/v1/soils/sand", "/v1/emitters/drip", "/v1/forecast"}


def test_initial_soil_pct_starts_bucket_below_full_then_finishes_next_day(upstream):
    # capacity = 100 mm/m * 0.7 m = 70 mm, threshold 35 mm. A 40% start (28 mm)
    # already sits below threshold, so day one opens the cycle. The 49 mm refill
    # (49000 L) exceeds one day's 40000 L, so day one is capped (1440 min, bucket
    # 61) and the 9000 L deficit finishes on day two in 576 min.
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))  # mid-season, Kc 1.15
    upstream["plot"]["initial_soil_pct"] = 40
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan").json()["days"]
    assert days[0]["required_litres"] == pytest.approx(49000)
    assert days[0]["litres"] == pytest.approx(40000)   # capped at one day's pumping
    assert days[0]["run_minutes"] == 1440
    assert days[0]["bucket_mm"] == pytest.approx(61)   # partial refill
    assert days[0]["remaining_litres"] == pytest.approx(9000)
    assert days[0]["irrigation_status"] == "SCHEDULED"
    assert days[1]["litres"] == pytest.approx(16000)   # finishes the 9000 L plus day-2 use
    assert days[1]["run_minutes"] == 576
    assert days[1]["bucket_mm"] == pytest.approx(70)   # reaches capacity
    assert days[1]["irrigation_status"] == "COMPLETED"


def test_initial_soil_pct_defaults_to_full_when_registry_omits_it(upstream):
    # An older registry that never sends the field must keep the full-bucket
    # behavior: no key in the plot payload, no irrigation in a dry winter week.
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))
    assert "initial_soil_pct" not in upstream["plot"]
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan").json()["days"]
    assert days[0]["bucket_mm"] == pytest.approx(63)  # 70 full - 7 ETc, not refilled


def test_test_crop_drains_fifteen_percent_per_day_regardless_of_weather(upstream):
    # The synthetic 'test' crop depletes 15 % of the current bucket each day and
    # ignores weather ET0: the sequence is deterministic. With a full start
    # (70 mm capacity) each day keeps 85 %: 59.5, 50.575, 42.99, 36.54, and then
    # 31.06 would land below the 35 mm trigger, so day 5 irrigates and refills.
    # It reports the drain as et0_mm with kc=1 so ET0 x Kc equals the soil drop.
    upstream["plot"]["crop_id"] = "test"
    upstream["weather"]["days"] = [
        {"date": str(TODAY + timedelta(days=i)), "et0_mm": 50, "rain_mm": 0}
        for i in range(7)
    ]
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan").json()["days"]
    assert [d["bucket_mm"] for d in days[:4]] == pytest.approx([59.5, 50.575, 42.98875, 36.5404375])
    assert days[4]["litres"] > 0  # fifth day crosses the half-capacity trigger
    assert days[4]["bucket_mm"] == pytest.approx(70)  # and refills to full
    assert days[0]["kc"] == 1.0  # synthetic crop reports a unit coefficient
    assert days[0]["et0_mm"] == pytest.approx(10.5)  # 15 % of the 70 mm full bucket
    assert days[0]["et0_mm"] * days[0]["kc"] == pytest.approx(70 - days[0]["bucket_mm"])


def test_rain_saturation_stale_and_runtime_ceiling(upstream):
    upstream["weather"]["stale"] = True
    upstream["weather"]["days"][0].update(et0_mm=200, rain_mm=300)
    upstream["weather"]["days"][1].update(et0_mm=40, rain_mm=0)
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan?days=2").json()["days"]
    # Daily net balance: min(C, B + rain - ETc), then trigger/refill.
    assert days[0]["bucket_mm"] == 70
    assert days[0]["run_minutes"] == 0
    # Day 2 demand is 46 mm (46000 L), above one day's 40000 L ceiling, so it is
    # scheduled for the full 1440 min and 6000 L remain for the next day.
    assert days[1]["required_litres"] == pytest.approx(46000)
    assert days[1]["litres"] == pytest.approx(40000)
    assert days[1]["run_minutes"] == 1440
    assert days[1]["remaining_litres"] == pytest.approx(6000)
    assert all(d["stale"] for d in days)


def test_pepper_root_depth_and_demand_bounded_by_capacity(upstream):
    # Bell pepper, root 0.5 m, soil 100 mm/m -> capacity 50 mm. A 100 mm ET0 day
    # (ETc 105 mm) would drive the raw balance to -55 mm, but the daily balance
    # is clamped to 0, so the demand is bounded by capacity (50 mm = 50000 L),
    # not the old 105000 L. A full 24 h day delivers only 40000 L, so the bucket
    # reaches 40 mm and the hydraulic-capacity warning fires (the system cannot
    # match the crop's own daily use).
    upstream["plot"].update(crop_id="bell-pepper", planting_date=str(TODAY - timedelta(days=80)))
    upstream["weather"]["days"][0]["et0_mm"] = 100
    client, _ = client_for(upstream)
    with client:
        day = client.get(f"/v1/plots/{PLOT_ID}/plan?days=1").json()["days"][0]
    assert day["required_litres"] == 50000     # bounded by capacity, not 105000
    assert day["litres"] == 40000              # one day's hydraulic ceiling
    assert day["run_minutes"] == 1440
    assert day["bucket_mm"] == 40
    assert day["remaining_litres"] == 10000
    assert day["capacity_warning"] is True


@pytest.mark.parametrize("days", ["0", "8", "-1", "abc", "1.5"])
def test_invalid_days(upstream, days):
    client, calls = client_for(upstream)
    with client:
        response = client.get(f"/v1/plots/{PLOT_ID}/plan?days={days}")
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"
    assert not calls


@pytest.mark.parametrize("kind", ["plot", "soil", "emitter", "weather"])
@pytest.mark.parametrize("mode", ["timeout", "connect", "json", 500, 404])
def test_upstream_failures_never_become_zero_plans(upstream, kind, mode):
    client, _ = client_for(upstream, (kind, mode))
    with client:
        response = client.get(f"/v1/plots/{PLOT_ID}/plan")
    if kind == "plot" and mode == 404:
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
    else:
        assert response.status_code == 503
        assert response.json()["code"] == "UPSTREAM_UNAVAILABLE"
        assert ("weather-service" if kind == "weather" else "registry-service") in response.json()["detail"]
    assert "days" not in response.json()


@pytest.mark.parametrize("kind,field,value", [
    ("plot", "area_m2", 0), ("plot", "emitter_spacing_m", -1),
    ("plot", "crop_id", "unknown"), ("plot", "planting_date", "2099-01-01"),
    ("soil", "available_water_mm_per_m", None), ("emitter", "flow_lph", 0),
    ("weather", "stale", None), ("weather", "days", []),
])
def test_invalid_upstream_payload(upstream, kind, field, value):
    upstream[kind][field] = value
    client, _ = client_for(upstream)
    with client:
        response = client.get(f"/v1/plots/{PLOT_ID}/plan")
    assert response.status_code == 503
    assert response.json()["code"] == "UPSTREAM_UNAVAILABLE"


@pytest.mark.parametrize("mutation", ["missing", "negative", "duplicate", "old", "nan"])
def test_forecast_integrity(upstream, mutation):
    days = upstream["weather"]["days"]
    if mutation == "missing":
        del days[0]["rain_mm"]
    elif mutation == "negative":
        days[0]["et0_mm"] = -1
    elif mutation == "duplicate":
        days[1]["date"] = days[0]["date"]
    elif mutation == "old":
        days[0]["date"] = "2020-01-01"
    else:
        days[0]["et0_mm"] = "NaN"
    client, _ = client_for(upstream)
    with client:
        response = client.get(f"/v1/plots/{PLOT_ID}/plan")
    assert response.status_code == 503
    assert "weather-service" in response.json()["detail"]


def test_health_and_configuration(upstream, monkeypatch):
    client, _ = client_for(upstream)
    with client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/v1/plots/invalid/plan").status_code == 422
    monkeypatch.delenv("REGISTRY_URL", raising=False)
    monkeypatch.delenv("WEATHER_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, registry_url="bad", weather_url="http://weather")


@pytest.mark.parametrize("kind,field,value", [
    ("soil", "id", "wrong"), ("emitter", "id", "wrong"),
    ("weather", "lat", 32), ("weather", "lon", 35),
])
@pytest.mark.parametrize("missing", [False, True])
def test_upstream_identity_and_coordinates(upstream, kind, field, value, missing):
    if missing:
        del upstream[kind][field]
    else:
        upstream[kind][field] = value
    client, _ = client_for(upstream)
    with client:
        response = client.get(f"/v1/plots/{PLOT_ID}/plan")
    assert response.status_code == 503
    assert ("weather-service" if kind == "weather" else "registry-service") in response.json()["detail"]


def test_reference_hand_examples(upstream):
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))
    for day in upstream["weather"]["days"]:
        day["et0_mm"] = 6
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan").json()["days"]
    # Day 6's 41400 L refill exceeds one 24 h day (40000 L), so it is scheduled
    # for 1440 min to 68.6 mm and day 7 finishes the 1400 L remainder in 299 min.
    assert [d["bucket_mm"] for d in days[:6]] == pytest.approx([63.1, 56.2, 49.3, 42.4, 35.5, 68.6])
    assert days[5]["required_litres"] == pytest.approx(41400)
    assert days[5]["litres"] == pytest.approx(40000)
    assert days[5]["run_minutes"] == 1440
    assert days[6]["bucket_mm"] == pytest.approx(70)
    assert days[6]["run_minutes"] == 299
    assert days[6]["irrigation_status"] == "COMPLETED"

    upstream["weather"]["days"][0]["rain_mm"] = 100
    client, _ = client_for(upstream)
    with client:
        day = client.get(f"/v1/plots/{PLOT_ID}/plan?days=1").json()["days"][0]
    assert day["bucket_mm"] == 70
    assert day["litres"] == day["run_minutes"] == 0

    upstream["plot"].update(crop_id="bell-pepper", area_m2=100, row_spacing_m=1,
                            emitter_spacing_m=.5, planting_date=str(TODAY - timedelta(days=47)))
    upstream["soil"]["available_water_mm_per_m"] = 10
    upstream["emitter"]["flow_lph"] = 2
    upstream["weather"]["days"][0].update(et0_mm=4, rain_mm=0)
    client, _ = client_for(upstream)
    with client:
        day = client.get(f"/v1/plots/{PLOT_ID}/plan?days=1").json()["days"][0]
    assert day["kc"] == pytest.approx(.818571428571)
    assert day["litres"] == pytest.approx(327.428571428)
    assert day["run_minutes"] == 50
    assert day["bucket_mm"] == 5


def test_bad_timezone_and_future_crop():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, registry_url="http://registry", weather_url="http://weather",
                 planner_timezone="invalid/timezone")
    with pytest.raises(ValueError):
        crop_kc("tomato", -1)


# --- Multi-day scheduling edge cases (regression guards, see §16 of the spec) ---

def test_cycle_latch_continues_above_half_threshold():
    # A cycle that opens below 50% keeps irrigating on a later day whose bucket
    # is already back above 50% — the half threshold starts a cycle, it does not
    # end one. Low ET0 so day two sits well above the 35 mm threshold.
    days = _project([{"date": str(TODAY + timedelta(days=i)), "et0_mm": 1, "rain_mm": 0}
                     for i in range(2)], pct=40)
    assert days[0]["bucket_before_mm"] < 35 and days[0]["irrigation_status"] == "SCHEDULED"
    assert days[1]["bucket_before_mm"] > 35          # above the trigger
    assert days[1]["litres"] > 0                      # yet still irrigating
    assert days[1]["irrigation_status"] in {"CONTINUING", "COMPLETED"}


def test_rain_fills_bucket_and_closes_the_cycle():
    days = _project([{"date": str(TODAY), "et0_mm": 7 / 1.15, "rain_mm": 0},
                     {"date": str(TODAY + timedelta(days=1)), "et0_mm": 7 / 1.15, "rain_mm": 200}], pct=40)
    assert days[1]["litres"] == 0                      # rain did the work
    assert days[1]["bucket_mm"] == pytest.approx(70)
    assert days[1]["irrigation_status"] == "COMPLETED"
    assert days[1]["irrigation_in_progress"] is False


def test_exactly_one_day_of_demand_is_not_capped():
    # required == daily capacity (40000 L): scheduled in full, 1440 min, complete.
    day = _project([{"date": str(TODAY), "et0_mm": 40 / 1.15, "rain_mm": 0}])[0]
    assert day["required_litres"] == pytest.approx(40000)
    assert day["litres"] == pytest.approx(40000)
    assert day["run_minutes"] == 1440
    assert day["bucket_mm"] == pytest.approx(70)
    assert day["irrigation_status"] == "COMPLETED"


def test_configurable_daily_limit_halves_delivery():
    # A 720 min (12 h) ceiling delivers half of a full day: 20000 L, bucket +20.
    day = _project([{"date": str(TODAY), "et0_mm": 7 / 1.15, "rain_mm": 0}], pct=40, max_daily=720)[0]
    assert day["run_minutes"] == 720
    assert day["litres"] == pytest.approx(20000)
    assert day["bucket_mm"] == pytest.approx(41)


def test_heavy_rain_never_exceeds_capacity():
    day = _project([{"date": str(TODAY), "et0_mm": 0, "rain_mm": 500}])[0]
    assert day["bucket_mm"] == pytest.approx(70)       # clamped to capacity
    assert day["bucket_pct"] == pytest.approx(100)
    assert day["irrigation_status"] == "NOT_REQUIRED"


def test_invariants_hold_under_insufficient_capacity():
    # Sparse drip (20 emitters x 0.6 = 12 L/h) can never match a bell pepper's
    # daily use: the warning fires and the plan stays well-formed every day.
    days = _project([{"date": str(TODAY + timedelta(days=i)), "et0_mm": 6, "rain_mm": 0}
                     for i in range(7)], crop="bell-pepper", soil_mm=83, area=100,
                    row=5, emitter=1, flow=0.6, pct=55)
    capacity = 83 * 0.5
    assert any(d["capacity_warning"] for d in days)
    for d in days:
        assert 0 <= d["bucket_mm"] <= capacity + 1e-6
        assert 0 <= d["run_minutes"] <= 1440
        assert d["remaining_litres"] >= 0 and d["remaining_run_minutes"] >= 0
        assert d["bucket_pct"] <= 100 + 1e-6
