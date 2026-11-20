"""Reproducible warm-cache benchmark over actual loopback HTTP, with a local provider."""

import argparse
import asyncio
import json
import math
import os
import socket
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from time import perf_counter

import httpx
from fastapi import FastAPI

from config import Settings
from main import create_app

provider_app = FastAPI()
provider_calls = 0


@provider_app.get("/health")
async def provider_health():
    return {"status": "ok", "calls": provider_calls}


@provider_app.get("/v1/forecast")
async def provider_forecast():
    global provider_calls
    provider_calls += 1
    today = datetime.now(UTC).date()
    return {
        "daily_units": {"et0_fao_evapotranspiration": "mm", "rain_sum": "mm"},
        "daily": {
            "time": [(today + timedelta(days=i)).isoformat() for i in range(7)],
            "et0_fao_evapotranspiration": [3.1, 2.8, 4.0, 5.2, 1.5, 6.3, 2.9],
            "rain_sum": [0.0, 4.2, 0.5, 0.0, 1.1, 0.0, 2.0],
        },
    }


def service_app():
    # Explicit settings isolate the benchmark from .env and production provider settings.
    return create_app(
        Settings(
            _env_file=None,
            open_meteo_base_url=os.environ["WEATHER_BENCHMARK_PROVIDER_URL"],
            open_meteo_api_key="",
            forecast_timezone="UTC",
            provider_timeout_seconds=5,
            provider_retries=2,
            cache_freshness_seconds=10800,
            stale_max_age_seconds=86400,
            retry_after_seconds=60,
        )
    )


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


async def wait_ready(client, url, process):
    deadline = perf_counter() + 15
    while perf_counter() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Benchmark server exited with {process.returncode}")
        try:
            if (await client.get(f"{url}/health")).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.05)
    raise RuntimeError("Benchmark server did not start within 15 seconds")


async def measure(url: str, requests: int, rps: float) -> dict:
    params = {"lat": 31.25, "lon": 34.79, "days": 7}
    async with httpx.AsyncClient(base_url=url, timeout=5, trust_env=False) as client:
        warm = await client.get("/v1/forecast", params=params)
        warm.raise_for_status()
        expected = warm.json()
        if expected["stale"] or len(expected["days"]) != 7:
            raise RuntimeError("Warmup did not return a complete fresh week")

        async def one():
            start = perf_counter()
            response = await client.get("/v1/forecast", params=params)
            latency_ms = (perf_counter() - start) * 1000
            response.raise_for_status()
            if response.json() != expected:
                raise RuntimeError("Forecast changed: benchmark no longer measures warm cache")
            return latency_ms

        start = perf_counter()
        tasks = []
        for index in range(requests):
            await asyncio.sleep(max(0, start + index / rps - perf_counter()))
            tasks.append(asyncio.create_task(one()))
        latencies = await asyncio.gather(*tasks)
        elapsed = perf_counter() - start
    ordered = sorted(latencies)
    p95 = ordered[math.ceil(len(ordered) * 0.95) - 1]
    return {
        "transport": "loopback HTTP to uvicorn",
        "requests": requests,
        "target_rps": rps,
        "elapsed_seconds": round(elapsed, 3),
        "p50_ms": round(ordered[math.ceil(len(ordered) * 0.5) - 1], 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(max(ordered), 3),
        "passed": p95 <= 100,
    }


async def run(args):
    if args.url:
        result = await measure(args.url, args.requests, args.rps)
        result["provider_calls"] = "not instrumented; use local mode to prove zero measured calls"
        return result

    provider_port, weather_port = free_port(), free_port()
    while weather_port == provider_port:
        weather_port = free_port()
    provider_url = f"http://127.0.0.1:{provider_port}"
    weather_url = f"http://127.0.0.1:{weather_port}"
    processes = []
    try:
        for module, port in [
            ("benchmark:provider_app", provider_port),
            ("benchmark:service_app", weather_port),
        ]:
            command = [
                sys.executable,
                "-m",
                "uvicorn",
                module,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
                "--log-level",
                "error",
            ]
            if module.endswith("service_app"):
                command.append("--factory")
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    env={**os.environ, "WEATHER_BENCHMARK_PROVIDER_URL": provider_url},
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                )
            )
        async with httpx.AsyncClient(timeout=1, trust_env=False) as client:
            await wait_ready(client, provider_url, processes[0])
            await wait_ready(client, weather_url, processes[1])
            result = await measure(weather_url, args.requests, args.rps)
            count = (await client.get(f"{provider_url}/health")).json()["calls"]
        result["provider_calls_including_warmup"] = count
        result["provider_calls_during_measurement"] = count - 1
        result["passed"] = result["passed"] and count == 1
        return result
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", help="Benchmark an existing weather server (makes one warmup call)"
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--rps", type=float, default=10)
    args = parser.parse_args()
    if args.requests < 20 or not math.isfinite(args.rps) or args.rps <= 0:
        parser.error("Use at least 20 requests and a finite positive rps")
    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
