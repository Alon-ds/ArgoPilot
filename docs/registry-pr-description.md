# Add farm and plot registry API

The registry service now persists farm and plot lifecycle operations in SQLite,
filters plots by farm, and exposes read-only crop, soil, and emitter catalogs.
Plot input validates dimensions, dates, coordinates, existing references, and
name uniqueness within a farm. Farm deletion is blocked while plots exist.

Errors use `application/problem+json`; database unavailability includes
`Retry-After`. The service README documents setup, API usage, validation,
error codes, test execution, and benchmark reproduction.

Validation: 12 automated integration tests cover success and failure paths using
isolated temporary SQLite files. The seed shell script was run once for local
setup; tests do not rerun it or modify the developer database.

Local HTTP benchmark: 600 requests over 60 seconds at 10 total requests/second,
equally distributed across 10 list/item routes, with zero errors. The highest
route p95 was 14.591 ms (15.691 ms including client scheduling delay), below
100 ms. This measures the small seeded database on a local machine with a mixed
workload, not production capacity or 10 requests/second per route.

See [benchmark report](registry-benchmark.md), [raw measurements](registry-benchmark.json),
and [judgment log](judgment-log.md). Author code and decision review remains
necessary before submission.
