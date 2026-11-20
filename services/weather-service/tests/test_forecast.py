import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from config import Settings
from main import create_app


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 19, 6, tzinfo=UTC)

    def __call__(self):
        return self.now


def payload(today="2026-11-19"):
    start = datetime.fromisoformat(today).date()
    return {
        "latitude": 31.25,
        "longitude": 34.75,
        "timezone": "GMT",
        "utc_offset_seconds": 0,
        "daily_units": {"time": "iso8601", "et0_fao_evapotranspiration": "mm", "rain_sum": "mm"},
        "daily": {
            "time": [(start + timedelta(days=i)).isoformat() for i in range(7)],
            "et0_fao_evapotranspiration": [3.1, 2.8, 4.0, 5.2, 1.5, 6.3, 2.9],
            "rain_sum": [0.0, 4.2, 0.5, 0.0, 1.1, 0.0, 2.0],
        },
    }


class Provider:
    def __init__(self, body=None):
        self.body = body if body is not None else payload()
        self.calls = []
        self.failures = []

    async def __call__(self, request):
        self.calls.append(request)
        await asyncio.sleep(0)
        outcome = self.failures.pop(0) if self.failures else self.body
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, httpx.Response):
            return outcome
        return httpx.Response(200, json=outcome)


@asynccontextmanager
async def client_for(provider, clock=None, **overrides):
    overrides.setdefault("forecast_timezone", "UTC")
    settings = Settings(_env_file=None, **overrides)
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as upstream:
        app = create_app(settings=settings, provider_client=upstream, clock=clock or Clock())
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://weather.test"
            ) as client:
                yield client


async def forecast(client, **params):
    return await client.get("/v1/forecast", params={"lat": 31.25, "lon": 34.79, **params})


async def test_schema_and_adapter_fetch_full_week_even_for_one_day():
    provider = Provider()
    async with client_for(provider) as client:
        response = await forecast(client, days=1)
    assert response.status_code == 200
    assert response.json() == {
        "lat": 31.25,
        "lon": 34.79,
        "source": "open-meteo",
        "fetched_at": "2026-11-19T06:00:00Z",
        "stale": False,
        "days": [{"date": "2026-11-19", "et0_mm": 3.1, "rain_mm": 0.0}],
    }
    query = provider.calls[0].url.params
    assert query["forecast_days"] == "7"
    assert query["daily"] == "et0_fao_evapotranspiration,rain_sum"
    assert query["timezone"] == "UTC"
    assert query["precipitation_unit"] == "mm"
    assert provider.calls[0].url.path == "/v1/forecast"
    assert "apikey" not in query


@pytest.mark.parametrize(
    "params",
    [
        {"lat": -91},
        {"lat": 91},
        {"lon": -181},
        {"lon": 181},
        {"lat": "NaN"},
        {"lon": "Infinity"},
        {"lat": "bad"},
        {"days": 0},
        {"days": 8},
        {"days": 1.5},
        {"days": "bad"},
    ],
)
async def test_invalid_query_returns_validation_without_provider(params):
    provider = Provider()
    async with client_for(provider) as client:
        response = await forecast(client, **params)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"
    assert not provider.calls


async def test_missing_coordinates_and_health():
    provider = Provider()
    async with client_for(provider) as client:
        response = await client.get("/v1/forecast")
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION"
        assert (await client.get("/health")).json() == {"status": "ok"}
    assert not provider.calls


@pytest.mark.parametrize("lat,lon", [(-90, -180), (90, 180), (0, 0)])
async def test_coordinate_boundaries_are_accepted(lat, lon):
    async with client_for(Provider()) as client:
        response = await forecast(client, lat=lat, lon=lon)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "points,expected_lat",
    [
        ([(31.21, 34.71), (31.29, 34.79), (31.2, 34.7)], "31.2"),
        ([(-0.01, 34.71), (-0.09, 34.79), (-0.1, 34.7)], "-0.1"),
    ],
)
async def test_same_floor_cell_shares_week_and_echoes_requested_point(points, expected_lat):
    provider = Provider()
    async with client_for(provider) as client:
        for i, (lat, lon) in enumerate(points):
            response = await forecast(client, lat=lat, lon=lon, days=1 if i == 0 else 7)
            assert response.status_code == 200
            assert response.json()["lat"] == lat
            assert response.json()["lon"] == lon
            assert len(response.json()["days"]) == (1 if i == 0 else 7)
    assert len(provider.calls) == 1
    assert provider.calls[0].url.params["latitude"] == expected_lat


