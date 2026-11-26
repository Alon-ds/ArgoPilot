---
name: irrigation-calc-reference
description: Use when implementing or reviewing AgroPilot irrigation calculations, crop stages, soil bucket balance, emitter runtime, or hand-calculated planner examples.
---

# Irrigation calculation reference

Read [the preserved FAO-56 research](../../../services/planner-service/docs/research/fao56.md).
Its chapter/table/equation citations distinguish source facts from product choices.
The following are explicit AgroPilot policies, not universal agronomic defaults.

## Inputs and crop curve

| Registry crop ID | Initial/development/mid/late days | Kc initial/mid/end | Fixed root depth (m) |
| --- | --- | --- | --- |
| tomato | 30/40/45/30 | 0.60/1.15/0.80 | 0.70 |
| bell-pepper | 30/35/40/20 | 0.60/1.05/0.90 | 0.50 |

These select Mediterranean Table 11 stages, Table 12 coefficients (tomato end
0.80 within 0.70–0.90), and the lower Table 22 root-depth bounds. Pepper initial
stage selects 30 from 25–30. No climate/wetting adjustment or root growth.

Age is integer date minus planting date, planting day age 0. Before planting:
reject. Initial Kc is constant through age `initial`. Development interpolates
linearly to mid Kc at age `initial+development`; mid stays constant through
`initial+development+mid`. Late interpolates to end Kc at the total stage age.
After that age, **clamp to end Kc indefinitely**; do not infer harvest or restart.
Interpolation follows Chapter 6 Eq. 66; `ETc = ET0*Kc` (mm/day), Eq. 58.

## Daily projection and units

**Day one starts at the plot's `initial_soil_pct` of field capacity (default
100 = a full bucket).** This is a stateless scenario, not measured soil moisture
or an irrigation log: the percent is a grower-entered estimate of today's
dryness, to be replaced by a sensor feed later. Carry water across forecast days
only. Repeating a request never writes state.

1. `C = soil.available_water_mm_per_m * root_m` (mm), Chapter 8 Eq. 82 units.
2. Start `B = C * initial_soil_pct/100`. Each day `P=clamp(B+rain_mm-ET0_mm*Kc, 0, C)`.
3. A cycle **starts** when `P<C/2` (exactly half does not; 1e-9 mm abs / 1e-12
   rel tolerance) and **continues** on later days — even while `P>=C/2` — until
   the bucket is full again. While a cycle is active, required depth `D=C-P`.
4. `count=area_m2/(row_spacing_m*emitter_spacing_m)`; continuous, no rounding.
   `required_litres=D*area_m2` (1 mm over 1 m² = 1 L).
5. **Daily runtime cap.** A drip runs at most `Max_daily_minutes` (default 1440).
   `daily_capacity_litres = count*flow_lph*Max_daily_minutes/60`.
   `scheduled_litres = min(required_litres, daily_capacity_litres)`.
   `run_minutes = Max_daily_minutes` when capped, else `ceil(scheduled_litres/count/flow_lph*60)`
   (≥1 for scheduled>0). Exact rational arithmetic from decimal strings avoids
   binary-float extra minutes at integers.
6. `added_mm=scheduled_litres/area_m2`; `end bucket B=min(C, P+added_mm)`.
   `remaining_litres=max(0,(C-B)*area_m2)`; the cycle closes when it reaches 0.
   The unmet deficit carries into the next day, where rain and ETc are
   re-applied — never subtract a fixed amount of runtime blindly.

This is a simplified Chapter 8 Eq. 85 balance: 100% net efficiency, zero
runoff/capillary rise, full net rainfall, constant roots, no stress model. The
half trigger differs from crop-specific `p` values and Annex 8's dual-Kc
schedule. **The 24 h daily cap and the multi-day carryover are a documented
engineering extension of the simplified bucket policy — not an explicit P2 or
FAO-56 requirement.** `capacity_warning` fires when `daily_capacity_litres <=
ETc*area_m2`: a full pumping day cannot match the crop's own daily use, so the
bucket cannot recover under those inputs.

## Hand calculations

1. **Single-day irrigation (no cap).** Pepper age 47: Kc=.6+(.45*17/35)=.818571…;
   root=.5, soil=10 mm/m, C=5. ET0=4, no rain: ETc=3.274285714…;
   P=1.725714286<2.5. D=3.274285714…; area 100 m² -> 327.4285714 L. Row 1 m /
   emitter .5 m -> count 200; flow 2 L/h -> daily cap 200*2*24=9600 L, so not
   capped; ceil(49.1142857)=50 min; end bucket 5 mm, status COMPLETED.
2. **Multi-day: 24 h cap and carryover.** Mid tomato, soil 100 mm/m, C=70 mm.
   ET0=6, Kc=1.15, rain=0: ETc=6.9. End buckets days 1–5: 63.1,56.2,49.3,42.4,35.5.
   Day 6 projects 28.6<35 -> required D=41.4 mm = 41400 L. For 1000 m², row 1.5 m,
   emitter .4 m, flow 1 L/h: count=1666.666…, daily cap=1666.666…*1*24=40000 L.
   41400>40000, so scheduled=40000 L, run_minutes=1440, end bucket 68.6 mm,
   remaining 1400 L, status SCHEDULED. Day 7 projects 61.7, continues the cycle:
   required 8300 L (8.3 mm) < 40000, ceil(298.8)=299 min, end 70 mm, COMPLETED.
3. **Rain closes the cycle.** Same tomato at B=70, rain=100, ET0=6: P=min(70,
   70+100−6.9)=70; required 0, litres 0, minutes 0, NOT_REQUIRED. Excess 93.1 mm
   drains. Had a cycle been active, rain reaching C closes it (COMPLETED, 0 L).
4. **Insufficient hydraulic capacity.** Pepper (C=41.5 mm) on 100 m², row 5 m /
   emitter 1 m -> count 20; flow .6 L/h -> daily cap 20*.6*24=288 L = 2.88 mm/day.
   ET0=6, Kc≈1.05: ETc≈6.3 mm/day = 630 L/day demand > 288 L capacity, so each
   day pumps the full 1440 min yet the bucket still falls. `capacity_warning`
   fires every active day; `remaining_litres` stays positive and, past day 7,
   the plan reports the cycle continues beyond the forecast horizon.

Missing/invalid data, wrong IDs/coordinates, forecast gaps, or HTTP failures
produce service-specific 503, never fabricated zeros. Stale flags propagate.
