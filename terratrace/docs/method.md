# Method

## Pipeline

```
source DEM (Mars MOLA / Earth Copernicus)
  -> window to AOI (lon/lat bbox transformed into source CRS)
  -> mask sentinels (ocean 0 m, nodata) to NaN
  -> reproject to local azimuthal-equidistant metric grid at target support
  -> common-support aggregation (valid-fraction tracked)
  -> features (slope, relief, ruggedness, connectivity, aspect dispersion, hypsometric)
  -> normalized distribution distances to the reference
  -> eligibility filters -> Pareto / tie / sensitivity
  -> transfer-gap ledger -> draft study protocol -> evidence graph -> study package
```

## Features

- **Slope** (degrees): `arctan(sqrt((dz/dx)^2 + (dz/dy)^2))` on a projected grid.
- **Local relief**: upper minus lower quantile within a declared physical window
  (`alpha=0` gives max-min; `alpha=0.05` a robust P5-P95).
- **Detrended ruggedness**: RMS of residuals after removing a local best-fit plane; a
  perfect plane returns ~0.
- **Low-slope connectivity**: fraction of valid cells in the largest 4-connected
  component below a slope threshold - a map-scale corridor statistic, not a route.
- **Aspect dispersion**: circular variance of slope direction in [0,1]; 0 = one dominant
  downslope direction, ~1 = isotropic.
- **Hypsometric integral**: `(mean - min) / (max - min)` of elevation; 0.5 = symmetric.

## Geomorphometric descriptors

Alongside the bulk-roughness features above, TerraTrace exposes a deeper geomorphometric
descriptor set that characterises *how* a surface curves and *how* its roughness changes
with scale. These form a non-destructive analysis layer: they read the same projected
metric grids but are not part of the default `core` or `extended` decision vector, so
computing them leaves the study package and its provenance hash unchanged. Each is defined
with an explicit window and known invariances, consistent with the map-scale claim
firewall — they describe surface *form*, not traversability or any mechanical property.

Profile, plan, and mean curvature are computed by the Zevenbergen & Thorne (1987) method,
which fits a local quadratic surface to each 3x3 node neighbourhood and reads curvature
from its coefficients. Profile curvature is taken in the slope (steepest-descent)
direction and expresses whether a slope is accelerating or decelerating downslope flow;
plan curvature is taken across the slope, along the contour, and expresses whether flow
converges or diverges; mean curvature combines the two into a general, direction-free
convexity. All three are exactly 0 on a plane of any tilt, and on the test paraboloid
`z = a(x^2 + y^2)` they take precisely profile = -2a, plan = +2a, and mean = -4a, following
the Zevenbergen & Thorne sign convention. Profile and plan curvature are undefined where
the surface is locally flat, because the slope direction is indeterminate when the gradient
is near 0; the engine returns 0 at those cells. Mean curvature is formed directly as
-2(D + E) from the second-derivative coefficients, so it needs no division by slope and
stays defined even on flat ground. Curvature therefore isolates local form — bumps,
hollows, ridges, and channels — independently of overall steepness.

The Vector Ruggedness Measure follows Sappington, Longshore & Thompson (2007). Within a
window, each cell's unit surface-normal vector is summed, and the measure is one minus the
length of the resultant divided by the number of cells. When every normal points the same
way the resultant is full length and the measure is 0; as the normals scatter the
resultant shortens and the measure climbs toward 1. Its defining property is that it is 0
on any plane, however steep, because a plane's surface normals are all parallel. Unlike the
spread of slope values, it is therefore decoupled from the mean slope and reports only the
dispersion of surface orientation. The result is bounded in [0, 1] and increases
monotonically as the surface is made rougher, which is the behaviour the validation suite
asserts.

