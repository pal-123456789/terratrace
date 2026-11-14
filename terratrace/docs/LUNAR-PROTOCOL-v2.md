# Lunar panel v2 — the corrective protocol

**Status: CORRECTED EXPLORATORY REANALYSIS.** The same data was examined in v1 before this
correction existed. This is not independent confirmation, not a new pre-registration, and not a
fresh experiment. For those you need genuinely held-out data and a protocol frozen before the data
are looked at.

## What was wrong, measured

The first lunar panel claimed "exact common support and matched footprint". It did not have it.
Reproduced from the shipped code and data:

| requested | Moon | Earth | equal? |
|---|---|---|---|
| 500 m | 500 m · 32 cells · **16.000 km** | 510 m · 31 cells · **15.810 km** | no |
| 750 m | 750 m · 21 cells · 15.750 km | 750 m · 21 cells · 15.750 km | yes, by luck |
| 1000 m | 1000 m · 16 cells · **16.000 km** | 990 m · 16 cells · **15.840 km** | no |

and the written record said `cells=[32, 32], support_m=500.0` for **both** sides.

Two independent causes. First, each body aggregated by its own integer factor — 500/5 = 100 on the
Moon, `round(500/30)` = 17 on Earth, giving 510 m. Second, `centre_square()` cropped to
`min(n, h, w)`, so a requested 32 × 32 Earth grid became 31 × 31 without saying so.

This is the same failure class the project already withdrew a Mars claim over: a comparison whose
footprints do not match, reported as though they did. It is a defect in the *comparison*, not in the
terrain, so no amount of descriptor care would have fixed it.

## What v2 does instead

Both bodies are warped **from their native source straight into an exact destination grid** in the
body's local azimuthal-equidistant CRS, with area-weighted (`average`) resampling.
`terratrace/common_grid.py` is the implementation and its docstring carries the same measurements.

AEQD's defining property — the distance from the projection centre to any projected point *is* the
geodesic distance, validated in `scripts/reproject_analytic_check.py` — is what makes "500 m" mean
500 m of ground on the Moon and on Earth, rather than a number copied between them.

The lunar side needs the warp too, and this is not a detail. The LOLA products are **polar
stereographic from the south pole**, so a local ground grid centred on a site is *rotated* relative
to the tile, and a nominal 500 m cell there is up to **500.80 m of ground** at Site20 (scale factor
`k = 1/cos²(θ/2)` at 138.75 km from the pole). Aggregating in the source projection would compare
500.80 m lunar cells against 500.00 m terrestrial ones.

### The footprint, and why it is 9000 m and not 15 km

15 km was the obvious choice and it does not fit. Because a local ground grid is rotated relative to
the tile, its corners reach `half_side · √2` from the centre, so the largest rotated square inside a
16 km tile is 11.27 km (14.81 km on the single 21 km tile):

| site | tile half-extent | max safe footprint |
|---|---|---|
| Site01, Site07, Site20 | 8.00 km | 11.27 km |
| Site23 | 10.50 km | 14.81 km |

9000 m is the largest value that (a) fits every site with margin for the warp and (b) is divisible
by all three supports, giving exactly **18 × 18, 12 × 12 and 9 × 9** cells at exactly 500, 750 and
1000 m — a common multiple every time, because 9000/500 = 18, 9000/750 = 12, 9000/1000 = 9.

### What is deliberately unchanged

The three declared axes, the seven Earth candidates, the six lunar sites, and the Pareto decision
rule. Changing those at the same time would have confounded a correction with a new analysis.

## Frozen before the run

`config/lunar_panel_v2.yml` was written and committed **before** the corrected run, and it carries
the falsifiers declared in advance:

* if the single surviving candidate at any support is no longer `earth_nevada_basin`, the v1 headline
  was an artefact of the footprint mismatch and must be reported as such;
* if the survivor set differs between supports, that is a scale-dependent result and is reported as
  such rather than collapsed;
* if no candidate is non-dominated, the honest output is the engine's INDETERMINATE path;
* the result is not to be preserved because it was the previous headline.

**Honest note on ordering.** The config was committed before the run; *this document* was written
immediately after it, describing the same pre-committed decisions. It is not itself a
pre-run artifact, and it should not be cited as one. This is the v3 lesson — pre-specified is not
pre-registered — applied rather than repeated.

## Result

Every comparison now runs on equal ground: 18 × 18 cells of exactly 500 m, 12 × 12 of 750 m and
9 × 9 of 1000 m, **9000 m on every unit**, enforced by `common_grid.assert_comparable()` before any
ranking. Full valid coverage on every window.

The descriptors moved materially — Site01's mean slope went from 10.3° to 9.06° at 750 m, because the
window is now 9 km instead of 15.75 km and the cell is exact. **The conclusion did not move:**
`earth_nevada_basin` remains the single non-dominated candidate at all three supports, and the
six-realisation error ensemble reproduces the point estimate's layer-1 set 6/6 at every support.

**The defect therefore did not drive the headline result. It had to be fixed regardless**, because
the panel's claim of a matched footprint was false, and the same defect is what forced the
withdrawal of the Mars claim in v2.

## The redundancy finding, which is the more important result

The three declared axes turn out to be **one axis measured three ways**:

| pair | Pearson (500 m) | Spearman (500 m) | Pearson (1000 m) |
|---|---|---|---|
| mean slope · mean 3×3 relief | **+1.000** | **+1.000** | +0.998 |
| mean slope · elevation std | +0.998 | **+1.000** | +0.999 |
| mean 3×3 relief · elevation std | +0.998 | **+1.000** | +0.997 |

and dropping any single axis leaves the non-dominated set unchanged at every site and every support.

So "non-dominated on three axes at every support" is, on this panel, a **one-dimensional** statement:
the candidates are ordered along a single roughness/relief gradient, and the survivor is the least
rough of the seven relative to each lunar reference. Three correlated roughness measures must not be
read as three independent dimensions of geological evidence, and the panel's robustness is explained
by that — a one-dimensional ordering is far more stable than a genuine three-dimensional Pareto
front would be.

This is recorded in the artifact itself (`axis_correlations`, `leave_one_axis_out` per site per
support), not only in prose.

**Boundary.** An absolute adequacy statement is still not available. The 50 % worst-axis distance
remains a descriptive label, not a validated threshold, and `LUNAR-DEMONSTRATION.md` says so.
