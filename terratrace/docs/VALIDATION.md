# Validation and ablations

TerraTrace is validated at the level it claims: **map-scale terrain morphology
screening**. These checks establish software/metric correctness, data handling,
sensitivity, and provenance. They do **not** establish rover traversability,
autonomy, geologic equivalence, site access, or mission readiness.

## Test suite (184 fixtures, `tests/run_tests.py`)

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
| reproject | Body-correct CRS strings (Mars sphere vs WGS84), centroid, grid sizing, unknown-body guard |
| catalog | 10-source registry validates; coverage + body-mismatch; `recommend_source` preference/least-download/keyless; SRTM band excludes >60°N; nodata sentinels |
| preflight | bbox well-formedness + body bounds; area/pixel/download sizing; config-schema (dup ids/paths, demtype-vs-dataset); non-US routing |
| profile | valid/water/NaN fractions; robust relief; advisory vs blocking flags; water==masks.zero_fraction |
| fetchcache | sha256 matches sourcelock; needs_fetch skip/mismatch; manifest round-trip + update |
| ingest | TIFF magic-byte guard rejects error-JSON; `_stream` retry/backoff + Retry-After + fail-fast |
| sourcelock | SHA-256 matches hashlib; citations/terms per body; missing-file entry |
| study (e2e) | Contract keys present; ineligible unit excluded; close unit dominates far; deterministic package hash; all-blocked -> BLOCKED; evidence graph has eligibility+result+protocol nodes; extended mode adds two dimensions |
| batch | Cross-reference × multi-lens synthesis: the same-statistics twin is the sole consensus analog; a far-rougher candidate is never non-dominated; deterministic, JSON-serialisable report |
| validation | The engine passes every scientific-correctness check (see below) |
| benchmark | Pinned behavioural invariants + hash stability + a scaling profile |

Every fixture has a known analytic answer; the runner exits non-zero on any failure.

## Automated scientific-correctness suite (`terratrace/validation.py`)

Beyond unit fixtures, `scripts/run_validation.py` drives the **real** comparison
pipeline on synthetic terrains with known relationships and asserts the engine's
descriptors, distances, and Pareto decision come out the way geomorphometry requires. All
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

## Independent cross-checks (recommended on real runs)

- Recompute slope/relief for a sample window in an independent GIS and compare.
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
