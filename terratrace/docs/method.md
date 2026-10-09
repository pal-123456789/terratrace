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

## Distances and decision

Per-feature distribution distance uses Wasserstein-1 normalized by a declared scale
(pooled IQR, with std/range fallback). Candidates are compared by **Pareto dominance**
over the active metric vector; a recommendation is emitted only when one eligible unit
is non-dominated and stable across sensitivity scenarios (pairwise rank-flip <= 0.1).
Otherwise the result is `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, or `BLOCKED`.

The decision never collapses the vector into a single "Mars-likeness" number. Two decision
axes are offered: `core` (four morphology metrics, default) and `extended` (adds aspect
dispersion and hypsometric integral) as a built-in robustness ablation.

## Reprojection

Each AOI is warped to a local azimuthal-equidistant CRS centered on its centroid, with the
correct body ellipsoid/sphere, so slope and relief are computed on true metres and are
comparable across Mars and Earth. Mars uses a sphere of radius 3,396,190 m; Earth uses
WGS84.

## Provenance

Every displayed value resolves through the evidence graph to a source, a transformation,
and a limitation. `sources.lock.yml` records each input's SHA-256, size, CRS, bounds, and
required citation; the study package carries a canonical `package_hash`.
