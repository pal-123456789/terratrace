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

## Terrain-type classification

For a one-word summary of a tile's map-scale form, `terrain_classify.py` assigns a single
descriptive terrain *type* — `flat_plain`, `rolling`, `dissected_upland`, or `rough_rugged`,
ordered from least to most relief and dissection. The classifier is deliberately transparent: it
is a set of explicit, documented threshold rules over the robust descriptors already in the
descriptor bank (median slope and its spread, median local relief, detrended ruggedness, the
Terrain Ruggedness Index, the Vector Ruggedness Measure, the Hurst roughness-scaling exponent, and
the ridge/valley landform fractions). There is no machine learning, no training, no fitted model,
and no randomness anywhere — each type owns a short list of boolean criteria, its score is simply
the fraction of those criteria the tile satisfies, and the chosen type is the argmax with a fixed
tie-break by the type order. The result carries the label, the evidence values the rules read, the
per-type scores, and a confidence equal to the margin between the top and runner-up scores.

The type is a **descriptive** map-scale morphology label and nothing more. It inherits the feature
layer's claim firewall unchanged: `flat_plain` does not assert the ground is safe to drive on and
`rough_rugged` does not assert bedrock or boulders. Summarising morphology into a word adds no
geological, genetic, lithological, age, hazard, mission, or rover-traversability claim that the
underlying descriptors do not already carry.

## Line-of-sight terrain structure: topographic openness & geomorphons

Two further descriptors read the surface not through local derivatives but along lines of
sight, which captures how exposed or enclosed a location is at the map scale. Both are
pure-NumPy, evaluated with whole-array shifts rather than per-cell loops, and sit in the same
non-destructive analysis layer as the geomorphometric descriptors above: computing them does
not change the default study package or its provenance hash.

**Topographic openness** (Yokoyama, Shirasawa & Pike, 2002) casts a ray from each cell along
eight azimuths and, over a fixed radius, records the steepest sight-line angle in each
direction. Positive openness is the mean of the eight *zenith* angles and negative openness
the mean of the eight *nadir* angles. Positive openness is high on convex, exposed features —
peaks, ridges, spur crests — and can exceed 90° at a summit where every sight line descends;
negative openness is its mirror, high inside pits, valleys, and channels. On a perfectly flat
surface both are exactly 90°, and on a uniform planar tilt both remain ~90° because the eight
directions cancel. It is a morphology and visualisation descriptor, not a measure of anything
mechanical.

**Geomorphon landform classification** (Jasiewicz & Stepinski, 2013) reduces the same
eight-direction line-of-sight scan to a *ternary* signature: each direction is compared
against a small flatness threshold and labelled lower (+), higher (−), or flat, giving a
per-cell count pair `(n_plus, n_minus)`. Because it depends only on elevation *differences*
and on direction *counts*, the signature is invariant to a uniform vertical shift and to
whole-grid rotation. The ternary signature is computed exactly as the published method
prescribes. The subsequent reduction to the ten common named landforms (flat, peak, ridge,
shoulder, spur, slope, hollow, footslope, valley, pit) uses an explicit, antisymmetric rule —
swapping `n_plus` and `n_minus` swaps peak↔pit, ridge↔valley, shoulder↔footslope, spur↔hollow
and fixes flat and slope — that is validated against canonical synthetic landforms; it is
**not** a verbatim copy of any particular GIS lookup table, and the documentation says so
rather than implying bit-for-bit equivalence with a specific implementation. The module also
exposes a *geomorphon spectrum*: a normalised 9×9 histogram over the `(n_plus, n_minus)`
counts, a compact distribution of a tile's local forms.

