# AgroPilot frontend

Next.js App Router, TypeScript, Tailwind CSS 4 and locally owned canonical shadcn/ui
Badge and Alert components. This app implements only the farm list and plot plan
pages from P2 FR-2.15–19. The prominent soil-bucket notice explains that plans
start full and use neither sensor readings nor irrigation history.

## Run

Use Node.js 22 LTS or newer and npm. From this directory:

```bash
npm ci
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. Edit the service URLs in your local configuration
to match your running services. Defaults in the example use ports 8000/8001/8002;
the current shared development services use 18000/18001/18002.
Never commit `.env.local`, `.next`, or `node_modules`.

| Variable | Meaning |
| --- | --- |
| `REGISTRY_URL` | Required registry HTTP(S) base URL |
| `WEATHER_URL` | Required weather HTTP(S) base URL, used for health |
| `PLANNER_URL` | Required planner HTTP(S) base URL |
| `SERVICE_TIMEOUT_MS` | Request timeout, default 5000 ms, allowed 100–60000 |
| `PLAN_TIMEZONE` | IANA zone used to validate today's plan, default `Asia/Jerusalem`; must match the planner |

Server configuration is validated in `src/lib/config.ts` when route modules
load, including during production build. A missing/invalid URL produces a clear
configuration error. CI must supply the three URLs (safe example values suffice
for build); it needs no real services for build or fixture browser tests.
`pydantic-settings` is for the independent Python services; this TypeScript app
uses Zod for settings and response validation.

## HTTP contracts and safety

All upstream HTTP calls live in `src/lib/services.ts`, guarded by `server-only`.
Pages fetch on the server, without caching. No upstream URL is public or sent
to the browser. Services share no imports, models, or database connections.

- Registry: `GET /v1/farms`, `/v1/plots`, `/v1/plots/{id}`; plain JSON arrays
  and UUID-based models inspected in the local registry implementation.
- Planner: `GET /v1/plots/{id}/plan?days=7`, returning
  `{plot_id, days:[{date, et0_mm, kc, litres, run_minutes, stale, bucket_mm}]}`.
- All three: `GET /health`, with `{"status":"ok"}` meaning up.

Plans must have exactly seven consecutive dates starting today in
`PLAN_TIMEZONE`, the requested plot ID, finite nonnegative numbers, and explicit
stale flags. Missing/invalid data is an error, never a zero recommendation.
No irrigation calculations occur in this app. Stale labels appear beside each
affected row and today's numbers. Upstream failures show status codes and known
dependency names without stack traces or arbitrary internal error details.
Health checks stream separately from recommendations. Registry metadata errors
do not suppress an otherwise valid plan. Refresh to fetch current information.

## Verify

```bash
npm run build
npm run lint
npm audit --audit-level=low
npm exec -- playwright install chromium
npm test
```

Browser acceptance tests start the production app on port 3100 and a separate
HTTP fixture on 18080. They cover farm links, empty farms, today/no-irrigation,
stale rows, planner errors/timeouts, incomplete/old/wrong-plot plans, health and
registry failures, no browser upstream calls, and a 375 × 667 viewport. The
mobile test asserts that today's instruction is in view and the document has
no horizontal overflow; it saves `test-results/plot-mobile.png`.
These fixtures verify frontend behavior, not the independent services' logic.

For CI, after the existing `npm ci`, build and lint steps, install Chromium with
`npm exec -- playwright install --with-deps chromium`, then run `npm test`.
Upload `test-results/` on failure. Provide the three service URL variables to
the build step and keep ports 3100/18080 free. The Playwright config supplies
its own fixture URLs and time zone to the production test server.

Design and implementation notes: [docs/implementation.md](docs/implementation.md).

The Badge and Alert source comes from the official shadcn `new-york-v4` registry
([Badge](https://ui.shadcn.com/r/styles/new-york-v4/badge.json),
[Alert](https://ui.shadcn.com/r/styles/new-york-v4/alert.json)); only the `cn`
import is mapped to this app's utility. Badge uses the actual `radix-ui` Slot.
These components are installed as local source, shadcn's standard ownership model.
The requested Anthropic frontend-design skill was fetched and read; the installed
copy at `.claude/skills/frontend-design/SKILL.md` was also read.
