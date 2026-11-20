# Frontend design and implementation plan

Scope: FR-2.15–19 and NFR-2.8 only. No commits, secrets, or changes outside this directory.

Design: field notebook with white #ffffff, mist #edf3f2, forest #154b3b,
ink #183c36, water #176187, and amber #805000. System humanist sans
(Segoe UI, then system sans) for legible instructions and tabular numbers.
Left aligned, max 960 px, 16 px phone gutters. Farm sections contain linked
plot rows. Plot page: compact back link/name, today's large instruction,
inline stale warning, then a seven-day table. Service status is a small footer.

Alternatives considered: a timeline hides column comparisons; a wide seven-column
table overflows phones. Use three columns (day, irrigation, weather/soil), with
stacked units and labels inside cells. The prominent instruction is necessary
for field use; avoid decorative hero metrics, images, and dashboard widgets.

Architecture: App Router server pages, no browser service requests. All HTTP and
configuration in src/lib, HTTP-only boundaries, runtime schema validation,
bounded timeouts, no caching or invented numeric defaults. Python's
pydantic-settings requirement applies to Python services, not this Next.js app.

1. Scaffold Next.js/TypeScript/Tailwind/shadcn primitives and lock dependencies.
2. Add HTTP fixture and browser acceptance tests for farm links, today first,
   stale rows, zero irrigation, service errors, invalid plans, health, and 375 px.
3. Implement validated server configuration, HTTP clients, pages, and styles.
4. Run build, lint and acceptance tests; review phone screenshots and diff.

Review focus: malformed/missing plan values never become zeros; mismatched plot
IDs fail safely; long names and large numbers wrap; unhealthy services remain
visible; registry metadata failure must not hide a valid planner recommendation.
