# Validation and ablations

TerraTrace is validated at the level it claims: **map-scale terrain morphology
screening**. These checks establish software/metric correctness, data handling,
sensitivity, and provenance. They do **not** establish rover traversability,
autonomy, geologic equivalence, site access, or mission readiness.

## Test suite (46 fixtures, `tests/run_tests.py`)

| Area | What the fixtures prove |
|---|---|
| features | Slope equals the analytic value on a known plane; relief exact on a ramp; ruggedness ~0 on a plane and scale-linear; connectivity counts the true largest component; aspect dispersion ~0 on a plane and high on noise; hypsometric integral 0.5 on a ramp, NaN when flat |
| support | Block aggregation on constants, a known 2x2 mean, nodata/valid-fraction tracking, common-factor guards |
| distances | Wasserstein-1 = 0 for identical, = c for a shift; KS 0/1 bounds; NaN ignored; degenerate scale stays finite; all-constant -> 0 |
| decision | Pareto dominance and non-dominated sets; rights allowlist fails closed; water (zero-fraction) block; stable-winner vs tie resolution |
| masks | Sentinel/below/above masking to NaN; zero-fraction; input not mutated |
| reproject | Body-correct CRS strings (Mars sphere vs WGS84), centroid, grid sizing, unknown-body guard |
| sourcelock | SHA-256 matches hashlib; citations/terms per body; missing-file entry |
| study (e2e) | Contract keys present; ineligible unit excluded; close unit dominates far; deterministic package hash; all-blocked -> BLOCKED; evidence graph has eligibility+result+protocol nodes; extended mode adds two dimensions |

Every fixture has a known analytic answer; the runner exits non-zero on any failure.

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
