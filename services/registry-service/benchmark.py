"""Measure read endpoints at a fixed total HTTP request rate."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import time
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--rate", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results.json"))
    parser.add_argument("--database", choices=("sqlite", "postgresql"), help="Backend under test")
    parser.add_argument("--summary-only", action="store_true", help="Omit individual request samples")
    args = parser.parse_args()
    if args.duration <= 0 or args.rate <= 0:
        parser.error("duration and rate must be positive")

    paths = []
    for table in ("farms", "plots", "crops", "soils", "emitters"):
        path = f"/v1/{table}"
        with urlopen(args.base_url + path, timeout=5) as response:
            items = json.load(response)
        if not items:
            parser.error(f"{path} must contain at least one item")
        paths.extend((path, f"{path}/{items[0]['id']}"))

    def measure(path, scheduled):
        started = time.perf_counter()
        try:
            with urlopen(args.base_url + path, timeout=5) as response:
                json.load(response)
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
            error = None
        except Exception as exception:
            error = str(exception)
        finished = time.perf_counter()
        return {
            "path": path,
            "latency_ms": (finished - started) * 1000,
            "scheduled_latency_ms": (finished - scheduled) * 1000,
            "error": error,
        }

    # Warm each route before the timed run.
    for path in paths:
        sample = measure(path, time.perf_counter())
        if sample["error"]:
            raise RuntimeError(sample["error"])

    started_at = datetime.now(timezone.utc).isoformat()
    futures = []
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=20) as executor:
        for index in range(args.duration * args.rate):
            scheduled = start + index / args.rate
            time.sleep(max(0, scheduled - time.perf_counter()))
            futures.append(executor.submit(measure, paths[index % len(paths)], scheduled))
        samples = [future.result() for future in futures]
    elapsed = time.perf_counter() - start

    def p95(values):
        ordered = sorted(values)
        return ordered[math.ceil(len(ordered) * 0.95) - 1]

    results = []
    for path in paths:
        group = [sample for sample in samples if sample["path"] == path]
        if not group:
            continue
        result = {
            "path": path, "requests": len(group),
            "errors": sum(sample["error"] is not None for sample in group),
            "p95_ms": round(p95([sample["latency_ms"] for sample in group]), 3),
            "scheduled_p95_ms": round(p95([sample["scheduled_latency_ms"] for sample in group]), 3),
            "max_ms": round(max(sample["latency_ms"] for sample in group), 3),
        }
        results.append(result)
        print(f"{path}: p95={result['p95_ms']} ms, errors={result['errors']}", flush=True)
    passed = len(results) == len(paths) and all(
        result["errors"] == 0 and result["scheduled_p95_ms"] <= 100 for result in results
    )
    report = {
        "started_at_utc": started_at, "platform": platform.platform(),
        "python": platform.python_version(), "base_url": args.base_url,
        "duration_seconds": args.duration, "target_total_rps": args.rate,
        "elapsed_seconds": round(elapsed, 3), "total_requests": len(samples),
        "workload": "Round-robin over 10 read endpoints; 10 total requests/second, 1 per endpoint/second at defaults.",
        "percentile_method": "nearest rank; scheduled latency includes client scheduling delay",
        "passed": passed, "endpoints": results,
    }
    if args.database:
        report["database"] = args.database
    if not args.summary_only:
        report["samples"] = samples
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Passed: {passed}. Results: {args.output}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
