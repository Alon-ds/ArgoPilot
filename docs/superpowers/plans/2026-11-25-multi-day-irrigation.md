# Multi-Day Irrigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cap each day's drip runtime at a configurable limit and carry the unmet irrigation deficit across forecast days, updating the soil bucket only by water actually scheduled.

**Architecture:** A per-day water balance in `engine.project()` carries `bucket` and an `irrigation_active` latch across the forecast days. Each day applies rain and ETc, caps the scheduled runtime at `max_daily_runtime_minutes`, raises the bucket only by the scheduled water, and recomputes the remaining deficit. New response fields expose required/scheduled/remaining and a status enum; the frontend renders ongoing cycles and hydraulic warnings.

**Tech Stack:** FastAPI + Pydantic + exact `Fraction` arithmetic (Planner); Next.js App Router + Zod (Frontend); pytest + Playwright.

**Spec:** `docs/multi-day-irrigation-design.md`

## Global Constraints

- Daily limit default **1440** min, configurable via `config.max_daily_runtime_minutes` (gt=0, le=1440).
- Preserve existing P2 fields `date, et0_mm, kc, litres, run_minutes, stale, bucket_mm`; new fields are additive.
- Deterministic pure engine; exact `Fraction` runtime arithmetic; no persistence, no LLM, no new services.
- Invariants: `0 <= bucket_mm <= capacity`, `0 <= run_minutes <= max_daily`, `remaining_litres >= 0`.
- Code, comments, tests, docs, UI labels in English.

## Review Focus

- **Rain mid-cycle lifts bucket above 50%** → the active cycle must continue, not abandon (Task 2).
- **Rain fills bucket to capacity mid-cycle** → cycle closes `COMPLETED`, no over-irrigation (Task 2).
- **Daily crop demand > daily hydraulic capacity** → `capacity_warning=True`, bucket never recovers (Task 2).
- **Unfinished cycle at the 7th forecast day** → frontend shows the horizon-overflow note with remaining (Task 3).
- **Exact 24 h requirement (required == daily capacity)** → not capped, `COMPLETED`, `run_minutes == max` (Task 2).

---

### Task 1: Engine multi-day model, config, response fields — DONE

**Files:** `services/planner-service/engine.py`, `models.py`, `config.py`, `main.py`.

Implemented: `project(..., max_daily_minutes=1440)` with the latched cycle, the clamp to `[0, capacity]`, the daily cap, proportional bucket update, remaining recomputation, `IrrigationStatus` enum and new `PlanDay` fields, `config.max_daily_runtime_minutes`, and the `test`-crop display fix (`et0_mm`=drain, `kc`=1.0). The five pre-existing tests were updated to the capped multi-day values with explanations. **70 planner tests pass.** Verified in self-review before this plan.

### Task 2: Engine edge-case tests (§16)

**Files:** Test: `services/planner-service/tests/test_planner.py`

**Interfaces:** Consumes `engine.project(plot, soil, emitter, forecast, max_daily_minutes)` and the `upstream`/`client_for` fixtures.

- [ ] **Step 1: Add failing tests** for: (a) cycle latch — a rain day lifts the bucket above 50% mid-cycle yet it continues to full; (b) rain fills to capacity mid-cycle → `COMPLETED`, `litres==0`; (c) exact 24 h — required == daily capacity → not capped, `run_minutes==1440`, `COMPLETED`; (d) `max_daily_minutes=720` halves the day's delivery; (e) heavy rain never pushes `bucket_mm > capacity`; (f) an invariants sweep over a multi-day capacity-insufficient plot (`0<=bucket<=cap`, `run_minutes<=max`, `remaining>=0`, `bucket_pct<=100`).
- [ ] **Step 2: Run** `uv run --no-sync python -m pytest -q` — new tests fail only where behavior is genuinely missing; most should pass against the implemented engine (regression guard).
- [ ] **Step 3:** Fix any engine gap a test exposes (minimal).
- [ ] **Step 4: Run** the full planner suite — Expected: all pass.
- [ ] **Step 5: Commit** `test(planner): multi-day edge cases and invariants`.

### Task 3: Frontend — ongoing-cycle cards, remaining, horizon note

**Files:** Modify `services/frontend/src/lib/services.ts` (Zod day schema + types), `src/components/plan.tsx` (today card + table), `src/app/globals.css`; Test: `src/../tests/mock-services.mjs`, `tests/frontend.spec.ts`.

**Interfaces:** Consumes the new `PlanDay` JSON fields from Task 1.

- [ ] **Step 1:** Extend the Zod `daySchema` with the new fields (additive, required).
- [ ] **Step 2:** Update `mock-services.mjs` plan days to include the new fields; add a mode producing an unfinished cycle at day 7.
- [ ] **Step 3: Write failing Playwright tests:** today card shows "Irrigation in progress" with scheduled/remaining and "Continues tomorrow" when `irrigation_in_progress`; a capacity-warning plot shows the hydraulic warning; an unfinished cycle at day 7 shows the horizon note; a normal completed day still reads normally; large minutes render as `Hh Mm`.
- [ ] **Step 4:** Implement `plan.tsx` cards + an `minutesToHm` helper + CSS; keep today's recommendation above the fold and 375 px layout.
- [ ] **Step 5: Run** `npm run lint && npm run build && npm test` — Expected: all pass.
- [ ] **Step 6: Commit** `feat(frontend): show multi-day irrigation cycle and remaining water`.

### Task 4: Documentation — skill, README, judgment log

**Files:** Modify `.claude/skills/irrigation-calc-reference/SKILL.md`, `services/planner-service/README.md`, `docs/judgment-log.md`.

- [ ] **Step 1:** Add the daily hydraulic cap, cycle latch, remaining calc, runtime rounding, and three hand examples (single-day, multi-day, insufficient capacity) to the skill; separate FAO-56 knowledge from this engineering extension.
- [ ] **Step 2:** Update the Planner README response contract (new fields + changed semantics).
- [ ] **Step 3:** Add a judgment-log entry (proposed, decided, why, alternatives, limitations incl. Phase 2).
- [ ] **Step 4: Commit** `docs: document the multi-day irrigation model`.

### Task 5: Verification (superpowers:verification-before-completion)

- [ ] Run planner pytest, registry pytest (100% coverage), frontend lint+build+Playwright+audit — paste real output.
- [ ] Restart the running planner; verify the §4/§10 scenario live (test45) in the browser; compare API response to the frontend display.
- [ ] Produce the before/after numerical example and the Hebrew technical report (§20).
