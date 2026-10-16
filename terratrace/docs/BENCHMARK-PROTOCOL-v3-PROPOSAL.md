# TerraTrace Benchmark — Protocol v3 PROPOSAL (not frozen)

**Status: PROPOSED 2026-10-16. Not frozen. Nothing here has been run.** It becomes a protocol only when
(1) the remaining coordinates are verified, (2) the engine extensions below are built and tested, and
(3) it is committed on its own **before** any v3 download is analysed. Until then it can still change.

## Why v3 (from the v2 result)

Protocol v2 (`RESULTS-v2.md`) withdrew the Craters-of-the-Moon analog claim: under matched footprints
and supports ≥ MOLA's effective resolution the engine abstained everywhere, and Craters was the nearest
candidate for a cratered highland as readily as for volcanic plains. The leading explanation —
**a smoothness / shortlist effect** (Martian terrain at km scale is smoother than all three Earth tiles,
and Craters is the smoothest) — is *consistent* with v2 but was **never tested directly**. v2 also had
low power (12–16 cells per side) and one over-broad rule (H3).

## The question

When Earth candidates include terrains that are **as smooth as Craters but not volcanic**, does a
basaltic lava plain still match Martian volcanic plains better — and does that advantage disappear for
Martian highlands?

- **S (shortlist / smoothness):** the nearest Earth candidate tracks km-scale roughness, not origin; a
  smooth non-volcanic control is non-dominated alongside, or instead of, the basaltic plains.
- **V (volcanic specificity):** basaltic-plains candidates dominate the smooth non-volcanic controls for
  Martian volcanic plains, but not for Martian highlands.

Either outcome is informative; neither is assumed.

## Design changes vs v2

| | v2 | v3 (proposed) |
|---|---|---|
| Common extent | 24 km (limited by cached tiles) | **60 km** (new downloads) |
| Cells per side @ 1.5 / 2 / 3 km | 16 / 12 / — | **40 / 30 / 20** |
| Earth candidates | 3 | **7, each with a stated role** (below) |
| Smoothness-matched non-volcanic controls | none | **2** (the direct test of S) |
| Mars references | 7 (all now *seen*) | v2's 7 as **calibration (exploratory)** + **fresh** confirmatory references |
| H3-type rule | fired on any change | must distinguish **reversed** from **stabilised** (lesson from v2) |

## Earth candidates (COP30 via OpenTopography; sized by the engine's own preflight)

| id | role | centre used | source of centre | preflight (66 km read) |
|---|---|---|---|---|
| earth_snake_river_plain | basaltic plains (contains Craters of the Moon) | 43.35 N, 113.45 W | existing Craters tile centre | ~18 MB |
| earth_harrat_khaybar | basaltic volcanic field | 25.5 N, 40.0 E | Smithsonian GVP field centroid | ~18 MB |
| earth_odadahraun | basaltic lava plain, Iceland | 65.23 N, 16.54 W | Wikidata / National Land Survey of Iceland | ~18 MB |
| earth_nullarbor | **smooth non-volcanic control** (limestone plain) | 30.3 S, 129.0 E | Wikipedia | ~18 MB |
| earth_llano_estacado | **smooth non-volcanic control** (sedimentary high plain) | 33.0 N, 102.0 W | Wikipedia | ~18 MB |
| earth_nevada_basin | near-miss (basin-and-range), wider re-fetch | 36.2 N, 115.6 W | existing tile centre | ~18 MB |
| earth_andean_volcano | rough control (stratovolcano), wider re-fetch | 0.05 S, 78.45 W | existing tile centre | ~18 MB |

**Total ≈ 129 MB, 33.8 Mpx** (all seven pass `preflight_unit`, no warnings). COP30 is a surface model
(includes vegetation/buildings); the chosen areas are sparsely built and vegetated — stated limitation.

## Mars references (MOLA, already on disk — no download)

| id | class | status | centre | verified? |
|---|---|---|---|---|
| v2's 7 references | as in v2 | **exploratory / calibration** (seen) | as in v2 config | — |
| mars_arcadia | volcanic plains | confirmatory | 47.2 N, 184.3 E | yes — USGS nomenclature via Wikipedia |
| mars_lunae | volcanic (ridged) plains | confirmatory | ~10.8 N, ~293.5 E | **NO — verify in the USGS Gazetteer before freezing** |
| mars_solis | volcanic plains | confirmatory | ~25.9 S, ~270.2 E | **NO — verify before freezing** |
| mars_terra_cimmeria | contrast: cratered highland | confirmatory | 34.7 S, 145.0 E | yes — Wikipedia |
| mars_arabia_terra | contrast: cratered/eroded highland | confirmatory | ~20 N, 30 E | yes — Wikipedia/HiRISE (centre approximate) |

Coordinates corrected during verification (recorded for transparency): Nullarbor 31.0 S → **30.3 S**;
Harrat Khaybar → **25.5 N, 40.0 E**; Arabia Terra 354 E → **30 E**; Ódáðahraun → **65.23 N, 16.54 W**.

## Engine work required before freezing

1. **Candidate classes + a class-dominance expectation** in `confirmation.py` (e.g. `basaltic` vs
   `smooth_control`), so S and V can be evaluated as pre-declared rules rather than read off by eye.
2. **H3 rule fix:** classify resolution-control changes as `reversed` (different nearest unit) vs
   `stabilised` (same nearest unit, INDETERMINATE → RECOMMEND) vs `destabilised`.
3. A config v3 + fetch list generated from the table above, run through `--dry-run` preflight first.

## Draft decision rules (to be finalised at freeze — not yet binding)

- **V supported** if, for ≥ 2 of 3 fresh volcanic-plains references, at every honest support some
  basaltic candidate Pareto-dominates both smooth controls, **and** for ≥ 1 of 2 fresh highland references
  it does not.
- **S supported** if, for ≥ 2 of 3 fresh plains references, a smooth control is in Pareto layer 1 at every
  honest support.
- Both, neither, or ERROR/low-power → reported as such; no rescue edits (same stopping rule as v2).

## Sources consulted for coordinates

Arcadia Planitia — https://en.wikipedia.org/wiki/Arcadia_Planitia ; Terra Cimmeria —
https://en.wikipedia.org/wiki/Terra_Cimmeria ; Arabia Terra — https://the-martian.fandom.com/wiki/Arabia_Terra
and https://hirise.lpl.arizona.edu/PSP_006885_1975 ; Harrat Khaybar — https://volcano.si.edu/volcano.cfm?vn=231060 ;
Nullarbor Plain — https://en.wikipedia.org/wiki/Nullarbor_Plain ; Ódáðahraun — https://www.wikidata.org/wiki/Q292913 ;
Llano Estacado — https://en.wikipedia.org/wiki/Llano_Estacado .