These feed an opt-in, fourth decision lens, `decision_metrics="landform"`, which keeps the
four core morphology axes and adds two candidate-to-reference distances: half the L1 total
variation between the two geomorphon spectra (bounded in [0, 1]) and a topographic-openness
distance. Like the `extended` and `geomorphic` lenses it is computed only when requested, so
the default `core` study package and its gated provenance hash are unchanged. The same opt-in
layer surfaces elsewhere: `descriptors.descriptor_bank` appends openness and geomorphon
sub-dictionaries, the terrain `fingerprint` gains an optional geomorphon-spectrum term, and a
study run with `landform=True, previews=True` carries a per-unit landform-composition table,
positive/negative openness medians, and two inline previews — a categorical landform map and a
grayscale openness field — that the HTML report and the offline viewer render when present and
omit otherwise. Eight canonical oracles in the validation suite pin the behaviour (openness is
90° on a plane and rises past 90° on a cone apex / in a bowl; a cone classifies as `peak`, a
bowl as `pit`, a tilt as `slope`, a plane as `flat`; and the classification is invariant to a
vertical lift).

The whole layer inherits the engine's claim firewall unchanged: it describes map-scale surface
*form* only and asserts nothing about traversability, hazard, geologic-unit identity, or
mission readiness. References: Yokoyama, R., Shirasawa, M., & Pike, R. J. (2002), *Visualizing
topography by openness: a new application of image processing to digital elevation models*,
Photogrammetric Engineering & Remote Sensing 68(3), 257–265; and Jasiewicz, J., & Stepinski,
T. F. (2013), *Geomorphons — a pattern recognition approach to classification and mapping of
landforms*, Geomorphology 182, 147–156, doi:10.1016/j.geomorph.2012.11.005.

## Scale & fabric: spectral roughness and directional anisotropy

Two further pure-NumPy descriptors summarise *how rough the surface is at each spatial scale*
and *whether that roughness has a preferred direction*. Both read the same projected metric grid
and sit in the same non-destructive analysis layer as the descriptors above: computing them
leaves the default study package and its provenance hash unchanged.

**Radially-averaged power spectral density** (`spectral.py`, after Perron, Kirchner & Dietrich
2008) fills nodata cells with the finite mean, removes a least-squares best-fit plane so DC and
tilt do not dominate, applies a separable 2-D Hann window to curb spectral leakage, takes the
2-D FFT, and radially averages the windowed periodogram over wavenumber `kr = sqrt(kx^2 + ky^2)`
(the k=0 bin excluded). The periodogram is normalised by the window energy so it integrates back
to the detrended variance. From that spectrum it reports the log-log **spectral slope** — how
power is partitioned between long and short wavelengths, fit over a mid-band that drops the
lowest-k bin and the near-Nyquist tail — the **band roughness** (the RMS amplitude in long-,
mid-, and short-wavelength thirds of log-k), the **peak wavelength** that carries the most power,
and a **total power** that recovers the detrended variance by Parseval's theorem. A single
sinusoid returns its own wavelength as the peak; spatially uncorrelated noise returns a flat
(~zero) slope.

**Directional structure function** (`anisotropy.py`, after Shepard et al. 2001) measures the RMS
elevation difference between points separated by a fixed lag along a fan of azimuths binned over
`[0, 180)`, so a surface whose roughness is the same in every direction looks isotropic while one
grooved by parallel ridges, dunes, or lineations is rougher across the grain than along it. It
reports an anisotropy **strength** `(Rmax - Rmin) / (Rmax + Rmin)` in `[0, 1]` (0 = isotropic,
approaching 1 as the surface becomes strongly lineated), the fabric **orientation** — the azimuth
of *minimum* roughness, i.e. the strike along which the ridges or dunes run — and an **isotropy**
ratio `Rmin / Rmax`. Because it is a difference statistic it is NaN-safe and exactly invariant to
a vertical datum offset.

Both are opt-in and gated. `study.compare_units(..., terrain_spectra=True)` (and
`run_real_study(terrain_spectra=True)`) attach a per-unit `spectral` and `anisotropy` block to
the study package for each compared, eligible unit; the HTML report and the offline viewer render
a **"Scale & fabric"** section when those blocks are present and omit it otherwise; and
`descriptors.descriptor_bank` and the terrain `fingerprint` gain opt-in spectral/anisotropy terms.
Everything is off by default, so the synthetic study package and its gated provenance hash are
byte-unchanged. Five scientific-correctness oracles pin the behaviour: a sinusoid's peak
wavelength, a white-noise surface's flat spectral slope, and Parseval total-power recovery for the
spectrum; a ridged surface's recovered orientation and high strength, and an isotropic-noise
surface's low strength for the fabric.

