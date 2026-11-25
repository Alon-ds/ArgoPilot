from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import Settings
from engine import crop_kc
from main import create_app

TODAY = date(2026, 11, 19)
PLOT_ID = "12345678-1234-1234-1234-123456789012"


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
        assert [d["bucket_mm"] for d in days] == pytest.approx([63, 56, 49, 42, 35, 70, 63])
        assert [d["run_minutes"] for d in days] == [0, 0, 0, 0, 0, 1512, 0]
        assert days[5]["litres"] == pytest.approx(42000)
        assert set(days[0]) == {"date", "et0_mm", "kc", "litres", "run_minutes", "stale", "bucket_mm", "bucket_pct"}
        # Soil as a percent of field capacity (70 mm): 63 mm -> 90 %, a refill -> 100 %.
        assert [d["bucket_pct"] for d in days] == pytest.approx([90, 80, 70, 60, 50, 100, 90])
        assert client.get(f"/v1/plots/{PLOT_ID}/plan").json() == data
    forecast = next(r for r in calls if r.url.path == "/v1/forecast")
    assert dict(forecast.url.params) == {"lat": "31.25", "lon": "34.79", "days": "7"}
    assert {r.url.path for r in calls} == {f"/v1/plots/{PLOT_ID}", "/v1/soils/sand", "/v1/emitters/drip", "/v1/forecast"}


def test_initial_soil_pct_starts_bucket_below_full_and_irrigates_day_one(upstream):
    # capacity = 100 mm/m * 0.7 m = 70 mm, threshold 35 mm. A 40% start (28 mm)
    # already sits below threshold, so day one irrigates and refills to full,
    # unlike the default full-bucket start which waits days.
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))  # mid-season, Kc 1.15
    upstream["plot"]["initial_soil_pct"] = 40
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan").json()["days"]
    assert days[0]["run_minutes"] > 0
    assert days[0]["litres"] == pytest.approx(49000)  # (70 - 21) mm * 1000 m2
    assert days[0]["bucket_mm"] == pytest.approx(70)  # refilled to capacity


def test_initial_soil_pct_defaults_to_full_when_registry_omits_it(upstream):
    # An older registry that never sends the field must keep the full-bucket
    # behavior: no key in the plot payload, no irrigation in a dry winter week.
    upstream["plot"]["planting_date"] = str(TODAY - timedelta(days=80))
    assert "initial_soil_pct" not in upstream["plot"]
    client, _ = client_for(upstream)
    with client:
        days = client.get(f"/v1/plots/{PLOT_ID}/plan").json()["days"]
    assert days[0]["bucket_mm"] == pytest.approx(63)  # 70 full - 7 ETc, not refilled


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
    assert days[1]["litres"] == pytest.approx(46000)
    assert days[1]["run_minutes"] == 1656
    assert all(d["stale"] for d in days)


def test_pepper_root_depth_and_unbounded_demand(upstream):
    upstream["plot"].update(crop_id="bell-pepper", planting_date=str(TODAY - timedelta(days=80)))
    upstream["weather"]["days"][0]["et0_mm"] = 100
    client, _ = client_for(upstream)
    with client:
        day = client.get(f"/v1/plots/{PLOT_ID}/plan?days=1").json()["days"][0]
    assert day["bucket_mm"] == 50
    assert day["litres"] == 105000  # Do not discard demand when provisional bucket is negative.
    assert day["run_minutes"] == 3780


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
    assert [d["bucket_mm"] for d in days[:6]] == pytest.approx([63.1, 56.2, 49.3, 42.4, 35.5, 70])
    assert days[5]["litres"] == pytest.approx(41400)
    assert days[5]["run_minutes"] == 1491

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
