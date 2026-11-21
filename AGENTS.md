# AgroPilot instructions for Codex

These instructions apply to the whole repository.

## Safety and configuration

- Never read, print, copy, or commit real `.env` or `.env.local` files.
- Use only the committed `.env.example` files to understand configuration.
- Keep credentials and service secrets out of source code, tests, logs, and
  documentation.
- Do not commit generated databases, coverage reports, `.next/`,
  `node_modules/`, Playwright output, or generated PDFs.

## Project skills

Reusable Codex skills live under `.agents/skills/`:

- `registry-api` for Registry HTTP contracts and tests.
- `irrigation-calc-reference` for FAO-56 planner calculations.
- `frontend-design` for intentional UI design and critique.
- `research` for evidence gathered from primary sources.

Read the relevant `SKILL.md` before changing that area.

## Verification

- Registry changes: run its Python 3.12/3.13 test and coverage workflow
  locally where practical; coverage must remain 100% for lines and branches.
- Weather and Planner changes: run each service's full pytest suite and audit.
- Frontend changes: run `npm run lint`, `npm run build`, `npm audit`, and
  the Playwright suite.
- Use a short-lived branch and pull request. Merge only after GitHub Actions
  is green.