async def test_adjacent_cells_are_separate():
    provider = Provider()
    async with client_for(provider) as client:
        for lat in [31.2999, 31.3, -0.0001, 0]:
            assert (await forecast(client, lat=lat)).status_code == 200
    assert len(provider.calls) == 4


async def test_freshness_expires_at_three_hours():
    provider, clock = Provider(), Clock()
    async with client_for(provider, clock) as client:
        await forecast(client)
        clock.now += timedelta(hours=3) - timedelta(microseconds=1)
        assert (await forecast(client)).json()["stale"] is False
        assert len(provider.calls) == 1
        clock.now += timedelta(microseconds=1)
        response = await forecast(client)
        assert response.json()["fetched_at"] == "2026-11-19T09:00:00Z"
    assert len(provider.calls) == 2


async def test_simultaneous_cold_requests_share_one_fetch():
    provider = Provider()
    async with client_for(provider) as client:
        responses = await asyncio.gather(*(forecast(client) for _ in range(20)))
    assert all(response.status_code == 200 for response in responses)
    assert len(provider.calls) == 1


async def test_two_retries_then_success():
    provider = Provider()
    provider.failures = [httpx.ReadTimeout("timeout"), httpx.Response(502)]
    async with client_for(provider) as client:
        response = await forecast(client)
    assert response.status_code == 200
    assert response.json()["stale"] is False
    assert len(provider.calls) == 3


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("offline"),
        httpx.ReadTimeout("timeout"),
        httpx.Response(500),
        httpx.Response(429),
        httpx.Response(200, text="not JSON"),
        {},
        {"daily": None},
        [],
    ],
)
async def test_provider_failure_retries_then_503_without_cache(failure):
    provider = Provider()
    provider.failures = [failure] * 3
    async with client_for(provider) as client:
        response = await forecast(client)
    assert response.status_code == 503
    assert response.json()["code"] == "UNAVAILABLE"
    assert int(response.headers["Retry-After"]) > 0
    assert len(provider.calls) == 3


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["daily"].pop("rain_sum"),
        lambda p: p["daily"]["rain_sum"].pop(),
        lambda p: p["daily"]["et0_fao_evapotranspiration"].__setitem__(6, None),
        lambda p: p["daily"]["rain_sum"].__setitem__(0, "0"),
        lambda p: p["daily"]["rain_sum"].__setitem__(0, True),
        lambda p: p["daily"]["rain_sum"].__setitem__(0, -1),
        lambda p: p["daily"]["time"].__setitem__(1, "2026-11-19"),
        lambda p: p["daily"]["time"].__setitem__(1, "invalid"),
        lambda p: p["daily_units"].__setitem__("rain_sum", "inch"),
        lambda p: p.pop("daily_units"),
        lambda p: p["daily"]["time"].reverse(),
    ],
)
async def test_incomplete_or_invalid_week_is_never_accepted_even_for_one_day(mutation):
    body = deepcopy(payload())
    mutation(body)
    provider = Provider(body)
    async with client_for(provider) as client:
        response = await forecast(client, days=1)
    assert response.status_code == 503
    assert len(provider.calls) == 3


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
async def test_nonfinite_provider_numbers_are_rejected(number):
    body = payload()
    body["daily"]["rain_sum"][0] = "PLACEHOLDER"
    import json

    raw = json.dumps(body).replace('"PLACEHOLDER"', number)
    provider = Provider()
    provider.failures = [httpx.Response(200, text=raw)] * 3
    async with client_for(provider) as client:
        assert (await forecast(client)).status_code == 503
    assert len(provider.calls) == 3


async def test_failure_serves_original_stale_values_without_replacing_cache():
    provider, clock = Provider(), Clock()
    async with client_for(provider, clock) as client:
        original = (await forecast(client)).json()
        clock.now += timedelta(hours=3)
        provider.body = {}
        stale = await forecast(client)
        assert stale.status_code == 200
        assert stale.json() == {**original, "stale": True}
        assert len(provider.calls) == 4
        provider.body = payload()
        provider.body["daily"]["rain_sum"][0] = 12.3
        recovered = await forecast(client)
        assert recovered.json()["stale"] is False
        assert recovered.json()["days"][0]["rain_mm"] == 12.3
        assert recovered.json()["fetched_at"] == "2026-11-19T09:00:00Z"


