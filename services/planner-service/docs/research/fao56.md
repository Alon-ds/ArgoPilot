# FAO-56 research: daily drip-irrigation planning

**Scope.** This is a research note for a future deterministic planner.  It does
not prescribe AgroPilot defaults and contains no application implementation.
The primary source is FAO Irrigation and Drainage Paper 56 (Allen *et al.*,
1998), specifically [Chapter 5](https://www.fao.org/4/x0490E/x0490e0a.htm),
[Chapter 6](https://www.fao.org/4/x0490E/x0490e0b.htm),
[Chapter 8](https://www.fao.org/4/x0490E/x0490e0e.htm), and
[Annex 8](https://www.fao.org/4/X0490E/x0490e0p.htm).  Citations below name
the FAO chapter, table, equation, or annex location so a value can be traced.

## Status of values and choices

- **FAO value** means a value, definition, or method stated by FAO-56.
- **Derived unit conversion** is arithmetic, not an agronomic parameter.
- **Planner decision required** means the paper does not supply a universal
  value; the planner must receive it, select a documented policy, or defer a
  recommendation.  It is not an assumption made by this document.

FAO's tabulated coefficients and stage lengths are reference information, not
site calibration: Table 11 calls its lengths examples and asks for local
observations where possible; Kc table values describe standard, well-watered
conditions and need climate/wetting adjustment where applicable. [Chapter 6,
Table 11 and text immediately following it](https://www.fao.org/4/x0490E/x0490e0b.htm);
[Chapter 5, standard-condition definition](https://www.fao.org/4/x0490E/x0490e0a.htm).

## 1. Crop water requirement from ET0 and Kc

### Standard (non-stressed) crop water use

**FAO method.** Under standard conditions, daily crop evapotranspiration is

\[
ET_c = K_c ETo
\]

where `ETc` and `ETo` are mm/day and `Kc` is dimensionless. This is FAO-56
Equation 56 (repeated as Equation 58 in Chapter 6). `ETo` is reference crop
evapotranspiration; `Kc` incorporates crop characteristics and the averaged
soil-evaporation effect. [Chapter 5, Eq. 56](https://www.fao.org/4/x0490E/x0490e0a.htm);
[Chapter 6, Eq. 58](https://www.fao.org/4/x0490E/x0490e0b.htm).

For a daily planner that accepts ETo, this is the direct water-depth demand
before rainfall, irrigation-system losses, runoff, capillary rise, deep
percolation, or water stress are accounted for. FAO describes the single-Kc
method as time-averaging soil evaporation; it is suitable for planning/basic
schedules, while daily high-frequency microirrigation is a stated use case for
the dual-Kc method. [Chapter 5, Table 10 and single/dual-Kc discussion](https://www.fao.org/4/x0490E/x0490e0a.htm).

### Growth stages and the daily Kc curve

**FAO method.** The four stages are initial (planting to about 10% ground
cover), development (10% cover to effective full cover), mid-season (effective
full cover to start of maturity), and late season (maturity to harvest/full
senescence). [Chapter 5, “Crop growth stages”](https://www.fao.org/4/x0490E/x0490e0a.htm).

For the single-Kc curve, use `Kc_ini` throughout the initial stage, linearly
interpolate from `Kc_ini` to `Kc_mid` in development, use `Kc_mid` in
mid-season, and linearly interpolate from `Kc_mid` to `Kc_end` in late season.
FAO gives the numerical interpolation expression as Equation 66. [Chapter 6,
“Numerical determination of Kc”, Eq. 66](https://www.fao.org/4/x0490E/x0490e0b.htm).

**Planner decision required.** The planting date (or observed stage dates),
which Table 11 row matches the cultivar/location/season, and whether to apply
FAO climate and wetting adjustments must be explicit inputs or documented
configuration. Do not silently select a Table 11 row.

### Units and volume conversion

| Quantity | Unit used by FAO-56 | Deterministic use |
| --- | --- | --- |
| `ETo`, `ETc`, precipitation `P`, infiltrated irrigation `I`, runoff `RO`, capillary rise `CR`, deep percolation `DP`, depletion `Dr`, `TAW`, `RAW` | mm/day or mm for a daily amount | Keep all water-balance terms as an equivalent depth over the **whole field area**. [Chapter 8, Eq. 85 definitions](https://www.fao.org/4/x0490E/x0490e0e.htm) |
| `Kc`, `Kcb`, `Ke`, `Ks`, `p`, MAD | dimensionless | Do not add units. [Chapter 5, Eqs. 56–57](https://www.fao.org/4/x0490E/x0490e0a.htm); [Chapter 8, Eq. 84 definition](https://www.fao.org/4/x0490E/x0490e0e.htm) |
| Root depth `Zr` | m | Use with volumetric soil water contents in Eq. 82. [Chapter 8, Eq. 82](https://www.fao.org/4/x0490E/x0490e0e.htm) |
| `theta_FC`, `theta_WP` | m³/m³ | Field-capacity and wilting-point volumetric water contents. [Chapter 8, Eq. 82 definitions](https://www.fao.org/4/x0490E/x0490e0e.htm) |

**Derived unit conversion.** `1 mm` applied over `1 m²` is `1 litre`; therefore
`volume_litres = depth_mm × area_m2`. This is dimensional arithmetic
(`0.001 m × 1 m² = 0.001 m³ = 1 L`), not a FAO crop coefficient. The result is
a **net field-area volume** when `depth_mm` is `I` in the FAO balance.

**Planner decision required.** Gross water pumped or scheduled at emitters
requires an application-efficiency/distribution policy and hydraulic data;
FAO-56 Chapter 8 defines `I` as the net depth that infiltrates the soil, not a
universal gross-efficiency factor. [Chapter 8, Eq. 85 definitions](https://www.fao.org/4/x0490E/x0490e0e.htm).

## 2. Tomato and bell pepper coefficients and stages

### Directly tabulated Kc values

The following are **FAO values** from Chapter 6, Table 12, for average Kc
under the table's standard climatic condition (sub-humid, `RHmin ≈ 45%`, wind
about `2 m/s`) and typical irrigation/soil wetting.

| Crop | `Kc_ini` | `Kc_mid` | `Kc_end` | maximum crop height |
| --- | ---: | ---: | ---: | ---: |
| Bell/sweet pepper | 0.60 | 1.05 | 0.90 | 0.70 m |
| Tomato | 0.60 | 1.15 | 0.70–0.90 | 0.60 m |

Source: [Chapter 6, Table 12, Solanaceae rows](https://www.fao.org/4/x0490E/x0490e0b.htm). The Table 12 note says `Kc_ini` can rise substantially
with frequent wetting (approaching 1.0–1.2), and refers to the wetting-based
procedures/dual method for greater accuracy. [Chapter 6, Table 12 note 1](https://www.fao.org/4/x0490E/x0490e0b.htm).

FAO permits climate adjustment of `Kc_mid` and `Kc_end` using wind, minimum
relative humidity, and height (Chapter 6 Eq. 62); the tabulated values should
not be treated as invariant climate constants. [Chapter 6, “Kc mid” climate
adjustment, Eq. 62](https://www.fao.org/4/x0490E/x0490e0b.htm).

### Directly tabulated stage-length examples

These are **FAO Table 11 examples**, in days ordered `initial / development /
mid-season / late-season`:

| Crop | Stage lengths | Total | Planting period and region in Table 11 |
| --- | --- | ---: | --- |
| Bell/sweet pepper | 25–30 / 35 / 40 / 20 | 125 | April/June, Europe and Mediterranean |
| Bell/sweet pepper | 30 / 40 / 110 / 30 | 210 | October, arid region |
| Tomato | 30 / 40 / 40 / 25 | 135 | January, arid region |
| Tomato | 35 / 40 / 50 / 30 | 155 | April/May, California, USA |
| Tomato | 25 / 40 / 60 / 30 | 155 | January, California desert, USA |
| Tomato | 35 / 45 / 70 / 30 | 180 | October/November, arid region |
| Tomato | 30 / 40 / 45 / 30 | 145 | April/May, Mediterranean |

Source: [Chapter 6, Table 11, Solanaceae rows](https://www.fao.org/4/x0490E/x0490e0b.htm). These rows are alternatives tied to their stated planting
period/region; none is a default for AgroPilot.

For the root-zone model, Table 22 gives bell pepper maximum effective rooting
depth `0.5–1.0 m`, `p = 0.30`, and tomato `0.7–1.5 m`, `p = 0.40` (the `p`
values apply around `ETc ≈ 5 mm/day`). [Chapter 8, Table 22](https://www.fao.org/4/x0490E/x0490e0e.htm). Table 22 says the smaller `Zr` values may be
used for irrigation scheduling and the larger values for stress/rainfed
modelling where there is no restricting soil layer. [Chapter 8, Table 22 note
1](https://www.fao.org/4/x0490E/x0490e0e.htm).

## 3. Root-zone soil-water bucket

### Capacity, threshold, and stress

**FAO method.** Total available water in the effective root zone is

\[
TAW = 1000(\theta_{FC}-\theta_{WP})Z_r
\]

in mm (FAO Eq. 82). Readily available water is

\[
RAW = p\,TAW
\]

in mm (FAO Eq. 83). [Chapter 8, Eqs. 82–83](https://www.fao.org/4/x0490E/x0490e0e.htm).

FAO gives an optional demand adjustment for the depletion fraction:

\[
p = p_{Table\ 22} + 0.04(5 - ET_c)
\]

with `ETc` in mm/day. [Chapter 8, Table 22 note 2](https://www.fao.org/4/x0490E/x0490e0e.htm). **Planner decision required:** whether to use this adjustment,
and the bound/validation policy, must be specified; this note does not invent
one.

Represent stored water as root-zone depletion `Dr`: `0` means field capacity;
increasing `Dr` means a drier root zone. FAO constrains it to
`0 ≤ Dr ≤ TAW`. [Chapter 8, Eqs. 85–86 and surrounding text](https://www.fao.org/4/x0490E/x0490e0e.htm). If `Dr ≤ RAW`, `Ks = 1`; for `Dr > RAW`,

\[
K_s = \frac{TAW-D_r}{TAW-RAW}.
\]

This is FAO Eq. 84. [Chapter 8, Eq. 84](https://www.fao.org/4/x0490E/x0490e0e.htm).

For a single Kc, stressed demand is `ETc_adj = Ks × Kc × ETo` (Eq. 81). For
the dual method it is `ETc_adj = (Ks × Kcb + Ke) × ETo` (Eq. 80); FAO calls the
dual application more valid because stress reduces transpiration rather than
soil evaporation. [Chapter 8, Eqs. 80–81](https://www.fao.org/4/x0490E/x0490e0e.htm).

### Daily root-zone balance

**FAO method.** At the end of day `i`:

\[
D_{r,i}=D_{r,i-1}-(P-RO)_i-I_i-CR_i+ET_{c,i}+DP_i.
\]

This is FAO Eq. 85. Rainfall, infiltrated irrigation and capillary rise reduce
depletion; evapotranspiration and deep percolation increase it. All terms are
mm over the whole field area. [Chapter 8, Eq. 85 and definitions](https://www.fao.org/4/x0490E/x0490e0e.htm).

Initial depletion can be measured/estimated as

\[
D_{r,i-1}=1000(\theta_{FC}-\theta_{i-1})Z_r
\]

(FAO Eq. 87); after heavy rain or irrigation, FAO permits assuming `Dr ≈ 0`.
[Chapter 8, Eq. 87](https://www.fao.org/4/x0490E/x0490e0e.htm).

When a same-day water input would raise the root zone above field capacity,
FAO's simple balance sends the excess to deep percolation:

\[
DP_i = \max\{(P_i-RO_i)+I_i-ET_{c,i}-D_{r,i-1},\ 0\}.
\]

This is Eq. 88; otherwise `DP = 0`. [Chapter 8, Eq. 88](https://www.fao.org/4/x0490E/x0490e0e.htm).

**Planner decision required.** The service needs measured/characterised
`theta_FC`, `theta_WP`, initial `Dr`, effective `Zr` (including its growth),
rainfall, runoff, and whether shallow groundwater makes `CR` nonzero. FAO says
`CR` can normally be zero when the water table is more than about 1 m below the
root-zone bottom; it does not supply site data. [Chapter 8, capillary-rise
section](https://www.fao.org/4/x0490E/x0490e0e.htm).

## 4. What Annex 8 does day by day

Annex 8 is a **dual-Kc spreadsheet example for dry edible bean**, not tomato or
pepper calibration. It combines the Chapter 7 dual-coefficient calculation
with the Chapter 8 daily root-zone balance and triggers from management
allowed depletion (MAD). [Annex 8, opening paragraphs](https://www.fao.org/4/X0490E/x0490e0p.htm).

For each date, its deterministic sequence is:

1. Determine stage and linearly interpolate daily `Kcb` in development and
   late season. Annex 8 maps this to Chapter 6 Eq. 66. [Annex 8, Box 8.1 and
   footnote 2](https://www.fao.org/4/X0490E/x0490e0p.htm).
2. With daily weather, crop height, wetted fraction, topsoil depletion and
   wetting events, calculate `Kcmax`, `Kr`, `Ke`, then `Kc = Kcb + Ke` and
   `ETc = Kc × ETo`; those `Ke` equations are Chapter 7 inputs, not a
   substitute for the single-Kc values above. [Annex 8, Box 8.1; Annex 8
   footnotes 5–7](https://www.fao.org/4/X0490E/x0490e0p.htm).
3. Grow the effective root depth without allowing it to decrease; Annex 8's
   primary example makes growth proportional to the rise in `Kcb`, with
   `Zr_max` reached by mid-season. It also presents time-based interpolation
   as another possible approach. [Annex 8, Eqs. 8-1 to 8-3 and discussion](https://www.fao.org/4/X0490E/x0490e0p.htm).
4. Recompute `TAW`, the allowed depletion (`MAD × TAW`), and a first end-of-day
   `Dr` assuming no drainage and non-stressed demand. Compute `Ks` when the
   threshold is exceeded, recalculate stressed ET, determine deep percolation,
   then save the final end-of-day `Dr`. [Annex 8, Box 8.1, footnotes 8–12](https://www.fao.org/4/X0490E/x0490e0p.htm).
5. If end-of-previous-day depletion exceeds the permitted threshold, schedule
   an irrigation at the beginning of the next day. The example's net amount
   equals the preceding depletion, so it refills to field capacity. [Annex 8,
   paragraphs 7–9 and footnote 4](https://www.fao.org/4/X0490E/x0490e0p.htm).

The Annex assumes rain and irrigation early in the day, zero rainfall runoff,
same-day drainage of excess precipitation, and a net irrigation depth equal to
the preceding depletion. It explicitly says these assumptions may not hold and
should be changed for local conditions. [Annex 8, paragraphs 7–9](https://www.fao.org/4/X0490E/x0490e0p.htm). It also notes that the next-day trigger
can cause small stress on the preceding day. [Annex 8, final discussion](https://www.fao.org/4/X0490E/x0490e0p.htm).

## 5. Deterministic planner specification: required equations and inputs

### Minimum single-Kc daily model

This is the smallest FAO-consistent deterministic model when daily `ETo` and a
single crop coefficient curve are available:

1. Obtain crop/stage dates and `Kc_ini`, `Kc_mid`, `Kc_end`; calculate daily
   `Kc_i` by the piecewise stage curve (Chapter 6 Eq. 66).
2. Calculate potential `ETc_i = Kc_i × ETo_i` (Chapter 6 Eq. 58).
3. Calculate `TAW_i`, `RAW_i`, `Ks_i`, and `ETc_adj,i` (Chapter 8 Eqs.
   82–85 and 81), then update `Dr` with the daily water balance (Eq. 85).
4. Select the next irrigation time/depth using an explicitly supplied policy.
   FAO's no-stress guidance is to irrigate before or when `Dr ≤ RAW`, with net
   irrigation no more than depletion to avoid deep percolation. [Chapter 8,
   “Forecasting or allocating irrigations”](https://www.fao.org/4/x0490E/x0490e0e.htm).
5. Convert a chosen net depth to litres as `depth_mm × area_m2`.

### Extra inputs for a daily drip/dual-Kc model

FAO identifies the dual method as appropriate for real-time high-frequency
microirrigation because it separately models transpiration (`Kcb`) and soil
evaporation (`Ke`). [Chapter 5, Table 10](https://www.fao.org/4/x0490E/x0490e0a.htm). A faithful Annex 8-style implementation additionally needs
daily weather used for dual-Kc adjustment, wetting fraction, evaporation-layer
parameters/depletion, precipitation timing, and an explicit root-growth model.
Those are inputs/choices; they cannot be reliably inferred from crop name and
area alone. [Annex 8, user-entered inputs and Box 8.1](https://www.fao.org/4/X0490E/x0490e0p.htm).

### Unresolved product decisions — intentionally not invented

- Whether the first release uses the single-Kc bucket or the more data-heavy
  dual-Kc drip model.
- Site/cultivar-specific stage dates and the exact Table 11 row or observed
  stages for each planting.
- Soil hydraulic inputs, initial depletion, rainfall/runoff source, groundwater
  treatment, root-growth rule, and the irrigation trigger/refill target.
- Whether to adjust `p` by daily ETc and what validated bounds apply.
- How to turn net infiltrated depth into gross valve/emitter runtime; this needs
  system-specific application efficiency and flow data.

These omissions are deliberate: FAO-56 supplies equations and example
assumptions, but it does not justify universal values for a particular field or
irrigation installation.

## Source note

FAO's online edition warns that its OCR/scanned electronic text can contain
discrepancies from the printed edition. Formula/table verification for any
production implementation should therefore retain the cited FAO edition and
test against Annex 8's published example. [FAO-56 title page](https://www.fao.org/4/x0490E/x0490e00.htm); [Annex 8, verification purpose](https://www.fao.org/4/X0490E/x0490e0p.htm).
