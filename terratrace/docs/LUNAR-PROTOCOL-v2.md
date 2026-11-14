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

The three declared axes turn out to be **one axis measured three ways**, and this is now a derived
result rather than a correlation. `scripts/dependence_audit.py` produces
`artifacts/dependence/dependence_audit.json`.

### It has a mechanism, not just a coefficient

`slope_deg` is `degrees(arctan(|∇z|))` from central differences, and `relief(window=3, alpha=0)` is
the 3×3 max-minus-min. On a locally planar surface with gradient `(a, b)` and cell spacing `d`, the
max-minus-min over the stencil is `2d(|a| + |b|)` — the per-axis extents **add**, they do not
compose — while `2d·tan(slope) = 2d·√(a²+b²)`. So

    relief = 2 d · tan(slope) · ρ,        ρ = (|a| + |b|) / √(a² + b²)  ∈ [1, √2]

**ρ depends only on the gradient's direction, not its magnitude or the cell size.** The two
descriptors are therefore functions of the same quantity and cannot be independent evidence. The
relation was checked against the engine's own `slope_deg` and `relief` on synthetic planes at six
gradients: worst error **4.4 × 10⁻¹⁶ m** in relief and **1.4 × 10⁻¹⁴ deg** in slope, with observed
ρ spanning exactly **[1.0000, 1.4142]** — the provable band, attained at the axis-aligned and
diagonal orientations respectively.

### The panel agrees with the algebra

Over the pool the frontier actually decides between (the seven Earth candidates), at every support:

| support | effective rank | participation ratio | condition number | Pearson slope·relief | Spearman (all pairs) | planar fit R² | fitted ρ |
|---|---|---|---|---|---|---|---|
| 500 m | **1** | 1.036 | 43.9 | +0.9969 | **+1.000** | 0.9957 | **1.258** |
| 750 m | **1** | 1.036 | 33.9 | +0.9948 | +0.967–1.000 | 0.9921 | **1.250** |
| 1000 m | **1** | 1.001 | 87.8 | +0.9990 | **+1.000** | 0.9978 | **1.277** |

The fitted ρ landing inside `[1, √2]` is an independent check on the derivation: a one-parameter fit
to real terrain recovers the direction factor the algebra predicts, and it recovers it at every
support. The cross-body pool (the six lunar references added as peer units) is rank 1 as well.

At the pixel level inside the windows, Pearson(slope, relief) is **+0.9835 … +0.9853** and the
measured ρ has median **1.27–1.285** with **61–64 %** of pixels inside the provable band. The
remainder is curvature inside the 3×3 window, which is exactly what the derivation says should break
it: on a paraboloid the relation degrades monotonically as the curvature coefficient rises.

### And the recommendation does not depend on any of them

Dropping any single axis leaves the non-dominated set **unchanged at every site and every support**
(`leave_one_axis_out`, both in the v2 panel artifact and re-derived here). A one-dimensional ordering
is invariant to which of its redundant names you keep.

### What this means, stated plainly

"Non-dominated on three axes at every support" is, on this panel, a **one-dimensional** statement:
the candidates are ordered along a single roughness/relief gradient and the survivor is the least
rough of the seven relative to each lunar reference. Three correlated roughness measures must not be
read as three independent dimensions of geological evidence. The panel's robustness is *explained* by
this, and explaining it makes the result **smaller, not wrong** — a one-dimensional ordering is far
more stable than a genuine three-dimensional Pareto front would be, which is consistent with the
6/6 ensemble and the 18/18 panel agreement rather than in tension with it.

**The honest consequence for a future panel:** it needs an axis that is not a roughness restatement
before it can claim multi-dimensional evidence. Directional fabric or anisotropy is the obvious
candidate, and it must arrive with its own hypothesis, unit and synthetic validation — not as a
fourth name for the same gradient.

**Boundary.** An absolute adequacy statement is still not available. The 50 % worst-axis distance
remains a descriptive label, not a validated threshold, and `LUNAR-DEMONSTRATION.md` says so.
