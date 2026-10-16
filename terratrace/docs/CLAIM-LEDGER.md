# TerraTrace — Claim-to-Evidence Ledger

Every important claim points to an actual experiment, its status, its uncertainty, and
what would falsify it. Three achievement types are kept separate: **[IMPL]** software
correctness, **[METHOD]** empirical method validation, **[DISCOVERY]** a scientific
result about Mars. Passing tests establishes [IMPL], not [DISCOVERY].

Branch: `research/matched-footprint-benchmark` (local; not pushed). Baseline at start:
`run_validation.py` 51/51 (exit 0), full suite 686 green (verified in chunks; single-run
exceeds the sandbox tool cap), gated study hash `8f4890777ee462a2…`.

| # | Claim | Type | Evidence (experiment) | Status | Uncertainty / limits | Falsifier |
|---|---|---|---|---|---|---|
| 1 | A matched-footprint harness separates spatial **support** from spatial **extent**, records provenance (metric dims, valid area, source spacing, effective resolution, usable blocks), and flags upsampling — wrapping, not replacing, `compare_units`. | IMPL | `terratrace/matched_benchmark.py`; `tests/test_matched_benchmark.py` (12 tests); gated study hash unchanged. | **Implemented + tested** | Wraps the existing decision; inherits its assumptions. | A test showing extent/support are still conflated, or the gated hash changing. |
| 2 | On synthetic ground truth (rough core in a smooth apron), a **matched** comparison recovers the correct core analog (`B_rough`) while a **mismatched** (ref ≫ candidate footprint) comparison flips to the wrong one (`A_smooth`). | METHOD | `run_matched_benchmark.py --synthetic`; `test_matched_small_extent_recovers_rough_core`, `test_mismatched_footprint_flips_to_wrong_analog`. | **Method-validated (confirmatory, synthetic)** | Synthetic; amplitudes chosen to illustrate the confound. Says nothing about Mars. | A matched comparison that returns the wrong core analog on this fixture. |
| 3 | The confound mechanism is a **window-size roughness dilution**: the reference's median ruggedness drops ~5× (6.3 → 1.2) when the window is enlarged from the core to the apron. | METHOD | `test_confound_mechanism_reference_roughness_drops_with_extent`. | **Method-validated** | Magnitude is fixture-specific; direction is general. | Ruggedness not decreasing when a rough core is diluted by a smooth apron. |
| 4 | At matched footprint, naive **slope-only / relief-only baselines agree** with the full decision (both pick `B_rough`) — the matched answer is not an artifact of the complex machinery; the machinery adds confound-detection + honest lens trade-offs/abstention. | METHOD | `test_single_descriptor_baselines_agree_at_matched_footprint`; `lens_ablation_matched` (core/geomorphic/landform/texture → B_rough; extended/hydro → TIE). | **Method-validated** | Baselines agree *here*; on other scenes the full approach may diverge (that is its value). | Baselines disagreeing with the full decision at matched footprint with no interpretable reason. |
| 5 | **Spatial-block bootstrap** (primary uncertainty) and a conservative **selection-aware (Bonferroni) correction** are available and surfaced through the harness. | IMPL | `matched_cell(..., bootstrap_method="block")` surfaces non-domination freq; `selection_adjusted_pvalue`; `test_block_bootstrap_surfaces_through_harness`, `test_selection_adjusted_pvalue_is_conservative_and_bounded`. | **Implemented + tested** | Bonferroni is deliberately conservative and does not itself model spatial dependence (the block bootstrap does). Not yet applied to real data. | — |
| 6 | **Craters-of-the-Moon ↔ Mars volcanic-plains is a footprint-robust morphological analog.** | DISCOVERY | *(the primary research question)* — real matched-footprint run per `config/matched_footprint.example.yml`. | **UNVERIFIED / exploratory only** | The original finding used a ~15× footprint mismatch (a real confound). Requires `rasterio` + cached DEMs on the user's machine (sandbox has no rasterio/egress). | Under matched footprint, the recommendation changes or Craters becomes dominated → the exploratory analog was partly a footprint artifact (a valuable negative result). |
| 7 | Our contribution is an **integration + falsification stance** (matched-footprint, support-controlled, selection-aware, abstaining analog screening), **not** "first quantitative Earth–Mars terrain comparison". | ASSESSED | Bounded literature review (search snippets): quantitative terrain comparison for rover testbeds (NHSJS 2026), global geomorphometric Mars maps, Earth–Mars SMILES volcanic morphometry. | **Assessed (sources consulted)** | Could not fetch full papers (egress blocked); the 14 official 2026 Space Apps challenges are not yet individually mapped to this project. | A prior tool shown to already do matched-footprint, support-resolved, selection-aware analog screening with abstention. |

