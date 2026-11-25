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
2. Start `B = C * initial_soil_pct/100`. Each day `P=min(C, B+rain_mm-ET0_mm*Kc)`; excess drains.
3. If `P<C/2`, irrigation depth `D=C-P`, end bucket `C`; otherwise `D=0`, end `P`.
   Exactly half does not trigger. Float equality uses 1e-9 mm absolute/1e-12
   relative tolerance. Do not clamp negative P before calculating D: this would
   discard unmet daily demand.
4. `litres=D*area_m2` (1 mm over 1 m² = 1 L).
5. `count=area_m2/(row_spacing_m*emitter_spacing_m)`; continuous geometric
   estimate, no rounding of emitter count.
6. `run_minutes=ceil(litres/count/flow_lph*60)`; zero when D=0, at least 1 for D>0.
   Use exact rational arithmetic from decimal-string litres, area, spacing and
   flow for this conversion, avoiding binary-float extra minutes at integers.

This is a simplified Chapter 8 Eq. 85 balance: 100% net application efficiency,
zero runoff/capillary rise, full net rainfall, constant roots, no stress model.
The mandated half trigger and same-day refill differ from crop-specific `p`
values and Annex 8's dual-Kc bean example/next-day schedule. Bucket uses net
depth; rounding runtime does not feed extra pumped water into tomorrow's bucket.

## Three hand calculations

1. **Threshold and refill.** Mid tomato, soil 100 mm/m: C=70 mm. ET0=6,
   Kc=1.15, rain=0: ETc=6.9. End buckets days 1–5 are
   63.1,56.2,49.3,42.4,35.5. Day 6 projects 28.6<35, so D=41.4 mm.
   For 1000 m², row 1.5 m, emitter 0.4 m, flow 1 L/h:
   count=1666.666…; volume=41400 L; minutes=ceil(1490.4)=1491; end=70.
2. **Rain saturation.** Same tomato at B=70, rain=100, ET0=6: P=min(70,
   70+100−6.9)=70; D=0, litres=0, minutes=0. Excess 93.1 mm drains.
3. **Pepper interpolation and ceiling.** Age 47: Kc=.6+(.45*17/35)=.818571…;
   root=.5, soil=10 mm/m, C=5. ET0=4, no rain: ETc=3.274285714…;
   P=1.725714286<2.5. D=3.274285714…; area100 m² gives327.4285714 L.
   Row1 m/emitter.5 m -> count200; flow2 L/h -> ceil(49.1142857)=50 min;
   end bucket5 mm.

Missing/invalid data, wrong IDs/coordinates, forecast gaps, or HTTP failures
produce service-specific 503, never fabricated zeros. Stale flags propagate.
