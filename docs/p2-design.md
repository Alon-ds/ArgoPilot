# P2 design

The task extends the existing FastAPI registry into four independently run
services. Registry remains port 8000; weather uses 8001; planner uses 8002;
Next.js uses 3000. Service boundaries are HTTP, never Python imports.

## Decisions and alternatives

Use SQLAlchemy with DATABASE_URL for both SQLite and PostgreSQL, preserving
existing API contracts and seed IDs. A separate PostgreSQL implementation would
duplicate data access; a database-specific compatibility branch would make
production differ unnecessarily. Use parameterized SQL through SQLAlchemy.

Weather owns an in-process cache keyed by floor(latitude*10), floor(longitude*10).
Cache a full seven-day forecast and return the requested prefix. Validate dates,
units, lengths, finite nonnegative numbers before accepting a provider response.
Freshness is three hours; stale data may be returned only within 24 hours and
only if it covers the requested calendar days. Retry twice before falling back.

Planner owns deterministic arithmetic, using the existing FAO research. This
exercise uses a half-full trigger as explicitly described in P2. Document its
difference from crop-specific FAO allowable depletion. With no soil sensor/history
input, begin each stateless projection with a full bucket and disclose that policy.
Do not represent it as measured moisture. Unknown or missing upstream data fails
explicitly; never manufacture zero weather or irrigation values.

Next.js server components fetch the services through src/lib only. A plot page
puts today's advice first, then the daily balance and stale markers. Health and
upstream errors remain visible. No browser-to-service calls or new features.

## Verification and limits

Preserve registry integration tests and coverage enforcement. Add mocked provider,
cache, retry and upstream error tests, hand-calculated engine examples, frontend
build/lint, and live HTTP integration. Benchmark PostgreSQL registry and warm
weather at 10 rps, with p95 at most 100 ms. Verify mobile at 375px in a browser.
Never label an unavailable live check as passed. GitHub API access currently fails
for the private repository; git transport access does not prove API access.
