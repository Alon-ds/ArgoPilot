# P2: independent FAO-56 verification

Verified 2026-11-19 against official FAO HTML chapters and the local files linked
below. This is the `/research` verification artifact; it preserves the original
research and engine. Scope: source attribution, selected crop parameters, bucket
policy, and the three hand cases. It is not a field calibration or full service
audit.

## Findings requiring correction in the original research

1. **Incorrect end-season equation citation.** The original research attributes
   both climate adjustments to Eq. 62. Mid-season uses Eq. 62; end-season uses
   Eq. 65, applicable when tabulated end Kc exceeds 0.45.
   [Original claim](fao56.md#directly-tabulated-kc-values);
   [FAO Chapter 6, end-season adjustment](https://www.fao.org/4/x0490E/x0490e0b.htm).
2. **Missing published adjustment bounds.** The original research leaves bounds
   unresolved. FAO explicitly limits adjusted `p` to `0.1 ≤ p ≤ 0.8`.
   [Original discussion](fao56.md#capacity-threshold-and-stress);
   [FAO Chapter 8, readily available water](https://www.fao.org/4/x0490E/x0490e0e.htm).

Both findings were reported immediately in the research task's progress channel.
Neither requires changing the task's chosen unadjusted Kc or half-capacity
policy. No arithmetic error was found in the three cases checked below.
[Task policy](../../../../.agents/skills/irrigation-calc-reference/SKILL.md);
[reviewed implementation](../../engine.py).

## Verified primary-source facts

### Evapotranspiration and crop curve

`ETc = Kc × ETo`, in mm/day, is Chapter 5 Eq. 56 and Chapter 6 Eq. 58.
Standard conditions exclude water stress. Single Kc averages soil evaporation;
Chapter 5 Table 10 identifies dual Kc for daily high-frequency microirrigation.
[FAO Chapter 5, Eq. 56 and Table 10](https://www.fao.org/4/x0490E/x0490e0a.htm);
[FAO Chapter 6, Eq. 58](https://www.fao.org/4/x0490E/x0490e0b.htm).

| Crop | Table 11 stages: initial/development/mid/late (days) | Table 12 Kc: initial/mid/end |
| --- | --- | --- |
| Tomato | 30/40/45/30; April/May, Mediterranean | 0.60/1.15/0.70–0.90 |
| Sweet/bell pepper | 25/30, 35, 40, 20; April/June, Europe and Mediterranean | 0.60/1.05/0.90 |

These are example stages and reference coefficients, requiring local assessment.
The pepper source prints `25/30` and total `125`; choosing 30 gives 125 days,
whereas choosing 25 gives 120. Eq. 66 uses constant initial/mid Kc and linear
development/late interpolation. [FAO Chapter 6, Tables 11–12 and Eq. 66](https://www.fao.org/4/x0490E/x0490e0b.htm).

The engine selects tomato end Kc 0.80, pepper initial length 30, and the listed
tomato stages. Its age-zero convention and indefinite post-season clamp are
explicit task choices. [Reference, crop curve](../../../../.agents/skills/irrigation-calc-reference/SKILL.md#inputs-and-crop-curve);
[engine, CROPS and crop_kc](../../engine.py).

### Roots and water balance

Table 22 gives tomato roots `0.7–1.5 m`, `p=0.40`; pepper `0.5–1.0 m`,
`p=0.30`, near ETc 5 mm/day. Smaller depths may serve scheduling. Eq. 82 is
`TAW=1000(θFC−θWP)Zr`; Eq. 83 is `RAW=p×TAW`.
[FAO Chapter 8, Table 22 and Eqs. 82–83](https://www.fao.org/4/x0490E/x0490e0e.htm).

Eq. 85 is `Dr_i=Dr_previous−(rain−runoff)−I−CR+ETc+DP`; `I` is net
infiltrated depth. Eq. 86 bounds depletion to `[0,TAW]`. Eq. 88 drains excess
above field capacity. No-stress scheduling keeps depletion at or below RAW.
[FAO Chapter 8, Eqs. 85–88 and forecasting irrigations](https://www.fao.org/4/x0490E/x0490e0e.htm).

### Annex 8 comparison

Annex 8 is a dual-Kc dry-edible-bean spreadsheet, with growing roots and
stage-dependent MAD. It schedules irrigation the next morning using the
preceding day's depletion; it also suppresses irrigation in the final half of
late season. It is not a universal half-capacity refill algorithm.
[FAO Annex 8, opening, Box 8.1 and footnotes 4, 8–11](https://www.fao.org/4/X0490E/x0490e0p.htm).

## Task policy versus FAO

The following implementation statements come from the
[irrigation reference](../../../../.agents/skills/irrigation-calc-reference/SKILL.md#daily-projection-and-units)
and [engine.project](../../engine.py), not inferred FAO prescriptions:

- Each request begins at full capacity `C=available_water_mm_per_m×root_m`.
- Fixed roots are tomato 0.70 m and pepper 0.50 m.
- Projected storage is `B*=min(C,B+rain−ETo×Kc)`.
- Strictly below `C/2`, refill the same day by `D=C−B*`; equality does not
  trigger, subject to `isclose` tolerances `1e-9 mm` absolute and `1e-12` relative.
- Full rainfall is credited; runoff and capillary rise are zero. No stress
  reduction, climate adjustment, root growth, or application losses are modeled.
- Negative projected storage is retained until refill depth is calculated;
  this is an unmet-demand accounting convention, not physical negative storage.
- Runtime ceiling does not add surplus pumped water to the next day's bucket.

Derived comparison: substituting `Dr=C−B` makes `B<C/2` equivalent to
`Dr>C/2`. Thus the task permits depletion past 50%, versus the tabulated tomato
40% and pepper 30%. It must not be described as implementing crop-specific RAW
or guaranteeing no stress. This follows algebraically from the task trigger and
the cited Table 22 values.

Derived units: 1 mm over 1 m² = 0.001 m³ = 1 L. Therefore
`litres=D×area`, emitter count is `area/(row_spacing×emitter_spacing)`, and
minutes are `ceil(litres/count/flow_lph×60)`. These hydraulic choices and
continuous emitter counts are stated in the
[reference](../../../../.agents/skills/irrigation-calc-reference/SKILL.md#daily-projection-and-units).

## Independent numerical verification

All following numbers are independently derived from the
[three reference cases](../../../../.agents/skills/irrigation-calc-reference/SKILL.md#three-hand-calculations),
then compared with the actual [engine.project](../../engine.py) output.
Python `fractions.Fraction` provided exact expected arithmetic. The planner's
existing `.venv/bin/python` ran an inline harness, with bytecode writes disabled;
no test file was added. All three comparisons passed.

### 1. Tomato threshold and refill

At mid-season, `C=100×0.70=70 mm`; daily `ETc=6×1.15=6.9 mm`.
Start at 70 with zero rain and remain in mid-season for all six days.

| Day | Projected bucket (mm) | Irrigation (mm) | End bucket (mm) |
| --- | ---: | ---: | ---: |
| 1 | 63.1 | 0 | 63.1 |
| 2 | 56.2 | 0 | 56.2 |
| 3 | 49.3 | 0 | 49.3 |
| 4 | 42.4 | 0 | 42.4 |
| 5 | 35.5 | 0 | 35.5 |
| 6 | 28.6 | 41.4 | 70 |

For 1000 m², 1.5 m rows, 0.4 m emitter spacing, 1 L/h emitters:
`count=5000/3`; `litres=41400`; exact minutes `7452/5=1490.4`;
ceiling **1491 minutes**. Engine matched all six buckets, volume, and runtime.

### 2. Rain saturation

Start at 70 mm; rain 100 mm; ETc 6.9 mm.
`B*=min(70,70+100−6.9)=70 mm`.
Derived drainage is `93.1 mm`; irrigation **0 L, 0 minutes**; end bucket
**70 mm**. Engine matched; drainage is inferred because its output does not
expose a drainage field.

### 3. Pepper interpolation and ceiling

Age 47 gives `Kc=0.60+(1.05−0.60)×17/35=573/700≈0.818571429`.
`C=10×0.5=5 mm`; `ETc=4×573/700=573/175≈3.274285714 mm`.
Projected storage `302/175≈1.725714286 mm` is below 2.5 mm.
Refill `D=573/175 mm`; for 100 m², volume
`2292/7≈327.428571429 L`. With 1 m rows, 0.5 m spacing and 2 L/h emitters:
`count=200`; exact minutes `1719/35≈49.114285714`; ceiling **50 minutes**.
End bucket **5 mm**. Engine matched Kc, volume, runtime and bucket.

## Review limits

The three cases validate the prescribed simplified arithmetic, not Annex 8
numerical equivalence or field suitability. Upstream validation, service HTTP
behavior, and all possible floating-point boundaries were outside this review.
The original research's `Dr≤RAW` scheduling wording is not an inequality error:
the official Chapter 8 forecasting section uses that inequality to express the
no-stress scheduling limit. [FAO Chapter 8](https://www.fao.org/4/x0490E/x0490e0e.htm).