@pytest.mark.parametrize("age_hours,status", [(24, 200), (24.001, 503)])
async def test_stale_age_limit_is_24_hours(age_hours, status):
    provider, clock = Provider(), Clock()
    async with client_for(provider, clock) as client:
        await forecast(client)
        clock.now += timedelta(hours=age_hours)
        provider.body = {}
        response = await forecast(client, days=1)
    assert response.status_code == status
    if status == 200:
        assert response.json()["stale"] is True
        assert response.json()["days"][0] == {
            "date": "2026-11-20",
            "et0_mm": 2.8,
            "rain_mm": 4.2,
        }


async def test_midnight_checks_date_coverage_even_while_fresh():
    provider, clock = Provider(), Clock()
    clock.now = datetime(2026, 11, 19, 23, tzinfo=UTC)
    async with client_for(provider, clock) as client:
        await forecast(client)
        clock.now += timedelta(hours=2)
        provider.body = {}
        response = await forecast(client, days=7)
        assert response.status_code == 503  # missing day 7, never pad or truncate
        assert len(provider.calls) == 4
        response = await forecast(client, days=6)
        assert response.status_code == 200
        assert response.json()["days"][0]["date"] == "2026-11-20"
        assert len(response.json()["days"]) == 6
        assert len(provider.calls) == 4  # full requested range is still fresh


async def test_yesterdays_provider_forecast_is_rejected():
    provider = Provider(payload("2026-11-18"))
    async with client_for(provider) as client:
        assert (await forecast(client, days=1)).status_code == 503


async def test_configurable_provider_and_retry_policy():
    provider = Provider()
    provider.failures = [httpx.Response(503)] * 2
    async with client_for(
        provider,
        open_meteo_base_url="https://customer-api.open-meteo.com",
        open_meteo_api_key="test-key",
        provider_retries=1,
        retry_after_seconds=45,
        provider_timeout_seconds=2,
    ) as client:
        response = await forecast(client)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "45"
    assert len(provider.calls) == 2
    request = provider.calls[0]
    assert request.url.host == "customer-api.open-meteo.com"
    assert request.url.params["apikey"] == "test-key"
    assert request.extensions["timeout"]["read"] == 2


@pytest.mark.parametrize(
    "settings",
    [
        {"provider_timeout_seconds": 0},
        {"provider_retries": -1},
        {"cache_freshness_seconds": 0},
        {"stale_max_age_seconds": 1},
        {"open_meteo_base_url": "not-a-url"},
        {"retry_after_seconds": 0},
    ],
)
def test_invalid_configuration_fails_at_startup(settings):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **settings)


async def test_jerusalem_day_starts_before_utc_midnight_and_provider_uses_same_zone():
    provider, clock = Provider(payload("2026-11-20")), Clock()
    clock.now = datetime(2026, 11, 19, 22, 30, tzinfo=UTC)
    async with client_for(provider, clock, forecast_timezone="Asia/Jerusalem") as client:
        response = await forecast(client)
    assert response.status_code == 200
    assert response.json()["days"][0]["date"] == "2026-11-20"
    assert response.json()["fetched_at"] == "2026-11-19T22:30:00Z"
    assert provider.calls[0].url.params["timezone"] == "Asia/Jerusalem"


async def test_local_midnight_requires_coverage_even_with_fresh_cache():
    provider, clock = Provider(), Clock()
    clock.now = datetime(2026, 11, 19, 21, 59, tzinfo=UTC)
    async with client_for(provider, clock, forecast_timezone="Asia/Jerusalem") as client:
        assert (await forecast(client)).status_code == 200
        clock.now += timedelta(minutes=2)
        provider.body = {}
        response = await forecast(client, days=7)
        assert response.status_code == 503
        assert len(provider.calls) == 4
        response = await forecast(client, days=1)
        assert response.status_code == 200
        assert response.json()["days"][0]["date"] == "2026-11-20"


def test_unknown_forecast_timezone_is_a_startup_error():
    with pytest.raises(ValidationError, match="FORECAST_TIMEZONE"):
        Settings(_env_file=None, forecast_timezone="Mars/Olympus")
