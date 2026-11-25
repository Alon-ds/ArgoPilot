# Multi-Day Irrigation Planning — Design

Date: 2026-11-25
Status: Approved (verbal), implemented on `fix/multi-day-irrigation`

## Intent and why

The planner assumed every irrigation refill is delivered instantly on the day it
is triggered (`bucket = capacity if irrigate`). With a sparse drip layout this
produced plans like **2,955 L in 14,778 minutes** (≈246 h ≈ 10 days) applied in a
single day, after which the bucket showed 100% and the next day showed "no
irrigation". That is physically impossible: a drip system runs at most 24 h/day.

The goal is a **multi-day scheduling model**: cap each day's irrigation at a
configurable runtime, update the soil bucket only by the water actually
scheduled, and carry the unmet deficit into the following forecast days while
rain and crop use keep changing the balance.

## Goals

- No day's scheduled runtime exceeds the configured daily limit (default 1440 min).
- The end-of-day bucket reflects only water actually scheduled — it never jumps
  to 100% unless the balance supports it.
- An unfinished irrigation cycle continues across forecast days until the bucket
  is full; rain and ETc are re-applied each day.
- Expose when the drip system physically cannot keep up with crop demand.
- Preserve the existing P2 response fields and all current behavior for plots
  whose refill already fits inside one day.

## Non-goals

- Persisting soil-water or irrigation state **across separate API requests**
  (Phase 2 — see below). This task is multi-day state *within one forecast*.
- Changing the Registry, the 50% trigger policy, or the FAO-56 Kc curves.
- Forecasting beyond the official 1–7 day horizon.

## Anti-goals (would be failures even if tests pass)

- Silently inflating emitter flow or plot parameters to make a plan "complete".
- Claiming physical irrigation happened (the planner forecasts, it does not
  confirm execution).
- Hiding severe water stress behind an optimistic recovery forecast.

## Constraints

- Deterministic, pure engine; no persistence, no LLM, no new services.
- Keep irrigation math in the Planner; Registry/Weather/Frontend boundaries hold.
- Preserve exact rational (`Fraction`) runtime arithmetic to avoid off-by-one
  minute errors at integer runtimes.
- Not an explicit P2/FAO-56 requirement — this is a documented engineering
  extension of the simplified bucket policy.

## Approaches considered

1. **Re-evaluate the 50% trigger every day (no cycle state).** Simplest, but a
   rain shower that lifts the bucket just over 50% mid-refill would abandon an
   unfinished cycle. Rejected — it does not model a real irrigation cycle.
2. **Blindly subtract the daily limit from the original required runtime.**
   Ignores that rain and crop use change the deficit each day. Rejected — wrong
   numbers as soon as weather varies.
3. **Chosen: per-day water balance with a latched cycle.** Carry `bucket` and an
   `irrigation_active` flag across the forecast days. Each day: apply rain and
   ETc, cap the scheduled runtime at the daily limit, raise the bucket only by
   the scheduled water, recompute the remaining deficit. A cycle starts below
   50% and continues (even above 50%) until the bucket is full; rain that fills
   it closes the cycle.

## Decisions (as approved)

- **Daily limit** is `config.max_daily_runtime_minutes`, default **1440**,
  configurable down to an operational ceiling via the environment.
- **Projected bucket is clamped to `[0, capacity]`** before taking the deficit
  (FAO-56-style), so demand is bounded by capacity; severe stress surfaces via
  `capacity_warning`, not an inflated volume. (This changes the old
  "unbounded demand" test — documented in that test.)
- **New response fields** (additive): `bucket_before_mm`, `required_litres`,
  `required_run_minutes`, `remaining_litres`, `remaining_run_minutes`,
  `irrigation_in_progress`, `irrigation_status`
  (`NOT_REQUIRED|SCHEDULED|CONTINUING|COMPLETED`), `capacity_warning`.
- **Changed semantics** of three existing fields (documented): `litres` and
  `run_minutes` are now *scheduled today*, and `bucket_mm` is the partial
  end-of-day level.
- **Synthetic `test` crop** display fixed: it reports its drain as `et0_mm` with
  `kc = 1.0`, so `ET0 × Kc` matches the soil change.

## What's left to the builder

- Frontend plan cards: show required/scheduled/remaining, ongoing-cycle state,
  the 7-day-horizon overflow note, and a readable hours:minutes format.
- Update the `irrigation-calc-reference` skill and Planner README with the new
  rule and three hand examples; add a judgment-log entry.

## Phase 2 (future, not in scope — needs approval)

Across separate requests the bucket still re-initializes from `initial_soil_pct`,
so a new forecast loses the previous one's progress. Real production use would
persist measured soil water, delivered volume, and the active cycle. This
requires a datastore and is proposed separately; not implemented here.