## Iteration-1 interpretable result (stopping condition met)

The primary research question now has an **interpretable, reproducible answer at the
method-validation level**: the matched-footprint instrument provably separates support
from extent and *detects and corrects a known footprint confound* on synthetic ground
truth (claims 1–4). The **Mars–Earth scientific answer (claim 6) remains open and is
honestly marked UNVERIFIED** — it is blocked only by `rasterio`/DEM access and is a
single documented command away on the user's machine. No result was forced; the
exploratory Craters finding is treated as a hypothesis to test, not to preserve.

**Next highest-value action:** implement the real runner (windowed, per-body
reprojected crops) and execute `config/matched_footprint.example.yml` on a
rasterio-equipped machine to answer claim 6, then record the outcome here.

## Iteration 2 additions (2026-10-15, same branch)

| # | Claim | Type | Evidence | Status | Limits / falsifier |
|---|---|---|---|---|---|
| 8 | A real matched-footprint runner exists: windowed per-body **reprojected** crops to a common metric extent, then the matched / mismatched / scale-grid comparison on REAL DEMs, reusing the engine's warp path. | IMPL | `terratrace/matched_real.py`; `scripts/run_matched_benchmark.py --config`; `tests/test_matched_real.py` (10 — offline, via monkeypatched metric grids). | **Implemented; pure core tested.** The `rasterio` read/reproject seam (`load_metric_grids`) is the ONLY part UNTESTED in this sandbox (no rasterio) — it is exercised by the user's real run. | Falsifier: on the data machine the reprojected crops come out wrong (extent/CRS/longitude convention) — verify on first run. |
| 9 | An **adversarial robustness** mode reports how far a recommendation can be trusted under bounded, justified perturbations (crop-origin shift, support step, correlated-noise/tilt/smoothing, lens family, candidate dropout). | IMPL + METHOD | `terratrace/adversarial.py`; `tests/test_adversarial.py` (5). Synthetic clear winner `B_rough`: stable_fraction 0.69, verdict "qualified"; a near-tie resolves to conflicting winners → "fragile". | Exploratory stress analysis, SEPARATE from confirmatory evidence; a persistent TIE is never "robust" (explicit honest guard). | — |
| 10 | **Absolute adequacy** is calibrated from the reference's OWN internal variability (held-out sub-windows): a candidate is "adequate" only within that band, else "inadequate"; if the reference can't be split, it reports "absolute morphological adequacy has not been established". | IMPL + METHOD | `terratrace/adequacy.py`; `tests/test_adequacy.py` (6). Twin (same roughness) adequate; 10× smoother impostor inadequate; tiny reference → not established. | NOT a universal analog score; relative to the reference's variability; distinct from the Pareto "best among candidates" question. | — |

**Suite status (honest):** the 686-test baseline is untouched (`git status` shows no
existing engine or test file modified; gated study hash `8f4890…` unchanged). The
**+33 new branch tests** (matched_benchmark 12, matched_real 10, adversarial 5,
adequacy 6) were verified green **directly**. The full ~719-test run exceeds the
sandbox per-call time cap and is left to **CI on push** — it is NOT claimed as
locally completed.

## Iteration 3 (2026-10-16, branch `research/m3-honest-regime`)

**Real v1 result (Daedalia Planum vs 3 Earth candidates), recorded exactly as produced:** Craters of
the Moon was the sole core-lens recommendation at 500, 1000 and 2000 m; spatial-block
non-domination: Craters 1.0, Nevada 0.0, Andes 0.0; the 10x mismatched-footprint control agreed;
slope-only and relief-only baselines agreed; lens ablation: core/geomorphic/landform -> Craters,
extended/texture/hydro -> TIE.

**Inspection of that bundle's own provenance (comparability gate) — the caveats that downgrade it:**

| support | regime | detail |
|---|---|---|
| 500 m | footprint-mismatched + below-effective-resolution | Earth tiles truncated: Craters 24.4 km, Andes 33.2, Nevada 36.1 vs Mars 39.8 (ratio 1.63); MOLA effective resolution ≈ 1389 m |
| 1000 m | footprint-mismatched + below-effective-resolution | same |
| 2000 m | footprint-mismatched | ratio 1.63 |

