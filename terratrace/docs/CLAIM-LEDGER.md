# TerraTrace — Claim-to-Evidence Ledger

Every important claim points to an actual experiment, its status, its uncertainty, and
what would falsify it. Three achievement types are kept separate: **[IMPL]** software
correctness, **[METHOD]** empirical method validation, **[DISCOVERY]** a scientific
result about Mars. Passing tests establishes [IMPL], not [DISCOVERY].

Branch history: this ledger was opened on `research/matched-footprint-benchmark` at iteration 1
(superseded by `research/m3-honest-regime`, now merged to `main`). Baseline when it was opened:
`run_validation.py` 51/51 (exit 0), full suite 686 green (verified in chunks; single-run
exceeds the sandbox tool cap), gated study hash `8f4890777ee462a2…`. The suite has grown at every iteration since. **Counts inside this ledger are dated snapshots by
design** — the current figure lives in the README and in the test runner's own banner, where
`scripts/doc_consistency_check.py` checks it, so a snapshot written here cannot silently become a
stale claim.

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

**Suite status (verified locally, all chunks completed):** 800 passed, 0 failed (86 files, run in 8
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

**Three achievements, kept separate (as of iteration 4):** software correctness — 800 tests green;
method validation — synthetic ground truths for footprint, resolution and specificity controls;
scientific discovery — **one reproducible negative result** (claim 14); no positive analog claim stands.

## Iteration 5 — protocol v3 RESULTS (2026-11-05; full write-up `RESULTS-v3.md`)

Recorded exactly as produced by the v3 rules: **S SUPPORTED** (3/3 confirmatory plains hold),
**V NOT SUPPORTED** (0/3 plains hold; V holds for both highlands), **R SUPPORTED** (0 reversals
in 15 confirmatory honest cells). All 15 confirmatory honest cells were in the honest regime —
unlike v2, where none were.

**Qualification, stated plainly:** v3 was **pre-specified but not fully pre-registered**. The
decision rules were committed on 2026-10-16 before any v3 data existed, and the config was written
708 s before the result bundle and is unmodified since (hashes in `BENCHMARK-PROTOCOL-v3.md`), but
the protocol *document* was committed **after** the run. This is weaker than v2's
commit-before-run and is not presented as equivalent.

| # | Claim | Type | Status | Evidence / limits | Falsifier |
|---|---|---|---|---|---|
| 15 (updated) | Craters' advantage was a non-specific "least-dissimilar member of a weak shortlist" (smoothness) effect. | DISCOVERY | **SUPPORTED — now directly tested, not inferred.** v2 called this "consistent, NOT tested"; v3 tested it. | 3/3 confirmatory plains references put a smooth **non-volcanic** control (Nullarbor limestone σ 5 m; Llano Estacado sedimentary σ 14 m) in Pareto layer 1 at every honest support; V fails 0/3 for plains while holding for both highlands. | A pre-registered test where a smooth *specifically volcanic* terrain beats the smooth non-volcanic controls for plains but not highlands. Deccan Traps is the closest case here and does not. |
| 17 | The nearest Earth analog tracks **km-scale roughness**, not volcanic origin. | DISCOVERY | **Supported by the frozen v3 protocol (S + V jointly).** | Smooth refs → smooth candidates; rough highland refs → rough **basaltic** candidates; the one smooth basalt (Deccan σ 32 m) competes for the roughest plains ref as a *smooth* unit. | A panel in which class membership predicts the frontier beyond what a roughness scalar does. |
| 18 | A keyless, credential-free Earth-DEM path exists that is **bit-identical** to the OpenTopography COP30 product. | IMPL | **Implemented + proven.** | `terratrace/cop30_cog.py` reads the public ESA GLO-30 COG mosaic on AWS via windowed HTTP range requests; `tests/test_cop30_cog.py` (17 tests) asserts max absolute difference **0.0 m** and 100 % identical pixels against the cached OpenTopography AOI tiles. | A bbox where the two disagree by more than float rounding. |
| 19 | The v3 reference set was corrected by verification, not by assertion. | IMPL + METHOD | **Implemented + tested.** | IAU Gazetteer (2052 features) verified every centre; **Solis Lacus is an albedo feature** (the plain is Solis Planum); **Lunae Planum is misclassified as volcanic** (a dissected highland, σ 41 m) and was dropped; **Terra Cimmeria's proposed point sampled Martz crater's interior** (σ 604 m); **Arabia Terra's proposed point sat on Cassini's rim**. All fixes were made **before** any v3 result existed. | — |
| 20 | The v2 H3 lesson is repaired: stabilisation and reversal are now distinct. | METHOD | **Implemented + tested** (`classify_resolution_change`, 21 rule mutants killed in `test_panel_v3.py`). | In the real v3 run, 3 membership_changed + 1 destabilised cells did **not** trip R, whereas v2's "any change" rule would have failed on a mere stabilisation. | A cell classified as unchanged/reversed that is the other. |

**One honest soft spot, reported rather than hidden:** the adversarial stress test on the primary
reference (`mars_arcadia` @1500 m) returns **fragile** (stable 0.86 over 21 bounded perturbations;
reverses under a 6-px crop-origin shift and under dropping either smooth control). The *class-level*
S pattern is robust (holds at every support, unchanged under resolution matching), but the *single
top-of-shortlist* pick is a near-tie among similarly smooth terrains and should not be over-read.

**Four achievements, kept separate (as of iteration 5):** software correctness — 817 tests green at
the time of that result, **854** in the shipped tree (the v3 entry added tests after this line was
written); method validation — synthetic ground truths for footprint, resolution and specificity
controls; scientific discovery — **one reproducible negative result (claim 14) and one reproducible
positive mechanism (claims 15/17)**; engineering — a credential-free, bit-identical data path
(claim 18). Still no claim that any Earth terrain is a mission-relevant Mars analog.

## Iteration 6 — corrections from an external review of the repository

Four entries. The first two are defects in *our own presentation* and are recorded because a claim
ledger that only lists successes is not a ledger.

| # | Claim | Type | Evidence | Status | Limits / falsifier |
|---|---|---|---|---|---|
| 21 | The v3 resolution-robustness result covers 15 confirmatory cells: 11 unchanged, 1 destabilised, 3 membership-changed, 0 reversed, 0 stabilised, 0 error. | PRESENTATION | `artifacts/mf_panel_v3/matched_panel_v3_real.json` → `hypotheses.R.counts` | **Corrected.** An earlier presentation listed only 11/3/0 — fourteen cells for a fifteen-cell experiment — dropping the destabilised cell (`mars_solis` @1500 m, where matching the footprint turns a RECOMMEND into a TIE). Now stated in full everywhere, with `tests/test_v3_archival.py` failing the build on any breakdown that does not sum or that omits a non-zero class. | The set of *public surfaces* scanned by that test is a fixed list; a new page quoting a breakdown must be added to it. |
| 22 | The v3 config was "unmodified since" the run. | PROVENANCE | `git show 820c17d:…matched_footprint_v3.yml` vs HEAD; `ddb2247` | **Corrected — the claim was false.** The config's recorded sha256 (`70eeafd4…`) is the revision at the result commit; the file shipped at HEAD (`98535076…`) differs by one comment: the Nevada Basin σ annotation, corrected from ~244 m to the measured 562 m nine minutes after the result. Every analytical parameter is byte-identical (parameter digest `ff3add2c…`). Reconciled in `docs/V3-ARCHIVAL-CLARIFICATION.md` and guarded by a test. | If a future edit changes a parameter rather than a comment, the guard fires; if it changes a comment, the two file hashes diverge again but the parameter digest does not. |
| 23 | The catalogued lunar source `moon_lola_ldem` is resolvable. | DATA | HTTP fetch of its `access.endpoint` | **FALSE — the endpoint is dead.** `https://astrogeology.usgs.gov/search/map/lunar_lro_lola_global_ldem_118m` returns a 200 whose body is the USGS "Error 404" page (2026-11-13). The lunar half of the challenge is therefore **blocked on data**, not on capability: body metadata, CRS and reprojection are lunar-ready in code. Recorded in `docs/LUNAR-STATUS.md`. | Unblocked by any working URL for a lunar DEM better than ~500 m posting. |
| 24 | TerraTrace's slope and 3×3 local-relief operators are reproduced by an independent toolchain. | VALIDATION | `scripts/gis_reproduction.py`; RichDEM + WhiteboxTools 2.3.6 | **Supported, with a stated boundary.** Relief reproduces to 1e-4 m; slope means agree to 0.016° absolute (per-cell \|Δ\| mean ≤ 0.044°) — *given the same elevation array*. The reprojection is **not** independently reproduced: TerraTrace uses rasterio, which is GDAL. Internally prepared; no external reviewer. See `docs/INDEPENDENT-GIS-REPRODUCTION.md`. | Two implementations can share a misconception. This does not validate the gate, the supports or any verdict. |

## Iteration 7 — the transformation mission (M1–M8)

Eight entries. Two of them are results that **weaken this project's own headline**, and they are here
at the same prominence as the passes because that is the only reason to keep a ledger at all. Each
number below is read out of the record named in its Evidence column, not remembered.

| # | Claim | Type | Evidence | Status | Limits / falsifier |
|---|---|---|---|---|---|
| 25 | The three declared lunar descriptors — mean slope, mean 3×3 relief, elevation σ — span **one dimension**, so the lunar panel is one-dimensional whatever the axis count suggests. | DISCOVERY (negative) | `artifacts/dependence/dependence_audit.json`; `scripts/dependence_audit.py`; `terratrace/dependence.py`; derived as well as measured: `relief = 2·d·tan(slope)·ρ` with ρ = (\|a\|+\|b\|)/√(a²+b²) ∈ [1, √2], so mean slope and mean 3×3 relief are the same measurement up to a direction factor bounded by 41 %. | **Derived AND measured.** Effective rank **1** at every support, over both the candidate pool and the wider cross-body pool; the Pareto frontier is invariant to dropping any single axis. | Holds for *these* descriptors on *this* terrain family. A genuinely non-redundant axis (e.g. curvature or a spectral statistic) would break it — which is the point of falsifying it. |
| 26 | The lunar headline survives 30 declared perturbations: 28 of 30 counted perturbations leave the layer-1 frontier untouched (**0.933**, verdict ROBUST against a threshold of 0.80 frozen before the run). | METHOD | `config/lunar_adversarial_v1.yml` (committed before the run); `artifacts/lunar_adversarial/lunar_adversarial.json`; `terratrace/lunar_adversarial.py`; `tests/test_lunar_adversarial.py`. | **Robust, with two named exceptions.** The reversals are `footprint:3000m` (11 cells) and `add_unit:earth_andean_volcano` (7 cells) — both recorded, neither absorbed. A 31st row (`info_drop_winner`) is informational and excluded from the denominator because removing the winner and observing no winner is not a test. | The perturbation families are ours, so this bounds sensitivity to the perturbations we thought of. It is a stress test, not a proof of stability under all perturbations. |
| 27 | Relative **ranking**, absolute **adequacy**, and evidence **sufficiency** are three separable verdicts, and no composite analog score exists anywhere in the engine or its outputs. | IMPL | `terratrace/verdicts.py`; `artifacts/discovery_atlas/discovery_atlas.json` → `verdict`; `tests/test_verdicts.py`; the atlas asserts `conflation_errors(...) == []` and walks its own JSON for score-like keys. | **Implemented and enforced.** On the lunar panel these three land in three different places — see 28 — which is the only way to show they are not one number wearing three names. | Three separated verdicts are still three claims; separability does not make any of them adequate. |
| 28 | **Adequacy is NOT established at any lunar cell** — 18 of 18. The reference's own morphological variability band admits 4 of the 5 sibling lunar sites, so a band calibrated on it cannot discriminate. | DISCOVERY (negative) | `artifacts/lunar_adequacy/lunar_adequacy.json`; `scripts/lunar_adequacy.py`; `terratrace/verdicts.py::band_discrimination` (a band admitting more than half the known-different controls is demoted to NOT_ESTABLISHED). | **NOT ESTABLISHED, at all 18 cells.** Reported at the same prominence as the passes, on the site, in the deck and in the offline evidence page. **Where both descriptor bands exist — 6 of the 18 cells, the six at 500 m — each admits 4 or 5 of the five sibling sites. The other 12 cells have no relief band at all** (the held-out sub-windows do not supply one at 750 m or 1000 m), so the verdict there rests on the slope band alone, which admits 4 or 5 as well. *(Corrected 2026-11-15: the entry previously attached the "admits 4 of 5" reading to the panel as a whole, which generalised a six-cell measurement to eighteen; the verdict is unchanged and rests on a weaker test at the twelve.)* | The demotion rule is ours and is published; a different threshold would move cells, not make the band informative. The band census is a property of the supports we chose, not of the Moon. |
| 29 | At **18 of 24** site × descriptor statistics, the unit nearest a lunar reference is **another lunar site**, not any of the seven Earth candidates. | DISCOVERY (negative) | `artifacts/lunar_adequacy/lunar_adequacy.json` → `summary.nearest_unit_is_a_sibling_lunar_site`; the same count is in the atlas headline. | **Measured, and uncomfortable.** "Nevada is the closest *Earth* candidate" is true; "Nevada is closest to the Moon" is **false**. The panel's own caveat — six nearby sites may resemble each other rather than the method being sensitive — is now a number rather than a suspicion. | Six sites in one polar neighbourhood cannot separate "sibling similarity" from "insensitive method". Only independent lunar regions could, and the data path for them is blocked (claim 23). |
| 30 | The scale-resolved discovery atlas merges five records into one output, runs **10 cross-artifact reconciliations**, and **refuses to publish** if any two disagree. | IMPL | `scripts/run_discovery_atlas.py`; `artifacts/discovery_atlas/discovery_atlas.json`; `tests/test_discovery_atlas.py` — a corruption matrix that mutates the record behind each reconciliation in turn and asserts *that* check fires. | **Implemented; every reconciliation proven able to fail.** 54 windows, two regimes declared disjoint and pooled nowhere (`cross_regime_comparable: false`). | Passing reconciliations show internal consistency, not external truth. A systematic error present in all five records would reconcile perfectly. |
| 31 | The projection and grid arithmetic are validated on **all five bodies** (Earth, Mars, Moon, Mercury, Ceres) against independent closed-form geodesy. | VALIDATION | `tests/test_five_body_geometry.py`; AZIMUTHAL-EQUIDISTANT's defining property checked against Vincenty (WGS84, for Earth) and great-circle (spherical, for the other four), written out in the test rather than imported. | **Validated analytically, and labelled as such.** Worst case 1.4e-7 m at 9 km on Earth; angular tolerance 3e-8 rad. | **This is NOT a five-body terrain comparison.** Only Earth and the Moon have real data here; Mars, Mercury and Ceres are projection-validated only, and the two lists are declared in the test and asserted to partition the five bodies rather than merge. |
| 32 | The submitted demo is within the event's stated limit and the SI-tool disclosure is written. | IMPL | `TerraTrace-submission.pptx` — counted out of the ZIP archive as **exactly 7 slide parts**, asserted in `tests/test_event_alignment.py`; `docs/event/SI-DISCLOSURE.md`. | **7 slides, limit 7 (title and intro included).** The disclosure uses the 2026 event's own term, "Super Intelligence (SI)". | The 2½-minute recording script in `docs/DEMO.md` is **not** submittable as the demo. The challenge title quoted in the deck is **CONFIRMED from the submission portal, 2026-11-15** (`docs/EVENT-ALIGNMENT.md` §6); it had been UNVERIFIED, and the confirmation matched the string already in the artefacts. |

**Honest summary of iteration 7.** Four things this iteration found that reduce what may be claimed:
the lunar panel is one-dimensional, its absolute question is answered at no cell, its nearest unit is
usually another lunar site, and the challenge title was unverified at the time of writing (it was confirmed from the portal on 2026-11-15). What it added that is solid: a
projection validated on all five bodies and honestly labelled, a perturbation-robustness verdict with
its exceptions named, and an atlas that refuses to publish when its own records disagree. **No claim
here is that any Earth terrain is a mission-relevant Mars or lunar analog.**

## Iteration 8 — the independent-axis probe (attacking the one-dimensional limitation directly)

The lunar half's one load-bearing limitation is that its three declared axes span a single dimension.
This iteration attacked it in the only way that can produce an honest answer: find out what the axes
cannot see, look for a bank descriptor that carries information they do not, and then test whether a
better axis would change the decision at all. Protocol frozen before the run at
`config/lunar_axis_probe_v1.yml`; record at `artifacts/lunar_axis_probe/lunar_axis_probe.json`;
write-up at `docs/AXIS-PROBE.md`. **EXPLORATORY** — the same 18 cells were examined in v2, so nothing
here is confirmatory.

| # | Claim | Type | Evidence | Status | Limits / falsifier |
|---|---|---|---|---|---|
| 33 | The three declared axes are **exactly blind to a quarter-turn rotation** of a planar surface, and not blind to a 45° rotation. | DERIVATION | `terratrace/axis_probe.py::invariance_report`; measured at machine precision over eight azimuths in the artifact's `invariance` block: max \|Δ\| under θ→θ+90° is 1.1e-13 m on relief, while θ→θ+45° moves relief by **124.3 m** through the bounded ρ factor. | **Proved analytically AND measured.** Mean slope and elevation σ cannot depend on azimuth at fixed gradient magnitude; mean relief depends on it only through ρ(θ) = \|cos θ\| + \|sin θ\|, invariant under a quarter turn and under reflection about the diagonal. | Holds on planars. Real terrain has no free azimuth, so this bounds what *can* be non-redundant by symmetry rather than identifying the best axis — and the two do not coincide: the descriptor the measurement finds most independent (`variogram/nugget`) is itself quarter-turn **invariant**, so the symmetry argument cannot see it. |
| 34 | A genuinely non-redundant descriptor exists in the engine's own bank: **`variogram/nugget`** is predicted by the three declared axes no better than chance. | DISCOVERY | Per cell, adjusted R² of the descriptor on the three axes over the cell's 8 units. Nugget: **median adjusted R² −0.511**, median raw R² 0.136 against a **chance-level raw R² of 0.4286** at n=8, p=3. Controls: the two bank scalars that *are* the declared axes score adjusted R² = 1.000000. | **Measured, with both controls passing.** 184 bank scalars → 142 admissible → 141 decision-tested (one excluded as a circular quantity). | Adjusted, not raw — a raw threshold of 0.5 would sit barely above the chance level, and the first version of the probe ranked a **constant** descriptor (`spectral/peak_wavelength_m`, spread 0.0000) first. That failure is recorded in the protocol as `pilot_disclosed` rather than hidden. |
| 35 | The lunar panel's **sole-non-dominated** property is fragile to the **number of axes**, not to any particular axis — and no candidate axis is distinguishable from an arbitrary coordinate in its effect. | DISCOVERY (negative) | `artifacts/discovery_atlas/discovery_atlas.json` → `axis_sensitivity`; 6th raw record reconciled into the atlas by checks `axis:probe_reproduces_panel`, `axis:no_pareto_removals`, `axis:control_is_present`. | **Established, and it bounds the headline.** Across 141 candidate axes the frontier changed at 0–18 of 18 cells; a **uniformly random** fourth coordinate changes it at **15.90 of 18 on average over 300 draws**; **0 of 141** candidate axes exceed that control's 95th percentile; and the most non-redundant axis of all changes the decision at **0** cells. | This does **not** show the declared axes are wrong, and it does **not** promote any Earth candidate: adding a coordinate can only promote co-winners, never remove one (asserted, and the driver refuses to publish on a removal). It measures how provisional the ranking is; the ranking itself stands as published. |
| 36 | The panel's axis normalisation — `\|value − reference\| / \|reference\|` — is **undefined when the reference value is 0**, or when an input is non-finite, for any compositional descriptor. *(Corrected 2026-11-15: this row read "latent" — the case is now refused, see the status column.)* | **FIXED** (was IMPL defect) | `terratrace/axis_probe.py::engine_fractional_distance`; the artifact's `nan_audit` records **13 of 184** bank scalars hitting an undefined normalisation — **12** a class fraction that can be zero for a reference window (`geomorphons/composition/flat` and `/pit` are 0 in all 18 cells). | **Fixed, and the reason it mattered was worse than "a NaN appears":** `decision.non_dominated` excludes any unit carrying a non-finite distance, so a zero-reference axis did not raise, it silently compared fewer units and returned a ranking over them. The policy is now `decision.axial_fractional_distance` — an exact both-zero agreement is 0.0, a zero reference against a non-zero value refuses with `UndefinedNormalisation`, and so does any non-finite input. All three declared axes are strictly positive, so no published panel result is affected, and the stress driver's baseline-reproduction check is what holds that. *(Corrected 2026-11-15: the 13th entry is the non-finite cause, which the first audit could not see because a NaN candidate made the distance a NaN rather than the `None` it tested for.)* | Any axis set containing a descriptor that can be zero for the reference, or a non-finite input anywhere. Answered by refusing (above) rather than by an epsilon; the probe still uses a within-cell range for its own added axis. |

**Honest summary of iteration 8.** The probe did not rescue the lunar half, and it did not need to:
it replaced "the panel is one-dimensional" with something sharper and more useful — **the
sole-winner property is an artefact of running a Pareto rule over eight units in three dimensions**,
demonstrated against a control that an arbitrary coordinate does the same. That is a bound on the
claim, published next to the claim, on the site and in the atlas. The one genuinely additive result is
that independence and decision-relevance come apart: the most statistically non-redundant axis in the
engine's own bank moves nothing. **No claim here is that any Earth terrain is a mission-relevant Mars
or lunar analog.**