The claim firewall is unchanged: these summarise the sampled DEM's roughness spectrum and
directional structure *only*. They are not a traversability, hazard, geologic, or
mission-readiness claim, and they say nothing about rock-scale obstacles below the pixel.
References: Perron, J. T., Kirchner, J. W., & Dietrich, W. E. (2008), *Spectral signatures of
characteristic spatial scales and nonfractal structure in landscapes*, Journal of Geophysical
Research: Earth Surface 113, F04003; and Shepard, M. K., Campbell, B. A., Bulmer, M. H., Farr,
T. G., Gaddis, L. R., & Plaut, J. J. (2001), *The roughness of natural terrain: A planetary and
remote sensing perspective*, Journal of Geophysical Research: Planets 106(E12), 32777–32795.

## Distances and decision

Per-feature distribution distance uses Wasserstein-1 normalized by a declared scale
(pooled IQR, with std/range fallback). Candidates are compared by **Pareto dominance**
over the active metric vector; a recommendation is emitted only when one eligible unit
is non-dominated and stable across sensitivity scenarios (pairwise rank-flip <= 0.1).
Otherwise the result is `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, or `BLOCKED`.

The decision never collapses the vector into a single "Mars-likeness" number. Six independent axis
sets are offered as robustness lenses, five of which are on by default in the atlas and ablation
tools:

- `core` — the four bulk morphology metrics (slope, relief, ruggedness, connectivity); the default
  and the one gated into the synthetic study package;
- `extended` — adds aspect dispersion and the hypsometric integral;
- `geomorphic` — adds Zevenbergen–Thorne mean curvature and the Vector Ruggedness Measure, shape
  descriptors decoupled from mean slope;
- `landform` — keeps the four core axes and adds the two line-of-sight structure distances described
  under *Line-of-sight terrain structure* above (a geomorphon-spectrum total-variation distance and a
  topographic-openness distance);
- `texture` — adds the scale & fabric axes described under *Scale & fabric* above (spectral slope /
  band roughness and directional-fabric anisotropy);
- `hydro` — **opt-in only** via `decision_metrics`, adds the flow-geometric axes (Topographic Wetness
  Index, convergence index, and the flow-dissection distance).

A recommendation that survives several independent axis sets is far more defensible than one that
holds under a single set. Every non-default lens is computed only when requested, and choosing one
does not alter the `core` study package or its provenance hash.

## Sensitivity / ablation

A recommendation is only trustworthy if it survives the analyst's own choices, so `sensitivity.py`
re-runs the finished screen under those choices and reports whether the answer holds.
`lens_ablation` re-runs `compare_units` under each of the decision lenses — `core`, `extended`,
`geomorphic`, `landform`, and `texture` (and `hydro` when it is requested) — and `support_ablation`
re-runs it across a set of common-support scales under one lens; each reports the set of units
recommended and whether that set collapses to a single unit (every recommending run names the same
one, or none recommends). `ablation_report` combines the two into an `overall_stable` verdict that is
true only when the recommendation is stable across lenses *and* across supports (or no support sweep
was requested).

This is a robustness *diagnostic* over the existing morphology screen, not a new scientific claim:
it adds nothing to what the screen already decided and only reports how fragile or stable that
decision is. A recommendation that is identical under all the independent axis sets and across a
range of supports is far more defensible than one that depends on a single setting; where the
ablation disagrees with itself it says so rather than hiding the fragility. The same map-scale
morphology firewall applies throughout.

## Uncertainty

A single distance is a point estimate that hides sampling error, so TerraTrace resamples
the terrain-feature distributions with replacement to put a confidence interval on each
distance and to convert the Pareto decision into a *frequency*: how often each candidate is
non-dominated, and how often one unit is the clear winner. "B beats A" becomes "B is
non-dominated in 78% of resamples", which is the honest, scientist-grade statement.
Bootstrapping runs whenever `n_boot > 0`.

Two resampling methods are available. The default, `independent`, draws pixels
independently. It is simple and fast, but DEM pixels are spatially autocorrelated —
neighbouring cells are not independent samples — so treating every pixel as its own draw
overstates the effective sample size and the resulting confidence intervals come out
**optimistically narrow**. They should be read as a lower bound on the true uncertainty,
not a calibrated one.

The `block` method is a two-dimensional **moving-block bootstrap**. Rather than shuffling
individual pixels, it tiles each resampled feature map with `block_size × block_size`
patches drawn with replacement from random positions in the source map (edge blocks clipped
to fit, NaNs carried along with their block), so the autocorrelation *within* a block is
preserved instead of destroyed. Because neighbouring cells now travel together, the
effective sample size is no longer inflated and the confidence intervals are more honest —
typically **wider** than the independent-pixel intervals. On a measured autocorrelated field
the block method's total distance-CI width came out several times the independent width,
confirming that the independent bootstrap really was over-confident there. A `block_size` of
1 degenerates to the independent resample; the guidance is to set `block_size` at or above
the terrain's spatial correlation length so each resampled patch holds a full correlation
cell.

Both methods are selectable end-to-end: `compare_units` and `run_real_study` accept
`bootstrap_method` (`independent` | `block`) and `block_size` (in aggregated pixels, default
4), honoured only when `n_boot > 0`. The block bootstrap is opt-in and the default stays
`independent`, so the synthetic study package and its provenance hash are unchanged. Either
way the quantity is still map-scale morphology: a wider interval reports honest uncertainty
about the *morphology distance*, and makes no claim about traversability, geologic
equivalence, or mission readiness.

## Autocorrelation-driven block size

The block bootstrap only gives honest intervals when its block is at least as large as the
terrain's spatial correlation length, and choosing that block by eye is unprincipled.
`autocorr.py` measures it from the data: it computes the field's autocorrelation as a
function of lag — the Pearson correlation between the map and copies of itself shifted by
one, two, three, and more pixels, pooling the horizontal and vertical shifts over finite
pairs — and reads the correlation length as the first lag at which that curve falls to 1/e.
Clamped to a sensible range, that length in pixels becomes the suggested block size fed to
the moving-block bootstrap, so each resampled block spans a full correlation cell by
construction rather than by guess. The curve and the length are map-scale descriptive
statistics of the elevation grid only; they say how smoothly the sampled surface varies and
make no traversability or mechanical-roughness claim.

## Statistical significance

A single distance, or even a bootstrap interval, still leaves one question open when two
candidates are close: is A *meaningfully* nearer the reference than B, or is the gap noise?
`significance.py` answers it with a one-sided permutation test. It pools the finite
elevation-feature samples of the two candidates, repartitions the pool at random into two
groups of the original sizes many times over, and each time recomputes the difference of
normalized distances to the reference; the p-value is the fraction of those random
relabellings whose gap is at least as extreme as the observed one. A standardized effect
size in [-1, 1] reports how large the closeness gap is independent of its significance, and
a bootstrap confidence interval brackets each distance. The test speaks only about the shape
of elevation-sample distributions — it asks whether a closeness gap could arise by chance
and makes no physical, geologic, or mission claim about either terrain.

## Statistical confidence for the decision

The significance test above compares any two candidates; wiring it into the finished screen
answers the sharper question an analyst actually asks — *is the recommended unit meaningfully
closer to the reference than the next-best one?* With `significance=True`, `study.compare_units`
(and `run_study` / `run_real_study`, which forward it) attaches an opt-in `significance` block: a
one-sided permutation test (`significance.permutation_closer_test`) of the recommended unit
against the **runner-up** — the second-closest eligible candidate — run per sample-based
morphology metric (slope, relief, ruggedness) with the decision's own per-feature scales, each
reporting one- and two-sided p-values and a standardized effect size. Connectivity is a single
scalar, so it carries a signed closeness difference rather than a permutation p-value. The block
also sets `recommendation_significant`, true when at least one metric shows the recommended unit
both closer and significant at the one-sided 5% level. The test is **off by default**, so when it
is not requested the frozen `run_study()` package and its provenance hash are byte-for-byte
unchanged.

`confidence.decision_confidence(package, sensitivity_report=None)` turns that evidence into an
honest, **non-composite** verdict — it never forms a weighted score. Instead it restates the
robustness evidence a study already contains as three independent signals, each reported
separately with its own value and plain-language detail:

- **bootstrap non-domination** — how often the recommended unit stays Pareto non-dominated across
  the bootstrap resamples (from the `bootstrap` block, present when a study was run with
  `n_boot > 0`);
- **significance vs the runner-up** — the permutation `recommendation_significant` flag above;
- **lens / support stability** — whether the recommendation survives changing the decision lens
  and common support (from a `sensitivity.ablation_report`).

From the signals that were actually evaluated it returns a single categorical `verdict` —
`robust`, `qualified`, `fragile`, `tie`, `indeterminate`, `blocked`, `not_comparable`, or
`unverified` — with a plain-language `rationale` and an explicit `caveats` list naming every
signal that was **not** evaluated. A recommendation is `robust` only when at least two signals
were evaluated and all are positive, `fragile` as soon as any evaluated signal is negative, and
`qualified` when the support is only partial; when the screen did not reach a single-unit
recommendation the verdict simply mirrors that state. A missing signal degrades to
"not evaluated" rather than being invented, so the verdict always states exactly how much
evidence stands behind it.

Both are surfaced end to end: the CLI gains `study --significance --n-perm` and a `confidence`
subcommand, and the stdlib HTTP API gains `POST /confidence` (plus a `significance` option on the
study-runner route); the HTML report and the offline viewer render a "Decision confidence" section
(the verdict, the three signals, the rationale, and the caveats) and a "Significance vs runner-up"
table, shown only when a robustness signal was actually computed — so the default report is
unchanged.

The firewall is unchanged: these are distribution-shape resampling statistics and morphology
screening only. "Decision confidence" means the robustness of the morphology screen's
recommendation to resampling, to a permutation test against the runner-up, and to changing the
decision lens or support — and nothing more. It is never a traversability, hazard,
geologic-equivalence, or mission-readiness claim. The resampling methods follow Efron & Tibshirani
(1993, *An Introduction to the Bootstrap*, Chapman & Hall) for the bootstrap and Good (2005,
*Permutation, Parametric, and Bootstrap Tests of Hypotheses*, 3rd ed., Springer) for the
permutation test.

## Elevation-error propagation

A morphology distance inherits uncertainty not only from sampling but from the DEM's own
vertical accuracy, so each catalog source now declares an approximate 1-sigma vertical
accuracy (`vertical_accuracy_m`, an order-of-magnitude RMSE from the product/mission docs)
and `errorprop.py` propagates it analytically into feature uncertainty. With a
central-difference gradient and independent per-pixel vertical error of standard deviation
`sigma_z`, the gradient-magnitude error is `sigma_G = sigma_z / (dx * sqrt(2))`; propagating
through `theta = atan(G)` (`dtheta/dG = 1 / (1 + G^2)`) gives a slope-angle uncertainty
`sigma_theta = sigma_G / (1 + tan(slope)^2)`, largest on flat ground and shrinking as the
terrain steepens and as the pixel grows. Local relief, a difference of two pixels, propagates
exactly as `sqrt(2) * sigma_z`, and detrended ruggedness carries a rough bound of order
`sigma_z`.

The caveat is exactly parallel to the independent-pixel bootstrap: assuming **independent**
per-pixel errors makes every number here an **optimistic lower bound** on the true
uncertainty. Real DEM errors are spatially correlated — striping, swath and tile seams,
co-registration residuals, terrain-dependent bias — which inflates feature uncertainty above
these estimates, and the relief and ruggedness bounds are additionally rough because window
residuals partially cancel the per-pixel noise. These are map-scale morphology uncertainties
only and make no mechanical, trafficability, or mission claim.

## Measurement-uncertainty propagation in the report

The elevation-error propagation above becomes visible in the deliverables when it is asked for.
`compare_units` and `run_real_study` take an opt-in `vertical_accuracy` argument — a single
`sigma_z` or a per-unit map — and, when it is supplied, attach a `feature_uncertainty` block to the
study package: the propagated 1-sigma slope, relief, and ruggedness bands for each unit, computed
by `errorprop.py` at that unit's common support and median slope. A real study resolves `sigma_z`
automatically from each source's catalog vertical accuracy (or a per-unit `vertical_accuracy_m`
override), so the bands reflect the actual DEM products compared. Passing `previews=True`
additionally attaches a `previews` block: one self-contained hillshade PNG data-URI per unit,
rendered by `hillshade.py` with the standard library alone. The HTML report (`report_html.py`) and
the offline viewer (`build_viewer.py`) both detect these blocks and, when present, render a
**"Measurement uncertainty"** table and an inline terrain-preview strip; when absent, that part of
the document simply does not appear.

Both features are **off by default**. When neither argument is given the study package is
byte-for-byte what it was before — the synthetic study and its gated provenance `package_hash` are
unchanged — so the uncertainty bands and previews are a strictly additive, opt-in layer. The bands
carry the same caveat as the propagation that produced them: they assume independent per-pixel
error and are therefore an optimistic lower bound, and they visualise map-scale morphology
uncertainty only, with no mechanical, trafficability, or mission claim. The hillshade is an
illustrative shaded-relief aid that encodes surface orientation and makes no quantitative claim.

## Batch studies

A single study compares one Mars reference against a slate of Earth candidates under
one decision lens, and that study already exists end-to-end. Analog screening is more
defensible when a candidate is tested against several Mars reference regions and under
several independent decision-axis sets at once, so `batch.py` generalises the single
study across both. It runs a grid: every (Mars reference × decision mode) cell is a
complete `compare_units` pipeline, the default modes being the same five lenses used
elsewhere — `core`, `extended`, `geomorphic`, `landform`, and `texture`.

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
comparable across bodies. Mars uses a sphere of radius 3,396,190 m, the Moon a sphere of
radius 1,737,400 m, Mercury a sphere of radius 2,439,400 m, Ceres a sphere of radius
469,730 m, and Earth the WGS84 ellipsoid.

## Multi-body support

The comparison core is body-agnostic, so TerraTrace screens Earth candidates against a
Mars, Moon, Mercury, *or* Ceres reference — five reference bodies in all (Earth, Mars,
Moon, Mercury, Ceres). Each AOI is warped on its own figure before any statistic is
computed — the Mars sphere (R = 3,396,190 m), the Moon sphere (R = 1,737,400 m, the
LRO/LOLA mean radius), the Mercury sphere (R = 2,439,400 m, the MESSENGER mean radius),
the Ceres sphere (R = 469,730 m, the Dawn mean radius), or the Earth WGS84 ellipsoid — so a
degree of longitude becomes the right number of metres on whichever body an AOI belongs to
and slope and relief are true metres everywhere. The source catalog carries keyless
planetary products for the non-Earth bodies — the Mars MOLA DEM, the LRO LOLA LDEM global
topography (~118 m), the MESSENGER global DEM of Mercury (~665 m), and the Dawn HAMO DTM of
Ceres (~137 m), all from USGS Astrogeology — beside the Earth products, and the preflight
accepts each body with its own longitude convention. Strongly irregular bodies such as the
asteroid Vesta are deliberately **not** offered: a single sphere would misrepresent a shape
that departs far from spherical, so forcing one would corrupt the metric grid rather than
describe it. Adding a body does not change the comparison logic: every existing Mars, Earth,
and Moon result and the gated synthetic study hash are unchanged, and the same claim
firewall applies — map-scale morphology only, on every body.

## DEM co-registration

Before two elevation grids can be differenced or compared pixel-by-pixel they must sit on
the same frame. `coregister.py` performs a translation-only, map-scale alignment and nothing
more: it recovers the horizontal pixel shift that best registers a *moving* grid onto a
*reference* grid, then estimates a single vertical-datum (bias) offset so the two share a
common zero. The horizontal shift is found by scoring every integer (dy, dx) within a search
radius by the root-mean-square elevation difference over the cells the two grids share — each
candidate's own median offset removed first, so a pure datum bias cannot pull the horizontal
search — and the best integer shift is then refined to sub-pixel precision by fitting a
parabola to the RMSE of its immediate neighbours and taking the vertex. The vertical offset
is the median difference over co-located finite cells, robust to outliers and to partial
overlap. Every routine is pure NumPy and NaN-aware: cells that are nodata in either grid are
ignored, and edges exposed by a shift are filled with NaN rather than wrapped. The alignment
is deliberately rigid — translation plus a datum offset only, with **no** rotation, scaling,
or non-rigid warp — and it is a numerical registration of two grids so their overlap can be
studied, carried out before comparison; it is not a claim about how either DEM was acquired
or any mechanical or mission property.

## Terrain fingerprint and similarity

A *fingerprint* is a compact, fixed-length signature of a terrain's map-scale morphology,
distilled from the geomorphometric descriptor bank. `fingerprint.py` pulls a stable,
documented subset of eleven descriptors — slope at the 50th and 90th percentiles, median
local relief, detrended and vector ruggedness, surface-area ratio (rugosity), the spread of
mean curvature, aspect isotropy, the hypsometric integral, the dispersion of the Topographic
Position Index, and the Hurst roughness-scaling exponent — chosen to span complementary and
largely independent axes of surface form. Two fingerprints are compared by a
per-dimension-normalised root-mean-square distance taken over the dimensions both signatures
define, mapped to a bounded similarity `sim = 1 / (1 + d)` in (0, 1]; identical signatures
give exactly 1.0 and the score decays monotonically as the signatures diverge.
`rank_library()` scores a query terrain against a library of references and returns them
ordered by similarity, best match first, so the engine can answer "which reference terrain
does this most resemble, morphologically?". Optional per-dimension scales (for example the
library's own spread) put every axis on a comparable footing so no single large-magnitude
descriptor dominates the distance. This is a morphology signature and a ranking only — a
statement about nearness in a morphology-signature space — and explicitly **not** a
classification, an identity match, a geological-equivalence claim, or any traversability,
mechanical, or mission claim.

## Fingerprint similarity search and dossiers

The single-terrain fingerprint above becomes a *search* once there are several references to
compare against. `fingerprint_library.py` turns a collection of named reference terrains into
a fingerprint library and ranks any query terrain against it, best morphological match first;
`cross_body_table` generalises that to the cross-**body** case, ranking a slate of Earth
candidates against a set of planetary references (Mars-like, Moon-like) and reporting, per
candidate, the full candidate × reference similarity matrix and the single reference it most
resembles. `scripts/fingerprint_search.py` is an offline, network-free demo over synthetic
terrains; a real-data run fingerprints DEM tiles loaded through `ingest` with the identical
API. All feature math lives in the fingerprint and descriptor layers, so the ranking inherits
their firewall unchanged: "most similar" means nearest in the fixed morphology-signature space
and is **not** a classification, identity, or geological-equivalence claim.

Where the study package summarises every unit at once, `dossier.py` produces the
per-**candidate** analogue: a focused decision brief for one unit that gathers, in one place,
its per-metric morphology distances to the reference, its Pareto-frontier layer, its
eligibility verdict, its bootstrap non-domination / clear-winner frequencies and distance CIs
(when a bootstrap was run), whether it is the recommendation, and the transfer-gap ledger and
prohibited-claims list that bind it — as a structured dict and as Markdown. An ineligible or
missing unit yields a blocked verdict with its reason and no distances rather than an error.
Nothing in a dossier widens, softens, or re-weights a claim; it only re-presents, per
candidate, what the engine already decided, under the same map-scale morphology firewall.

For visual context, `hillshade.py` can render an AOI as a Horn shaded-relief image encoded as
a base64 PNG data URI using only the Python standard library, so a terrain preview embeds
inline in the self-contained HTML report with no external assets. It is a visualisation aid
that encodes illuminated surface orientation only and makes no quantitative claim.

## Provenance

Every displayed value resolves through the evidence graph to a source, a transformation,
and a limitation. `sources.lock.yml` records each input's SHA-256, size, CRS, bounds, and
required citation; the study package carries a canonical `package_hash`.