| # | Claim | Type | Status | Why / falsifier |
|---|---|---|---|---|
| 6 (updated) | Craters-of-the-Moon ↔ Daedalia Planum is a footprint-robust morphological analog. | DISCOVERY | **EXPLORATORY — not confirmed.** Consistent with the hypothesis, but no v1 cell was in an honest regime, and both defects favour the smoothest, smallest-window candidate (Craters). | Tested by protocol v2 (frozen before any v2 result): H1 confirmation on 3 held-out plains, H2 specificity on 2 contrast terrains, H3 resolution-matched control, H4 adequacy. |
| 11 | The comparability gate labels a cell honest only if footprints are truly matched (no truncation, extent ratio ≤ 1.05) and support ≥ every unit's effective resolution. | IMPL | Implemented + tested (`comparability.py`, 13 tests); reproduces the v1 defect from the real numbers. | — |
| 12 | Resolution matching removes a source-smoothing false analog on synthetic ground truth. | METHOD | Method-validated (`resolution.py`, 12 tests): a smooth impostor wins against a coarsely observed reference; after matching, the true twin wins. At 900 m the matched run returned INDETERMINATE rather than the twin. | Depends on the 3× effective-resolution heuristic. |
| 13 | The panel separates a specific analog relationship from a non-specific "closest member of a weak shortlist" effect. | METHOD | Method-validated (`confirmation.py`, 12 tests; v2 integration, 25 tests in `test_matched_real.py`). | — |

**Suite status (verified locally, all chunks completed):** 771 passed, 0 failed (86 files, run in 8
chunks; none timed out). Validation 51/51. Gated study hash unchanged.

**Next action:** run `config/matched_footprint_v2.yml` on the data machine and record H1–H4 here
exactly as produced (stopping rule in `BENCHMARK-PROTOCOL-v2.md`).

## Iteration 4 — protocol v2 RESULTS (2026-10-16; full write-up `RESULTS-v2.md`)

Recorded exactly as produced by the frozen rules: **H1 NOT SUPPORTED** (0/3 confirmatory plains hold),
**H2 INCONCLUSIVE** (not evaluable — no honest-regime recommendation anywhere), **H3 NOT SUPPORTED**
(primary changed under resolution matching), **H4 reported** (no recommended unit to assess).

| # | Claim | Type | Status | Evidence / limits | Falsifier |
|---|---|---|---|---|---|
| 6 (final) | Craters of the Moon ↔ Mars volcanic plains is a specific, footprint-robust morphological analog. | DISCOVERY | **NOT SUPPORTED — withdrawn.** | v2 honest regime: abstention at all 14 cells; Craters nearest for a cratered highland (Noachis) as readily as for plains; outside Daedalia's and Elysium's own variability. | A future, pre-registered, adequately powered test with smoothness-matched controls in which Craters beats them for plains but not highlands. |
| 14 | With MOLA + COP30, these three candidates and 24 km windows, the data do not support a specific Craters–plains relationship; the earlier preference is explained at least in part by footprint mismatch and below-resolution comparison. | DISCOVERY (negative) | **Supported by the frozen v2 protocol (H1) + v1-vs-v2 contrast.** | Low power (12–16 cells/side); one source per body (not independent replications). | Reversal of H1 in an adequately powered re-run of the same frozen design. |
| 15 | Craters' advantage is a non-specific "least-dissimilar member of a weak shortlist" (smoothness) effect. | INTERPRETATION | **Consistent with v2, NOT directly tested** (descriptive analyses 1–4 in `RESULTS-v2.md` are not pre-registered). | Smoothness explanation inferred, not measured against a smoothness-matched control. | v3: a smoothness-matched non-volcanic Earth control does NOT compete with Craters for Mars plains. |
| 16 | Protocol lesson: the frozen H3 rule ("any change") could not distinguish a recommendation that was *stabilised* by resolution matching from one that was *reversed*. | METHOD | Recorded; verdict NOT altered. | Under matching the nearest candidate was unchanged in all 11 cells; only INDETERMINATE → RECOMMEND. | — |

**Three achievements, kept separate (as of iteration 4):** software correctness — 771 tests green;
method validation — synthetic ground truths for footprint, resolution and specificity controls;
scientific discovery — **one reproducible negative result** (claim 14); no positive analog claim stands.
