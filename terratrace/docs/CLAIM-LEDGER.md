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