To describe how roughness depends on scale, TerraTrace computes an isotropic structure
function: the root-mean-square elevation difference between points separated by each of a
set of lags, pooling horizontal and vertical offsets. For a self-affine
(fractional-Brownian) surface this RMS difference grows with lag as a power law, `lag^H`,
so the slope of the structure function plotted on log-log axes estimates the Hurst
exponent H, which the engine clamps to [0, 1]. A value near 1 marks a smooth,
long-range-correlated surface whose roughness keeps growing with distance; a value near 0
marks white-noise-like roughness already saturated at the smallest lag. The limits are
fixed analytically: a linear ramp, whose elevation difference is exactly proportional to
lag, yields H = 1, while spatially uncorrelated noise yields H near 0. This provides a
single, scale-aware roughness summary that complements the fixed-window ruggedness and
relief statistics.

These descriptors rest on standard references: Zevenbergen & Thorne (1987, *Earth Surface
Processes and Landforms* 12, 47-56) for the local-quadratic curvature method; Sappington,
Longshore & Thompson (2007, *Journal of Wildlife Management* 71, 1419-1426) for the Vector
Ruggedness Measure; and the self-affine surface / fractional-Brownian-motion framework
underlying structure-function and Hurst roughness scaling (Mandelbrot & Van Ness, 1968,
*SIAM Review* 10, 422-437; applied to topography by Turcotte, 1997, *Fractals and Chaos in
Geology and Geophysics*, Cambridge University Press).

## Distances and decision

Per-feature distribution distance uses Wasserstein-1 normalized by a declared scale
(pooled IQR, with std/range fallback). Candidates are compared by **Pareto dominance**
over the active metric vector; a recommendation is emitted only when one eligible unit
is non-dominated and stable across sensitivity scenarios (pairwise rank-flip <= 0.1).
Otherwise the result is `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, or `BLOCKED`.

The decision never collapses the vector into a single "Mars-likeness" number. Three decision
axis sets are offered as mutually-exclusive robustness lenses: `core` (the four morphology
metrics, default and gated), `extended` (adds aspect dispersion and hypsometric integral),
and `geomorphic` (adds Zevenbergen-Thorne mean curvature and the Vector Ruggedness Measure —
shape descriptors decoupled from mean slope). The `extended` and `geomorphic` modes are
opt-in: a recommendation that survives all three independent axis sets is far more defensible
than one that holds under a single set. Choosing a non-default mode does not alter the `core`
study package or its provenance hash; the extra descriptors are computed only when requested.

## Batch studies

A single study compares one Mars reference against a slate of Earth candidates under
one decision lens, and that study already exists end-to-end. Analog screening is more
defensible when a candidate is tested against several Mars reference regions and under
several independent decision-axis sets at once, so `batch.py` generalises the single
study across both. It runs a grid: every (Mars reference × decision mode) cell is a
complete `compare_units` pipeline, the default modes being the same three lenses used
elsewhere — `core`, `extended`, and `geomorphic`.

The grid is synthesised rather than scored. For each candidate the batch reports how
often it is Pareto non-dominated (frontier layer 1) across all cells, how often it is
the sole recommendation, and its mean Pareto layer. The headline result is a consensus
shortlist: the candidates that are non-dominated in *every* cell and are therefore
robust to both the choice of Mars reference and the choice of morphology lens. A robust
ordering then ranks candidates by how consistently they stay non-dominated.

This is a transparent robustness synthesis, never a composite "Mars-likeness" number,
and it inherits the engine's claim firewall: map-scale morphology only. A candidate can
be non-dominated under some lenses yet still miss the consensus shortlist, and under
some lenses the honest verdict is a tie with no sole winner even while one candidate is
always non-dominated — the batch surfaces that disagreement rather than forcing an
answer. The array-level `run_batch` needs no network or rasterio and is fully testable;
`run_real_batch` loads real DEMs through the same shared loader as the single real study.

## Reprojection

Each AOI is warped to a local azimuthal-equidistant CRS centered on its centroid, with the
correct body ellipsoid/sphere, so slope and relief are computed on true metres and are
comparable across Mars and Earth. Mars uses a sphere of radius 3,396,190 m; Earth uses
WGS84.

## Provenance

Every displayed value resolves through the evidence graph to a source, a transformation,
and a limitation. `sources.lock.yml` records each input's SHA-256, size, CRS, bounds, and
required citation; the study package carries a canonical `package_hash`.
