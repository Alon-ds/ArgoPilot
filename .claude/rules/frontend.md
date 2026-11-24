---
globs: services/frontend/**
---

The frontend is a **Next.js App Router** project with server components by default.

- Pages under `src/app/` are server components — no `"use client"` unless the page genuinely needs browser state or event handlers.
- Service calls go through `src/lib/services.ts` only. Never import httpx, fetch, or axios directly in a page or component.
- Internal service URLs must never reach the browser. All fetches happen on the Next.js server side.
- Validate every service response with **Zod** before rendering. An incomplete or invalid response must show a `ServiceError`, not a blank page or partial data.
- Run before pushing:

```bash
cd services/frontend
npm run lint
npm run build
npm test
```

- `npm run dev` rebuilds on save and is fine for development. Use `npm run build` to catch type errors that the dev server sometimes misses.
