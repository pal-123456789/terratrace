# Validation and ablations

TerraTrace is validated at the level it claims: **map-scale terrain morphology
screening**. These checks establish software/metric correctness, data handling,
sensitivity, and provenance. They do **not** establish rover traversability,
autonomy, geologic equivalence, site access, or mission readiness.

## Test suite (983 fixtures, `tests/run_tests.py`)

| Area | What the fixtures prove |
|---|---|
| features | Slope equals the analytic value on a known plane; relief exact on a ramp; ruggedness ~0 on a plane and scale-linear; connectivity counts the true largest component; aspect dispersion ~0 on a plane and high on noise; hypsometric integral 0.5 on a ramp, NaN when flat |
| features (curvature / VRM / roughness) | Zevenbergen-Thorne profile, plan, and mean curvature are 0 on a tilted plane and bit-exact on a paraboloid (profile -2a, plan +2a, mean -4a); the Vector Ruggedness Measure is 0 on any plane and rises with added roughness, staying in [0,1]; the structure function increases with lag and the Hurst exponent is 1 on a linear ramp and near 0 on white noise; curvature degrades to NaN on a sub-3x3 AOI |
| support | Block aggregation on constants, a known 2x2 mean, nodata/valid-fraction tracking, common-factor guards |
| distances | Wasserstein-1 = 0 for identical, = c for a shift; KS 0/1 bounds; NaN ignored; degenerate scale stays finite; all-constant -> 0 |
| decision | Pareto dominance and non-dominated sets; rights allowlist fails closed; water (zero-fraction) block; stable-winner vs tie resolution |
| frontier | Peeled Pareto layers in order; dominance matrix; id-only within-layer order; identical-vector + determinism |
| uncertainty (block) | `block_resample_2d` tiles a 2-D field with block×block patches drawn with replacement, preserving within-block autocorrelation (block=1 degenerates to independent pixels; NaNs carried with their block); the block-bootstrap distance CIs come out **wider** than the independent-pixel bootstrap on an autocorrelated field, and the closer unit holds the higher non-domination frequency |
| masks | Sentinel/below/above masking to NaN; zero-fraction; input not mutated |
| reproject | Body-correct CRS strings across five bodies (Mars, Moon, Mercury, Ceres spheres + Earth WGS84), centroid, grid sizing, unknown-body guard; Mercury and Ceres are supported bodies and the Mars/Moon strings are unchanged |
| catalog | 15-source registry validates across five bodies (keyless Moon LOLA LDEM, Mercury MESSENGER, Ceres Dawn HAMO, and the keyless `earth_cop30_cog` beside the Mars + Earth products); coverage + body-mismatch; `recommend_source` preference/least-download/keyless; SRTM band excludes >60°N; nodata sentinels; every source carries a positive `vertical_accuracy_m` |
| preflight | bbox well-formedness + body bounds; area/pixel/download sizing; config-schema (dup ids/paths, demtype-vs-dataset); non-US routing |
| profile | valid/water/NaN fractions; robust relief; advisory vs blocking flags; water==masks.zero_fraction |
| fetchcache | sha256 matches sourcelock; needs_fetch skip/mismatch; manifest round-trip + update |
| ingest | TIFF magic-byte guard rejects error-JSON; `_stream` retry/backoff + Retry-After + fail-fast |
| sourcelock | SHA-256 matches hashlib; citations/terms per body; missing-file entry |
| study (e2e) | Contract keys present; ineligible unit excluded; close unit dominates far; deterministic package hash; all-blocked -> BLOCKED; evidence graph has eligibility+result+protocol nodes; extended mode adds two dimensions |
| batch | Cross-reference × multi-lens synthesis: the same-statistics twin is the sole consensus analog; a far-rougher candidate is never non-dominated; deterministic, JSON-serialisable report |
| validation | The engine passes every scientific-correctness check (see below) |
| benchmark | Pinned behavioural invariants + hash stability + a scaling profile |
| report | A study package and a batch report each render to Markdown containing the result, the per-axis metric table, and the provenance package hash; rendering is deterministic |
| report_html | A study package and a batch report each render to a single self-contained, offline HTML document; every dynamic value is HTML-escaped and the claim firewall is reproduced verbatim; rendering is deterministic (no timestamps) |
| significance | The permutation test flags a true closeness gap (not a tie) as significant, and the bootstrap distance interval comes out correctly ordered (lo <= median <= hi) |
| autocorr | White-noise terrain has a correlation length of ~1 px, far below a smooth hill's; the suggested block size lands within its clamp range |
| repro | A recomputed hash matches the stored package hash; a tampered field is detected; the synthetic study reproduces bit-for-bit across runs |
| coregister | A known horizontal pixel shift is recovered (overlap-RMSE search + sub-pixel parabola refinement) so the aligned overlap RMSE returns to ~0, and an injected vertical-datum offset is recovered as the median of co-located cells; edges NaN-filled, never wrapped |
| fingerprint | A terrain's similarity to itself is exactly 1.0; similarity discriminates a flat plane from a rough surface; `rank_library` puts the true match first; the 11-field signature is deterministic and JSON-serialisable |
| api | The new endpoints (`GET /bodies`, `POST /validate`, `POST /batch`, `POST /report`) each return 200 with well-formed JSON, and the existing security is preserved (loopback-only Host allowlist, 64 KiB body cap, `n_boot` clamped to 500) |
| errorprop | Zero vertical error gives zero slope/relief/ruggedness sigma; relief sigma is exactly `sqrt(2) * sigma_z`; the flat-ground slope sigma matches the closed form while a steeper slope gives a *smaller* slope-angle sigma; a more-accurate source (3DEP 1 m) yields a smaller slope sigma than a noisier one (SRTM GL3), tracking the catalog's `vertical_accuracy_m` |
| hillshade | The shaded relief encodes to a valid, self-contained PNG data URI whose single IDAT stream zlib-decompresses to exactly `height * (width + 1)` bytes (one 0x00 filter byte per scanline); a flat field is uniform, NaN cells render black, an oversized grid downsamples below `max_size`, and the encoded bytes are deterministic |
| fingerprint_library | A fresh draw of a known process ranks its matching reference first; the cross-body table maps each Earth candidate to the correct planetary reference (Mars-like, Moon-like), fills every candidate × reference cell with a float, and is deterministic |
| dossier | The recommended unit's dossier is flagged `is_recommended` with non-empty per-axis distances on the declared decision axes; an ineligible unit is blocked with its reason, empty distances, and no frontier/uncertainty — without raising; a bootstrapped run carries non-domination frequencies; the Markdown renders every metric and a verdict word |
| sensitivity | On a clear-winner synthetic scene the recommended unit is stable across all five default decision lenses and across a sweep of common supports (`lens_ablation`, `support_ablation`, and `ablation_report` agree, `overall_stable=True`); the ablation is deterministic |
| terrain_classify | Synthetic flat, rolling, and rough tiles classify as `flat_plain`, `rolling`, and `rough_rugged` as expected; the rule-based label, its evidence, per-type scores, and confidence are deterministic |
| references | The data-sources credits bundle lists a real citation and licence for every source across all five bodies (Mars, Earth, Moon, Mercury, Ceres), grouped by body; rendering is deterministic |
| integration (uncertainty + previews) | `feature_uncertainty` and `previews` are opt-in and absent by default, so the gated synthetic study `package_hash` is unchanged; when supplied they attach to the package and the HTML report and viewer render a "Measurement uncertainty" table and inline hillshade previews |
| openness / geomorphons | Topographic openness (Yokoyama 2002) is exactly 90° on a flat plane, rises above 90° (positive) at a cone apex and (negative) in a bowl; the geomorphon ternary signature (Jasiewicz & Stepinski 2013) classifies a cone as `peak`, a bowl as `pit`, a tilt as `slope`, and a plane as `flat`, is invariant to a uniform vertical lift and to whole-grid rotation, and its 9×9 spectrum / 10-form composition are deterministic and JSON-serialisable |
| landform (study + report/viewer) | The opt-in `landform=True` / `decision_metrics="landform"` paths attach a per-unit geomorphon composition + spectrum + openness block (and, with `previews=True`, categorical landform and grayscale openness PNGs); off by default the study package and its gated `package_hash` are byte-unchanged; the HTML report and viewer render a landform-composition table, openness medians, and the two literature citations, and are byte-identical when no landform block is present |
| spectral / anisotropy | The radially-averaged PSD (Perron 2008) places a single sinusoid's spectral peak at its true wavelength, returns a flat (~zero) log-log slope on white noise, and recovers the detrended variance by Parseval (`total_power`); the directional structure function (Shepard 2001) recovers the orientation and high strength of a lineated (ridged) surface and reports low strength on isotropic noise, with strength bounded in [0,1]; both signatures are deterministic and JSON-serialisable |
| scale & fabric (study + report/viewer) | The opt-in `terrain_spectra=True` path attaches a per-unit `spectral` + `anisotropy` block for every compared, eligible unit; off by default the study package and its gated `package_hash` are byte-unchanged; the HTML report and offline viewer render a "Scale & fabric" section when the blocks are present and are byte-identical when absent, and `descriptor_bank` + the terrain `fingerprint` carry opt-in spectral/anisotropy terms |
| common_grid | A footprint that is not a whole number of cells is **refused**, not rounded; the destination transform describes exactly `n` cells of the requested support, centred on the projection origin, in an azimuthal-equidistant CRS; the comparability gate rejects a support mismatch, a footprint mismatch, a cell-count mismatch and a record flagged inexact; the source-resolution floor is enforced before any descriptor is computed; a geographic source must declare its metric posting (otherwise a degree pixel size silently reads as metres and the floor becomes ~0); and the published defective comparison — Moon 500 m / 32 cells / 16.000 km against Earth 510 m / 31 cells / 15.810 km, recorded as `cells=[32, 32]` — is replayed end to end and **must be refused**. On real data, both bodies build identical 18 × 18 / 12 × 12 / 9 × 9 grids covering exactly 9000 m |
| evidence | Recorded ensemble counts are checked against each other: counts must be whole and ≤ the draw count, membership counts must equal the member slots the recorded sets imply, set counts must sum to the number of realisations, and every frequency must equal its own count over the draws. Twelve negative tests corrupt a record (a count contradicting its frequency, an impossible frequency, a missing candidate, lost draws, 7 of 6 draws, mismatched member slots, a frequencies-only record) and must each be detected — including one that decrements a number in the committed artifact |
| dependence | The slope/relief relation is derived (`relief = 2 d tan(slope) rho`, `rho` bounded in `[1, sqrt(2)]` and dependent only on the gradient's direction) and then checked **against the engine's own `slope_deg` and `relief`** on synthetic planes — worst error 4.4e-16 m and 1.4e-14 deg — so the lunar panel's three "axes" are shown to be one measurement rather than three. Effective rank, participation ratio, condition number and VIF are exercised on duplicated versus independent axes (three copies of one axis must rank 1; three independent axes must rank **3**, or the statistic is broken), the bound is checked over a dense grid of orientations, and `rho` is shown to be scale-free so the redundancy cannot be a resolution artefact |
| lunar adversarial | The stress test's declared perturbations, frozen in `config/lunar_adversarial_v1.yml` before the run, must equal the ones the module and the record actually contain — so "declared in advance" is mechanical rather than a claim about intent. The masks remove exactly the declared cells (including when every deviation ties); the DEM perturbations are deterministic per seed and do what they say (smoothing preserves the mean, a tilt moves the surface, an undeclared kind is refused); `axes_of` is pinned against the panel script itself so the stress test cannot drift into measuring something else; and the scorer is checked on the two mistakes this driver made first — references treated as mutual candidates, and single-support perturbations scored against supports they never ran. Every declared footprint/support combination must still be an exact whole-cell grid, and the record's summary (counts, fractions, reversing list, verdict) must reconcile with its own rows |
| verdicts | The three separable verdicts — relative ranking, absolute adequacy, evidence sufficiency — are checked as *rules* (unknown states refused; a missing band cannot be promoted to adequate; a band that admits known-different terrain is **demoted to NOT_ESTABLISHED** rather than reported as a positive; the sufficiency reasons are the declared ones) and as a *negative property*: the composition must keep all three visible when they disagree, and `conflation_errors` must fire on every way of collapsing them — a dropped part, a smuggled composite score (including one nested inside a sub-dict), an adequacy state with no calibrated band, a recommended unit outside its own non-dominated set, and a TIE state carrying a recommendation. A definite ranking beside NOT_ESTABLISHED adequacy must survive composition unreduced, and poor evidence must mark a ranking **provisional** rather than delete it |
| five-body geometry | Azimuthal equidistant's defining property — the distance from the projection centre to any projected point **is** the geodesic distance — is checked for **all five bodies**, against two closed-form geodesy implementations written in the test file rather than against another PROJ call: a great-circle distance on a sphere of the body's own radius for Mars, the Moon, Mercury and Ceres, and Vincenty's inverse formula on the WGS84 ellipsoid for Earth. Measured worst error: **1.4e-7 m** on Earth at 9 km. Each body's CRS must carry its own radius (a body-scale mistake must be visible by orders of magnitude, and the negative control proves it is); the site list includes the real lunar centre at −89.46°, not a convenient latitude. The grid arithmetic — `plan`, the affine coefficients, the footprint, pixel-centre alignment — must be **body-independent**, with only the CRS differing, so two sides of a comparison cannot disagree about what "500 m" means while both records look well formed. **Scope:** this is ANALYTIC validation on five bodies; the REAL-DATA validation is Earth and the Moon, and the test file declares those two lists and asserts they partition the five |
| harness | A test that cannot exercise its claim raises `Skip` with a reason instead of returning silently, and the runner reports SKIP separately from PASS and FAIL. This exists because a test which quietly returned when rasterio or a 40 MB product was absent printed PASS, letting "the suite is green" be read as "everything was verified" |

Every fixture has a known analytic answer; the runner exits non-zero on any failure.

## Automated scientific-correctness suite (`terratrace/validation.py`)

Beyond unit fixtures, `scripts/run_validation.py` drives the **real** comparison
pipeline on synthetic terrains with known relationships and asserts the engine's
descriptors, distances, and Pareto decision come out the way geomorphometry requires. All 51
of these checks pass:

| Check | Property proven |
|---|---|
| self_distance_zero | A unit compared with itself has an all-zero distance vector |
| translation_invariance | A vertical offset (+1000 m) changes no morphology axis (shape, not height) |
| rotation90_invariance | A 90° rotation leaves slope/relief/ruggedness distributions unchanged |
| monotonic_roughness_discrimination | Distance grows monotonically as a candidate is made rougher (real power) |
| dominance_recovery | A candidate closer on every axis provably dominates and is the recommendation |
| null_control | A same-statistics twin is closer than a 5× rougher impostor |
| water_candidate_blocked | A flat/zero (water-proxy) tile is BLOCKED by eligibility, not silently compared |
| determinism | Identical inputs reproduce an identical package hash |
| curvature_zero_on_plane | Profile, plan, and mean curvature vanish on a tilted plane and match the analytic paraboloid values (local convexity is measured, not slope) |
| vrm_discriminates_roughness | The Vector Ruggedness Measure is 0 on a plane and increases with surface roughness within [0,1], decoupled from mean slope |
| roughness_hurst_sane | The structure function grows with lag and the Hurst scaling exponent stays in [0,1] (1 on a smooth ramp, near 0 on white noise) |
| openness_flat | Topographic openness (Yokoyama 2002) is exactly 90° at every cell of a flat plane, for both positive and negative openness |
| openness_peak | At a cone apex positive (sky) openness rises above 90° while negative (ground) openness drops below 90° |
| openness_pit_mirror | At a bowl centre the mirror holds: negative openness rises above 90° while positive openness drops below it |
| geomorphon_flat | A flat plane is classified as `flat` in >95% of cells, with `flat` the dominant form |
| geomorphon_cone_peak | A radial cone apex classifies as `peak` |
| geomorphon_bowl_pit | A radial bowl centre classifies as `pit` (the antisymmetric mirror of the peak) |
| geomorphon_tilt_slope | A uniformly tilted plane classifies dominantly as `slope` |
| geomorphon_relief_invariance | Adding a uniform +100 m vertical offset leaves the geomorphon composition identical (shape, not height) |
| significance_clear_winner | On a clear-winner scene the engine recommends the closer candidate and the opt-in permutation block flags `recommendation_significant` true — the closeness gap to the reference beats random relabelling on at least one morphology metric |
| significance_near_tie_is_honest | On a near-tie scene the test does not manufacture a result: the engine either does not reach a lone recommendation, or reports `recommendation_significant` false, so a coin-flip gap is never dressed up as significant (no false positive) |
| confidence_robust_on_clear_winner | On the clear-winner scene, with both the bootstrap and significance blocks present, `decision_confidence` returns the `robust` verdict and both the bootstrap-non-domination and significance-vs-runner-up signals are evaluated and positive |
| confidence_fragile_or_tie_on_near_tie | On the near-tie scene the verdict is never `robust`: it downgrades to `fragile`/`qualified` or mirrors a non-recommendation state (`tie`/`indeterminate`), so weak evidence is reported honestly |
| spectral_sinusoid_peak | A single-wavelength sinusoid (period 8 cells) places the radially-averaged PSD peak at its true wavelength (`peak_wavelength_m` lands within one radial bin, 6-11 m) |
| spectral_white_noise_flat | Broadband white noise has a ~flat power spectrum, so the log-log `spectral_slope` is ~0 (|slope| < 1) — the descriptor separates scale-free noise from structured terrain |
| spectral_parseval | The summed spectral power (`total_power`) recovers the detrended variance to within 25% (Parseval), so the spectrum is correctly normalised |
| anisotropy_ridges_oriented | Parallel ridges (a one-directional sinusoid) are strongly anisotropic (strength > 0.5) with the fabric orientation along the invariant strike (within ±25°) |
| anisotropy_isotropic_low | Isotropic noise shows no preferred direction: the directional structure function is ~equal in every azimuth, so anisotropy strength < 0.25 |
| multiscale_identical_is_layer1_all_scales | Scale-resolved screening is self-consistent: on a 3-unit scene (reference, a NEAR twin, and a FAR unit carrying scale-persistent structure) swept over three ascending supports, the NEAR twin is Pareto layer 1 at *every* support |
| kh_roughness_plane_is_zero_rough_discriminates | The Kreslavsky–Head (2000) differential-slope baseline roughness is ~0 on a tilted plane (< 1e-6°, the second difference of a linear field) and strictly greater on a rough surface |
| iwahashi_pike_texture_and_convexity | The Iwahashi–Pike (2007) signatures behave as defined: surface texture is strictly greater on a seeded rough field than a smooth plane, and a radial dome reads as a convex location |
| drainage_flow_conservation_and_dissection | The depression-filled D8 flow descriptor conserves mass (every finite cell has `acc >= 1`, and outlet accumulations sum to exactly the finite-cell count) and its drainage texture discriminates roughness |
| wavelet_checkerboard_finest | The orthonormal 2-D Haar wavelet puts **all** detail energy at the finest level for a period-2 checkerboard (`dominant_level == 1`; Mallat 1989) |
| hypsometry_ramp_and_cross_consistency | A symmetric ramp has hypsometric integral exactly 0.5, and two independent implementations — the Strahler-exact and the engine's robust-quantile version — agree |
| normal_roughness_plane_zero_discriminates | Surface-normal-dispersion roughness is ~0 on a tilted plane (all normals parallel) and strictly greater on a rough surface (Hobson 1972; McKean & Roering 2004) |
| tpi_peak_ridge_pit_valley | Weiss (2001) TPI slope-position classification recovers the extremes: a radial cone apex classifies as `ridge` and a radial bowl centre as `valley` |
| fractal_plane_two_rough_higher | The differential box-counting fractal dimension measures ~2 on a tilted plane (`|D − 2| < 0.25`) and is strictly greater on a seeded rough field (Sarkar & Chaudhuri 1994) |
| lacunarity_uniform_one_clustered_higher | Gliding-box lacunarity is exactly 1.0 on a perfectly uniform field and strictly greater on a sparse clustered field (Plotnick, Gardner & O'Neill 1993) |
| entropy_constant_zero_complex_higher | Shannon slope entropy is 0 on a constant field and strictly greater on a complex multi-scale surface than on a single planar ramp (Shannon 1948) |
| slope_area_concave_positive_theta | A concave surface yields a **positive** Flint (1974) slope-area concavity index with a credible log-log fit (`r2 > 0.3`) |
| twi_decreases_with_slope | The Beven & Kirkby (1979) Topographic Wetness Index `ln(a / tan β)` is strictly greater on a gentler slope at equal contributing area |
| convergence_cone_divergent_bowl_convergent | The Köthe & Lehmeier (1996) convergence index resolves aspect-sign: > 0 (divergent) on a cone, < 0 (convergent) in a bowl, ~0 on a uniform plane |
| svf_flat_is_one_pit_lower | The Zakšek, Oštir & Kokalj (2011) sky-view factor is 1.0 on a flat surface, and a deeper bowl has a strictly smaller value than a shallow one |
| multiscale_tpi_cone_bowl_plane | The two-scale Weiss (2001) TPI classifier puts a cone apex in an upper-position class (`hilltop`/`upper_slope_ridge`) and a bowl centre in a lower one (`valley`/...) |
| variogram_whitenoise_vs_plane | The Matheron (1963) semivariogram is nugget-dominated on an uncorrelated white-noise field (nugget > half the sill) and steeply rising on a smooth plane |
| roughness_length_ramp_hurst_white_flat | The Shepard et al. (2001) RMS/Allan-deviation roughness has a deviogram Hurst in [0.8, 1.2] (~1, long-correlated) on a ramp and ~0 (flat, decorrelated) on white noise |
| curvature_classes_dome_bowl_saddle_plane | Wood (1996) morphometric curvature classes recover the textbook shapes at a quadratic's centre: dome → `peak`, bowl → `pit`, saddle → `pass`, tilted plane → `planar` |
| fabric_plane_cluster_vs_rough_isotropic | The Woodcock (1977) orientation-tensor fabric is a tight **cluster** on a plane (`isotropy < 0.05`, `C > 3`) and dispersed/isotropic on a seeded rough field |
| openness_difference_cone_ridge_bowl_valley | The Yokoyama (2002) openness-difference slope position is positive (ridge-dominated) on a convex cone and negative (valley-dominated) in a concave bowl |
| melton_flat_zero_and_cross_check_hi | The Melton (1965) relief scalars are 0 on a flat tile, and on a rough tile the elevation-relief ratio cross-checks the hypsometric integral (|Δ| < 0.05) |
| transect_plane_constant_slope | The swath/transect utility reads back a planar ramp's imposed geometry: `mean_slope` within 5% of the imposed 0.1 and strictly positive relief along the track |

The suite emits a hashed report (`--json`) whose hash covers the pass/fail outcomes,
so it is a stable, host-independent regression oracle.

## Performance (`terratrace/benchmark.py`)

`scripts/run_benchmark.py` pins end-to-end behavioural invariants (which state is
reached, which unit wins, what is blocked), checks hash stability, and profiles
wall-clock time vs grid size. A benchmark-driven optimisation of the local-relief
operator replaced a per-window `nanquantile` with an exact min/max (α=0) or a single
two-quantile call (α>0): a 96×96 study dropped from ~12 s to ~0.3 s (**~40× faster**)
with **bit-identical** outputs — verified by unchanged `relief` arrays and an
unchanged study `package_hash`. Performance is now characterised, not assumed.

## Independent cross-checks

Two cross-checks have been **performed**, not merely recommended. Both are reproducible from
the repository and both record what they found, including the parts that were inconvenient.

**The Earth DEM from a second mirror** (`scripts/verify_earth_mirror.py`). The headline Earth
path reads ESA Copernicus GLO-30 straight from the public AWS COG mosaic, keyless. Microsoft
Planetary Computer — a NASA Space Apps Global Offer — publishes the same ESA product from Azure
behind a public STAC API that needs no account. The script asks that API which item covers the
tile, so the mirror's own index decides what is compared, then reads the same tile from both and
compares the numbers. Result: **exact elevation-value agreement between two hosting paths for the
same ESA Copernicus product** — every one of the tile's 12,960,000 elevation values is identical,
while the two *files* are **not** byte-identical: they differ by 360 bytes of container metadata.
Both halves matter. A check that compared file sizes would have called this a data disagreement; a
check that compared filenames would have called it a match without looking. The record is
`artifacts/mirror_check/earth_cop30_mirror.json`, and `tests/test_earth_mirror.py` holds the
decision rule that separates the two cases, including that a network failure is reported as
BLOCKED and never as agreement. This is a provenance fact — a second host for one product — and
**not** independent corroboration: the Azure copy is the same ESA product, and the record says so.

**The reprojection against closed-form geodesy** (`scripts/reproject_analytic_check.py`). An
azimuthal-equidistant projection has an exact defining property — the distance from the projection
centre to any projected point *is* the geodesic distance — so the engine's reprojection is compared
against mathematics rather than against a second wrapper around the same GDAL library. See
[INDEPENDENT-GIS-REPRODUCTION.md](INDEPENDENT-GIS-REPRODUCTION.md), which also records that this
exercise caught the author's own arithmetic and not the code's.

Recommended on real runs, and not yet done:

- Re-derive slope/relief for a sample window in an independent GIS and compare.
- Confirm each product's CRS/bounds against its label (captured in `sources.lock.yml`).
- Inspect `scripts/inspect_study.py` output for degeneracy (zero-fraction, valid
  fraction, non-finite or all-zero vectors).

## Ablations

### A1 - Water contamination (data quality)

A coastal AOI (La Palma) was **97.9% ocean**; Copernicus encodes sea as 0 m, which
would masquerade as flat terrain. Mitigations, each tested: automatic eligibility
block above 60% zero pixels; opt-in masks; land-only default AOI. Lesson: validate
`frac==0` and valid fraction before trusting any real-DEM result.

### A2 - Core vs extended decision axes (robustness)

Same real inputs (Mars reference vs Nevada desert vs Craters of the Moon, Idaho),
reprojected to a 1 km local metric grid, water-clean:

| decision axes | result | reason |
|---|---|---|
| core (slope, relief, ruggedness, connectivity) | RECOMMEND Craters of the Moon | dominates all four bulk-roughness axes |
| extended (+ aspect dispersion, hypsometric integral) | **TIE** | Nevada is far closer on aspect dispersion (dist 0.007 vs 0.421) and hypsometric shape; neither unit Pareto-dominates |

Interpretation: the "best analog" is not well-defined independent of what is being
tested. Bulk roughness favors the lava field; directional texture and
elevation-distribution shape favor the desert. TerraTrace reports the tie rather
than forcing a winner. This is the central honesty of the tool.

### A3 - Sensitivity scenarios

Each run recomputes under four scenarios (slope threshold and relief tail), and
reports a pairwise rank-flip fraction. A recommendation is emitted only when a single
unit is non-dominated and stable (flip <= 0.1); otherwise TIE/INDETERMINATE.

## Reproducibility

`scripts/make_source_lock.py` records each input's SHA-256, size, CRS, bounds, and
required citation. The study package embeds a canonical `package_hash`
(`run_study` is deterministic across runs). A reviewer can regenerate a study from the
locked sources and compare hashes.

## Known limitations

- 463 m MOLA is the limiting support; no sub-support (rock/obstacle-scale) claims.
- Copernicus is a surface model (vegetation/buildings) and encodes water as 0 m.
- Reprojection uses a local azimuthal-equidistant grid per AOI; extreme-latitude or
  very large AOIs should use an area-appropriate projection.
- No field or simulation outcome data yet exists, so no transfer-performance claim is
  made or validated.
- Bootstrap confidence intervals default to the `independent`-pixel method, which assumes
  independent pixels and is therefore **optimistic** (too narrow) on real, spatially
  autocorrelated DEMs. The opt-in `block` bootstrap (`bootstrap_method: block`, `block_size`
  at or above the terrain correlation length) now resamples spatial blocks for honest, wider
  CIs; `independent` remains the default, so its optimism caveat still applies unless `block`
  is selected.
