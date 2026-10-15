# TerraTrace Matched-Footprint Benchmark Protocol

**Status: v1, frozen 2026-10-15 (before the real Mars–Earth confirmatory run).**
This protocol is fixed in advance; the real matched-footprint evaluation data have
**not** been examined at freeze time (they require `rasterio` on the user's machine
and have not been produced). This separation is the point: the synthetic result
below is *method validation*; the real result will be *scientific discovery*.

## Primary research question (iteration 1)

Does the exploratory Craters-of-the-Moon ↔ Mars-volcanic-plains morphological analog
survive a **matched-footprint, support-controlled** comparison, or is it (wholly or
partly) an artifact of the ~15× footprint mismatch and source-resolution difference
in the original exploratory run?

**Primary user / decision:** a planetary geomorphologist screening Earth terrains for
further morphological investigation of a Mars reference terrain.

## The two controls (never conflated)

| Control | Meaning | Experiment type |
|---|---|---|
| `extent_m` | physical side length each unit is cropped to **before** aggregation | vary at fixed support → *extent* experiment |
| `support_m` | aggregation cell size handed to `compare_units` | vary at fixed extent → *scale* experiment |

- **Matched footprint:** every unit cropped to the *same* `extent_m` (comparability).
- **Mismatched footprint:** reference `extent_m` ≫ candidate `extent_m` (reproduces the
  original confound; used only as a control contrast).
- **No upsampling:** `support_m` below `effective_resolution_m = 3 × source_spacing`
  is flagged `upsampling_risk`; resampled grid spacing is never read as independent
  source resolution.

## Metadata recorded for every (unit, extent, support) cell

AOI selection rationale (in the config); realized metric extent; valid-area fraction;
source grid spacing + effective resolving capability; common support; descriptor
neighbourhood (support in metres); usable spatial-block count; truncation flag;
upsampling-risk flag. (See `matched_benchmark.cell_provenance`.)

## Candidate selection (real run)

Modest, scientifically diverse, **chosen for morphological reasons, not fame**:
a plausible analog, a plausible near-miss, and a contrasting control — each cropped
to the *same* physical extent as the Mars reference window. Expand beyond the current
three Earth candidates where DEMs are available. Do **not** pick AOIs to manufacture
a preferred winner.

## Predeclared success / failure conditions (real run — frozen)

For the Mars volcanic-plains reference vs the Earth candidate set, under matched
footprint across a support sweep:

- **S1 — analog robust (supports the exploratory finding):** Craters of the Moon
  remains Pareto non-dominated (and the core-lens recommendation) across the matched
  extents and supports, and under matched footprint specifically.
- **S0 — analog is footprint-sensitive (negative finding, still valuable):** under
  matched footprint the recommendation changes, Craters becomes dominated, or the
  matched answer differs from the mismatched answer — i.e. part of the exploratory
  result was a footprint/resolution artifact.
- **Abstention (TIE / INDETERMINATE) is an acceptable, informative outcome** and must
  not be hidden. A positive result is not required.

## Method-validation result (synthetic, confirmatory for the harness)

Reproduce offline: `python scripts/run_matched_benchmark.py --synthetic`.

A reference with a small **rough core** (texture amp 25) inside a large **smooth
apron** (amp 4) is compared with a uniformly-smooth and a uniformly-rough candidate.
Ground truth for the core AOI: the reference is rough → `B_rough` is the correct
analog. Measured:

- **matched @ core extent (1200 m)** → recommends **B_rough** (correct).
- **mismatched (ref 12000 m, candidates 1200 m)** → recommends **A_smooth** (wrong:
  the rough core is diluted by the smooth apron — reference ruggedness median drops
  6.3 → 1.2, a 5× window-size artifact).
- Matched ≠ mismatched: the matched-footprint protocol **recovers the known-correct
  analog that the mismatched comparison misses.**

This validates the *instrument*. It says nothing yet about Mars.

## Three achievements kept separate

1. **Software correctness** — `tests/test_matched_benchmark.py` (8 tests) + the full
   suite; gated default study hash `8f4890…` unchanged.
2. **Empirical method validation** — the synthetic confound above (confirmatory for
   the harness).
3. **Scientific discovery** — the real Mars–Earth matched-footprint answer. **Not yet
   produced; requires the real run (below).**

## Real confirmatory run (next action — user's machine)

Config: `config/matched_footprint.example.yml`. Requires `rasterio` + the cached DEMs
(`data/mars/mola_463m.tif`, `data/earth/*.tif`).

**Resource estimate (bounded, offline-safe):** read **windowed** crops only — never
load the 2.1 GB global MOLA fully. Comparable extent ≈ 40 km → Mars ≈ 86 px (at
463 m), Earth ≈ 1333 px (at 30 m); aggregated to 500–2000 m support → tens of cells
per side. ~6 units × ~4 extents × ~3 supports ≈ 72 compare_units calls, seconds each.
Expected < 2 min wall-clock, < 1 GB RAM with windowed reads. No network, no API key
(MOLA + already-cached COP30).

**Status of the real runner:** the synthetic path is implemented and tested; the real
path (crop on the per-body reprojected metric grid via windowed `rasterio` reads) is
the smallest next build and is intentionally **not** stubbed as if complete.
