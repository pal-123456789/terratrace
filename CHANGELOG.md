# Changelog

Complete build history of TerraTrace, generated from the git commit messages
(newest first). Each entry is the exact message recorded with that commit.

## Unreleased — v3 preparation: class-aware expectations, resolution-change classification, and 800-test gate

*Prepared 2026-10-16 by Pal Ghevariya (v3 proposal remains unfrozen)*

Added the v3-preparation layer without changing the v2 runner or the default decision engine:
`matched_benchmark` now exposes the existing Pareto layers and dominance matrix; `confirmation`
can evaluate candidate classes and named S/V expectations; `panel_v3` distinguishes resolution
stabilisation from reversal and evaluates the proposed smoothness-vs-volcanic hypotheses. The v2
reference-panel result remains exactly as recorded. The complete offline suite is now **800 passed,
0 failed**; validation remains 51/51; the gated default study hash is unchanged. Protocol v3 is
still a proposal, not a frozen experiment.

## Unreleased — Matched-footprint benchmark, honest-regime gate, and a frozen v2 reference-panel protocol

*Prepared 2026-10-16 by Pal Ghevariya (research branches `research/matched-footprint-benchmark`, merged as PR #1, and `research/m3-honest-regime`)*

Turns the analog result into a falsifiable experiment instead of a single verdict. Everything is
additive and gated: no engine module changed, and the default study hash (8f4890…) is unchanged.

- **Matched-footprint harness** (`matched_benchmark.py`): separates spatial *extent* from spatial
  *support*, records per-unit provenance, adds slope/relief baselines, lens ablation, and a
  selection-aware (Bonferroni) correction. A synthetic ground truth shows a mismatched footprint
  can flip the recommended analog, and the matched comparison recovers the correct one.
- **Real runner** (`matched_real.py`, `run_matched_benchmark.py --config`): windowed per-body
  reprojected crops of real DEMs. A first real run exposed a candidate-pool contamination bug (a
  held-out Mars window competed as a candidate); fixed with a test.
- **Adversarial robustness** (`adversarial.py`) and **absolute adequacy** (`adequacy.py`): how far
  a recommendation survives bounded perturbations, and whether "best among these" is actually
  within the reference's own morphological variability.
- **Honest-regime gate** (`comparability.py`): inspecting the real v1 bundle showed every cell was
  footprint-mismatched (Earth tiles truncated, ratio 1.63), and the 500/1000 m cells were below MOLA's
  effective resolution. The v1 Craters-of-the-Moon result is therefore recorded as exploratory.
- **Resolution-matching control** (`resolution.py`) and **confirmation/specificity panel**
  (`confirmation.py`), integrated as a v2 reference-panel runner.
- **Protocol v2 frozen before any v2 result** (`docs/BENCHMARK-PROTOCOL-v2.md`,
  `config/matched_footprint_v2.yml`): 7 Mars references (held-out volcanic plains + contrast
  terrains), H1–H4 decision rules, a stopping rule, and stated limitations.
- Claim-to-evidence ledger (`docs/CLAIM-LEDGER.md`). Suite: 686 -> 771 offline tests, all passing.
  Validation oracles unchanged at 51.

## Unreleased — Six cited descriptors, a sixth `hydro` decision lens, a transect profiler, and bank/transect interfaces

*Prepared 2026-10-12 by Pal Ghevariya (pending commit — hash assigned at commit time; builds on the pending descriptor batches)*

Six pure-geometry map-scale morphology descriptors join the descriptor bank, a sixth opt-in
decision lens is added, and a swath/profile extractor plus new CLI / API / fingerprint surfaces
are exposed. Everything is append-only and decision-gated (off by default), so the default study
package and its canonical synthetic hash (8f4890…) are byte-unchanged.

- **Six new cited descriptors** (all map-scale morphology, all off by default): a geostatistical
  semivariogram (range / sill / nugget; Matheron 1963); an RMS / Allan-deviation roughness length
  (Shepard et al. 2001); Wood (1996) morphometric curvature feature classes; a Woodcock (1977)
  surface-normal orientation-tensor fabric; an openness-difference slope position (Yokoyama 2002);
  and the Melton (1965) ruggedness number and relief ratios.
- **Sixth opt-in decision lens `hydro`** (`decision_metrics="hydro"`): the four core axes plus a
  Topographic Wetness Index, an aspect convergence index, and a flow-dissection
  distance-to-reference axis — a flow-geometric robustness lens, not a hydrological claim. The
  analog-atlas and one-command ablation defaults are unchanged (the five default lenses); hydro is
  opt-in via `decision_metrics`.
- **`transect` swath/profile extractor:** a utility that samples an elevation profile / swath
  across a DEM.
- **New interfaces:** unified CLI `bank` and `transect` subcommands; stdlib HTTP API `POST /bank`
  and `POST /transect` (loopback-only, with the same Host-allowlist and body-cap guards as the
  existing endpoints); and an opt-in `include_geostat` term for the terrain fingerprint.

Validation: +7 scientific-correctness oracles (44 -> 51). References: +4 method citations (23 -> 27)
— Matheron (1963), Wood (1996) / Dikau (1989), Woodcock (1977), Melton (1965) / Pike & Wilson
(1971). Suite: 613 -> 686 offline fixture tests.

Claim firewall unchanged: purely geometric map-scale morphology — NOT a hydrological, traversability,
geologic-equivalence, site-access, or mission-readiness claim; not NASA-endorsed.

686 fixture tests, all passing, no network required.

---

## Unreleased — Four cited geomorphometry descriptors: Topographic Wetness Index, Convergence Index, Sky-View Factor, two-scale TPI

*Prepared 2026-10-11 by Pal Ghevariya (pending commit — hash assigned at commit time; builds on the pending descriptor batches)*

Four pure-geometry map-scale morphology descriptors added to the descriptor bank. All four are
append-only and decision-gated (off by default), so the default study package is untouched and the
canonical synthetic study hash is UNCHANGED.

- **Topographic Wetness Index** (Beven & Kirkby 1979): a geometric wetness-propensity index built
  from contributing-area and local slope — a flow-geometric composite, not a hydrological claim.
- **Convergence Index** (Köthe & Lehmeier 1996; see also Kiss 2004): aspect-field convergence /
  divergence of the local terrain.
- **Sky-View Factor** (Zakšek et al. 2011): the hemispherical visible-sky fraction — a purely
  geometric openness measure, not an illumination or insolation claim.
- **Two-scale TPI slope position** (Weiss 2001): nested landform position from two TPI
  neighbourhoods, extending the existing single-scale TPI (reuses the Weiss 2001 citation).

Validation: +4 scientific-correctness oracles (40 -> 44). Suite: 593 -> 613 offline fixture tests.

Claim firewall unchanged: purely geometric map-scale morphology — NOT a hydrological, illumination,
traversability, geologic-equivalence, or mission-readiness claim; not NASA-endorsed.

613 fixture tests, all passing, no network required.

---

## Unreleased — One-command real multi-body analog study: run_real_analog_study.py orchestrator

*Prepared 2026-10-11 by Pal Ghevariya (pending commit — hash assigned at commit time; builds on the pending scale & fabric push)*

A single flagship entry point that runs the entire real multi-body analog study end to end. It
only orchestrates existing, already-tested modules, so it adds no new claim and the canonical
synthetic study hash is UNCHANGED.

scripts/run_real_analog_study.py (new): one command takes a config and runs the whole pipeline —
config -> preflight (schema + every AOI bbox, no network) -> fetch the covering DEM per unit
(or --synthetic to run on built-in synthetic terrains, or --dry-run to stop after preflight) ->
a full-depth study (significance, spatial block bootstrap, landform lens, terrain_spectra, and
hillshade previews all on) -> decision confidence -> a complete, self-consistent bundle:
study.json, report.md, report.html, a self-contained offline viewer, REFERENCES, a sha256
CHECKSUMS manifest, and confidence.json. The offline --synthetic / --dry-run modes make the whole
orchestrator exercisable with no network and no API key.

config/real_multibody.example.yml (new): a curated, ready-to-run config — a Mars reference AOI
plus Earth analog candidate AOIs, with the depth flags (significance / bootstrap / landform /
terrain_spectra / previews) switched on — so the one command produces a full-depth bundle out of
the box.

REAL-DATA-RUNBOOK.md: rewritten around the one-command path (the manual fetch -> profile ->
run_real_study sequence is retained for stepwise runs).

Tests: +2 offline fixtures covering the orchestrator (its --synthetic / --dry-run paths run with
no network), so the suite is now 472; the default study path and its gated package_hash are
untouched.

Claim firewall unchanged: this is orchestration over the existing map-scale morphology engine —
NOT a traversability, hazard, geologic-equivalence, or mission-readiness claim; not NASA-endorsed.

472 fixture tests, all passing, no network required.

---

## Unreleased — Scale & fabric: radially-averaged power spectrum + directional terrain anisotropy

*Prepared 2026-10-11 by Pal Ghevariya (pending commit — hash assigned at commit time; builds on the pending significance/confidence push)*

Two pure-NumPy map-scale morphology descriptors + an opt-in integration; the canonical synthetic
study hash is UNCHANGED (every new path is off by default and gated).

spectral.py (new): radially-averaged 2-D power spectral density (PSD). Detrends the plane,
Hann-windows, FFTs, and radially averages the periodogram over wavenumber, reporting the log-log
spectral slope (how power is shared between long and short wavelengths), band roughness (RMS
amplitude in long/mid/short wavelength bands), the peak wavelength, and a total power that recovers
the detrended variance by Parseval. A map-scale roughness-spectrum descriptor (after Perron,
Kirchner & Dietrich 2008).

anisotropy.py (new): directional terrain fabric via the directional structure function (RMS
elevation difference along a fan of azimuths). Reports anisotropy strength (0 = isotropic, -> 1 =
strongly lineated), the fabric orientation (azimuth of minimum roughness = the strike along which
ridges/dunes/grain run), and an isotropy ratio. Relief-invariant and NaN-safe (after Shepard et
al. 2001).

Integration (all OPT-IN): study.compare_units(..., terrain_spectra=True) (and
run_real_study(terrain_spectra=True)) attach package["spectral"] and package["anisotropy"] per
compared/eligible unit; the HTML report (report_html.py) and offline viewer (build_viewer.py)
render a "Scale & fabric" section when those blocks are present; and descriptors.descriptor_bank
and the terrain fingerprint gained opt-in spectral/anisotropy terms. With no spectral/anisotropy
block the report/viewer render byte-identically to before.

validation.py: +5 scientific-correctness oracles (spectral_sinusoid_peak,
spectral_white_noise_flat, spectral_parseval, anisotropy_ridges_oriented, anisotropy_isotropic_low)
— the scientific-correctness suite is now 28 checks, all passing.

references.py: added the Perron, Kirchner & Dietrich (2008) power-spectrum and Shepard et al.
(2001) natural-terrain-roughness method citations (method_references() now returns 6). README /
docs/index.md / docs/method.md / docs/VALIDATION.md updated.

Claim firewall unchanged: map-scale roughness-spectrum and directional-structure descriptors of
the sampled DEM only — NOT a traversability, hazard, geologic, or mission-readiness claim; they
say nothing about rock-scale obstacles below the pixel; not NASA-endorsed.

470 fixture tests, all passing, no network required.

---

## Unreleased — Statistical confidence for the analog decision: permutation significance + non-composite confidence

*Prepared 2026-10-11 by Pal Ghevariya (pending commit — hash assigned at commit time; builds on the CI-fix 7969d18)*

Opt-in statistical confidence for the analog recommendation; every new path is OFF by default and
gated, so the canonical synthetic study hash is UNCHANGED.

study.py: compare_units (and run_study / run_real_study, which forward it) gain significance=True
+ n_perm (default 1000). When requested they attach a package["significance"] block — a one-sided
permutation test (significance.permutation_closer_test) of whether the recommended unit is
genuinely closer to the reference than the RUNNER-UP (the second-closest candidate), computed per
sample-based morphology metric (slope, relief, ruggedness) with the decision's own scales, with
per-metric one/two-sided p-values, an effect size, and a recommendation_significant flag.
Connectivity is a scalar and reported as a signed closeness difference. OFF by default, so the
frozen run_study() package and its provenance hash are byte-unchanged.

confidence.py (new): decision_confidence(package, sensitivity_report=None) restates the robustness
evidence a study already holds as THREE independent signals — bootstrap non-domination frequency,
permutation significance vs the runner-up, and lens/support stability — and returns a single
NON-COMPOSITE categorical verdict (robust / qualified / fragile / tie / indeterminate / blocked /
not_comparable / unverified) with a plain-language rationale and an explicit list of the signals
NOT evaluated. There is no weighted score; a missing signal degrades to "not evaluated" rather
than being invented.

Surfacing: the HTML report (report_html.py) and offline viewer (build_viewer.py) render a
"Decision confidence" section (verdict + the three signals + rationale + caveats) and a
"Significance vs runner-up" table, shown only when a robustness signal was actually computed (so
the default report/viewer are byte-unchanged). cli.py: study --significance / --n-perm + a new
confidence subcommand. api.py: new POST /confidence and a significance option on the /compare
study-runner route (n_perm capped at 2000).

validation.py: +4 scientific-correctness oracles (significance_clear_winner,
significance_near_tie_is_honest, confidence_robust_on_clear_winner,
confidence_fragile_or_tie_on_near_tie) — the scientific-correctness suite is now 23 checks, all
passing.

references.py: added the Efron & Tibshirani (1993) bootstrap and Good (2005) permutation-test
method citations. README / docs/index.md / docs/method.md / docs/VALIDATION.md updated.

Claim firewall unchanged: distribution-shape resampling statistics and map-scale morphology
screening only — NOT a traversability, hazard, geologic-equivalence, or mission-readiness claim;
not NASA-endorsed. "Decision confidence" = robustness of the recommendation to resampling, to a
permutation test vs the runner-up, and to changing the decision lens/support — nothing more.

428 fixture tests, all passing, no network required.

---

## Unreleased — Landform / line-of-sight terrain structure: topographic openness + geomorphons

*Prepared 2026-10-11 by Pal Ghevariya (pending commit — hash assigned at commit time)*

Two pure-NumPy line-of-sight modules + an opt-in integration; the canonical synthetic study
hash is UNCHANGED (every new path is off by default and gated).

openness.py: topographic openness (Yokoyama, Shirasawa & Pike 2002) — positive and negative
openness from the zenith/nadir sight-line angles averaged over eight azimuths. Exactly 90 deg
on a flat surface; positive openness is high on peaks/ridges (can exceed 90 deg), negative
openness high in pits/valleys. A map-scale morphology / visualisation descriptor only.

geomorphons.py: geomorphon landform classification (Jasiewicz & Stepinski 2013) — a per-cell
ternary line-of-sight signature (n_plus, n_minus) reduced to the 10 common landforms (flat,
peak, ridge, shoulder, spur, slope, hollow, footslope, valley, pit), plus a normalised 9x9
geomorphon spectrum. Relief- and orientation-invariant. The ternary signature is computed
exactly as the method prescribes; the 10-form reduction is an explicit, antisymmetric rule
validated against canonical synthetic landforms, NOT a verbatim copy of any particular GIS
lookup table.

Integration (all OPT-IN): a fourth decision lens decision_metrics="landform" (the four core
axes + a geomorphon-spectrum total-variation distance + a topographic-openness distance);
opt-in landform terms in descriptors.descriptor_bank and the terrain fingerprint; and, when a
study is run with landform=True + previews=True, a landform-composition table, positive /
negative openness medians, a categorical landform map PNG and a grayscale openness PNG in the
HTML report (report_html.py) and the offline viewer (build_viewer.py). With no landform block
the report/viewer render byte-identically to before.

validation.py: +8 canonical oracles (openness_flat / openness_peak / openness_pit_mirror /
geomorphon_flat / geomorphon_cone_peak / geomorphon_bowl_pit / geomorphon_tilt_slope /
geomorphon_relief_invariance) — the scientific-correctness suite is now 19 checks, all passing.

references.py: added the Yokoyama 2002 and Jasiewicz & Stepinski 2013 method citations.
README / docs/index.md / docs/method.md / docs/VALIDATION.md updated.

Claim firewall unchanged: map-scale morphology only — NOT traversability, hazard,
geologic-unit identification, or mission readiness; not NASA-endorsed.

379 fixture tests, all passing, no network required.

---

## bd5c6b8 — Harden: real-path regression test + GitHub Actions CI + accurate landing README

*Committed 2026-10-10 by Pal Ghevariya*

- tests/test_real_study_path.py: exercises run_real_study end-to-end WITHOUT rasterio
  (monkeypatches the raster load) -- proves the real entry point's wiring: reference
  detection, per-unit vertical-accuracy resolution (explicit + catalog-by-demtype),
  opt-in feature_uncertainty + hillshade previews, and the geomorphic lens. Guards the
  real-data path (otherwise untested in CI) against regressions. 330 tests, all green.
- .github/workflows/ci.yml: runs the dependency-free suite + the scientific-correctness
  validation on Python 3.10/3.11/3.12 on every push/PR (CI badge added).
- README.md (root landing page): refreshed to the true scope -- five bodies, 13-source
  catalog, 330 tests, the full capability set -- it was badly stale (46 tests, Mars-only).

---

## a96b3b7 — Day 10 — v0.2 push 5: curated analog-site library, one-command bundle, API+CLI expansion

*Committed 2026-10-10 by Pal Ghevariya*

Four parallel subagents; 327 fixture tests all passing; synthetic study hash UNCHANGED.

regions.py (+config/regions.example.yml): a curated library of 11 well-known planetary
reference sites (Jezero, Gale, Valles Marineris, Mare Tranquillitatis, Aristarchus,
Caloris) and terrestrial analog sites (Hawaii, Iceland, Atacama, Devon Island, Craters of
the Moon), as ready-to-use AOI presets (approximate bboxes; illustrative, not endorsed).

bundle.py (+scripts/export_bundle.py): one command exports a complete deliverable set --
study.json, report.md, report.html, REFERENCES.md, viewer.html, and a sha256 CHECKSUMS
manifest -- all self-consistent and verified (sha256sum -c passes).

api.py: new GET /references, POST /sensitivity, POST /classify (loopback-only + body cap +
Host allowlist preserved). cli.py: new references, sensitivity, classify subcommands.

README/docs test counts updated. 327 fixture tests, all passing, no network required.

---

## 92b49fc — Day 9 — v0.2 push 4: integrated uncertainty + previews, sensitivity ablation, terrain classifier, credits, API/CLI

*Committed 2026-10-10 by Pal Ghevariya*

Five parallel subagents + core integration; 307 fixture tests all passing; the canonical
synthetic study hash is UNCHANGED (opt-in features are off by default).

Integrated measurement uncertainty + previews (study.py + report_html.py + build_viewer.py):
compare_units / run_real_study gain opt-in vertical_accuracy (scalar or per-unit; real runs
auto-resolve it from each source's catalog vertical accuracy) and previews=True. When
supplied, the package carries feature_uncertainty (propagated slope/relief/ruggedness 1-sigma
via errorprop) and previews (one self-contained hillshade PNG data-URI per unit via
hillshade), and the HTML report + offline viewer render a "Measurement uncertainty" table and
inline terrain previews. OFF by default -> synthetic package/hash byte-unchanged (regression
test added).

sensitivity.py: lens_ablation / support_ablation / ablation_report — reports whether the
recommendation is STABLE across the three decision lenses and across common-support scales.

terrain_classify.py: a transparent, rule-based morphological type label (flat_plain / rolling
/ dissected_upland / rough_rugged) with evidence + confidence margin. Descriptive map-scale
label only, not a geological/genetic/mission classification.

references.py (+ scripts/make_references.py): a complete "Data sources & credits" bundle
(citation + licence per source, grouped by body) so every study is properly attributed.

api.py: new POST /dossier (per-unit decision brief) and POST /report.html (HTML report);
loopback-only + body cap + Host allowlist preserved. cli.py: new dossier + report-html
subcommands.

README / docs/method.md / docs/VALIDATION.md / docs/index.md updated.

307 fixture tests, all passing, no network required.

---

## 4251941 — Day 8 — v0.2 push 3: elevation-error propagation, hillshade previews, cross-body fingerprint search, site dossiers

*Committed 2026-10-10 by Pal Ghevariya*

Four parallel subagents + core work; 275 fixture tests all passing; the canonical synthetic
study hash is UNCHANGED.

Error propagation (catalog.py + errorprop.py): every catalog source now carries an
approximate 1-sigma vertical accuracy (vertical_accuracy_m) + a vertical_accuracy_for()
accessor; errorprop propagates it analytically into slope / relief / ruggedness uncertainty
(central-difference model: sigma_g = sigma_z/(dx*sqrt(2)); slope-angle sigma =
sigma_g/(1+tan(slope)^2); relief sigma = sqrt(2)*sigma_z). Honest caveat: assumes independent
per-pixel errors, so it is an optimistic lower bound (parallel to the bootstrap caveat).

hillshade.py: a Horn shaded-relief image encoded as a base64 PNG data URI using ONLY the
stdlib (zlib/struct/base64 — no PIL), so a terrain preview can be embedded inline in a fully
self-contained HTML page. (Validity checked without PIL: the IDAT decompresses to
height*(width+1) bytes.)

fingerprint_library.py (+ scripts/fingerprint_search.py): build a library of reference-terrain
fingerprints and rank candidates against them, including the cross-body case (rank Earth
candidates against each planetary reference). A morphological similarity ranking, not a
classification/identity claim.

dossier.py: a focused per-candidate decision brief (its per-metric distances, Pareto layer,
eligibility verdict, bootstrap frequencies + CIs when present, whether it is the
recommendation, and the transfer-gap ledger + prohibited claims) as a structured dict and as
Markdown.

README / docs/method.md / docs/VALIDATION.md / docs/index.md updated.

275 fixture tests, all passing, no network required.

---

## b27864c — Day 7 — v0.2 push 2: five bodies (Mercury + Ceres), HTML report, DEM co-registration, terrain fingerprint, API + viewer

*Committed 2026-10-10 by Pal Ghevariya*

Five parallel subagents + core work, each verified against the code and the suite; 247
fixture tests all passing; the canonical synthetic study hash is UNCHANGED.

Five reference bodies: added Mercury (MESSENGER sphere R=2,439,400 m) and Ceres (Dawn
sphere R=469,730 m) across reproject.py / catalog.py / preflight.py (registry is now 13
sources, keyless for the planetary bodies). Earth/Mars/Moon CRS strings and the gated study
hash are byte-unchanged. Strongly irregular bodies (e.g. Vesta) are deliberately excluded —
a single authalic sphere would misrepresent them.

report_html.py (+ scripts/make_html_report.py): a polished, fully SELF-CONTAINED, offline
HTML report (inline CSS, no external/CDN assets, every dynamic string escaped) rendered from
a study or batch package.

coregister.py: translation-only DEM co-registration — recovers a known pixel shift via an
overlap-RMSE search with sub-pixel parabola refinement (RMSE -> ~0 in tests) and estimates
the vertical-datum offset, so two DEMs can be aligned before differencing/comparison. No
rotation/scale/warp.

fingerprint.py: a compact 11-field normalized terrain signature, a bounded similarity
metric, and rank_library() for morphological analog similarity search (a signature + ranking,
NOT a classification/identity claim).

api.py: new GET /bodies, POST /validate, POST /batch, POST /report endpoints (loopback-only,
body cap, and Host allowlist all preserved; the n_boot cap is now 500 so an HTTP request
stays responsive — the library still accepts any n_boot offline).

build_viewer.py: the self-contained offline viewer now shows a target-body badge, a decision
matrix, a Pareto-frontier panel, and an uncertainty panel.

README / docs/method.md / docs/VALIDATION.md / docs/index.md updated for the expansion.

247 fixture tests, all passing, no network required.

---

## ad1fd6a — Day 6 — v0.2 leap: multi-body (Moon), reporting, significance, autocorrelation, repro, unified CLI, geomorphometry

*Committed 2026-10-10 by Pal Ghevariya*

A large, parallel-built expansion (six subagents + core work, each verified against the
code and the full suite; 220 fixture tests green; the canonical synthetic study hash is
UNCHANGED, so all prior provenance still holds).

Multi-body (Mars + Moon + Earth): reproject.py adds the lunar sphere (R=1,737,400 m) and
body_radius_m(); catalog.py adds the keyless LRO/LOLA `moon_lola_ldem` source (registry is
now 11 sources); preflight.py accepts body "moon" (radius-correct area + lon convention).
Mars/Earth CRS strings and the gated study hash are byte-unchanged.

report.py (+ scripts/make_report.py, CLI `report`): publication-grade Markdown from a study
or batch package — plain-language verdict, decision table for the chosen lens, eligibility,
an uncertainty section when bootstrapped, sensitivity, the transfer-gap ledger, and a
provenance appendix carrying the package hash.

significance.py: a permutation test ("is candidate A significantly closer to the reference
than B?") returning a p-value + effect size, plus a bootstrap distance CI — closeness gaps
are now tested, not merely asserted.

autocorr.py: spatial autocorrelation curve + 1/e correlation length + suggest_block_size, so
the spatial block bootstrap's block size is chosen from the data instead of guessed.

repro.py (+ scripts/verify_study.py): recompute and verify a package's content hash, diff two
packages, and confirm the synthetic study reproduces bit-for-bit — reviewer-grade integrity.

features.py / descriptors.py: surface_area_ratio (rugosity), terrain_ruggedness_index (Riley
1999 TRI), tpi_map, landform_fraction — an analysis layer, deliberately NOT wired into the
default decision (gated hash preserved).

cli.py: a unified `python -m terratrace.cli` dispatcher — study (default, back-compatible),
validate, benchmark, report, version.

README / docs/method.md / docs/VALIDATION.md / docs/index.md updated for the expansion.

220 fixture tests, all passing, no network required.

---

## dfbb0ad — Day 5 — honest uncertainty: spatial moving-block bootstrap (autocorrelation-aware CIs)

*Committed 2026-10-10 by Pal Ghevariya*

uncertainty.py: add block_resample_2d (a 2-D moving-block bootstrap) and
block_bootstrap_pareto. DEM pixels are spatially autocorrelated, so the existing
independent-pixel bootstrap gives optimistically NARROW confidence intervals. The block
bootstrap resamples block x block patches, preserving within-block correlation, and yields
honest -- typically much wider -- CIs and non-domination frequencies. Verified on an
autocorrelated field: the block distance-CI total width was several times the independent
width (the independent method really was over-confident).

study.py: compare_units and run_real_study gain an opt-in bootstrap_method
("independent" default | "block") plus block_size (aggregated pixels), active only when
n_boot>0. The default path is byte-identical and the canonical synthetic study
package_hash is UNCHANGED (verified); the independent bootstrap_pareto is untouched.

Tests: block_resample_2d block-preservation/determinism/clamping, block closer-unit +
report shape, the wider-CI demonstration vs the independent bootstrap, and the
compare_units wiring. config/aois.example.yml, README, docs/method.md, docs/VALIDATION.md,
and REAL-DATA-RUNBOOK.md updated with the method and block_size guidance.

184 fixture tests, all passing, no network required.

---

## 7849e70 — Day 4 — cross-reference, multi-lens batch studies (comparative synthesis)

*Committed 2026-10-10 by Pal Ghevariya*

batch.py (new): run_batch runs a GRID of full comparisons — every (Mars reference region
x decision lens: core / extended / geomorphic) cell is a complete compare_units run — and
synthesises, per Earth candidate: layer1_frequency (how often it is Pareto non-dominated
across the whole grid), recommended_frequency, mean_layer, a consensus_shortlist
(candidates non-dominated in EVERY cell → robust to both the reference choice AND the
morphology lens), and a robust_ordering. It is a transparent robustness synthesis, NOT a
composite "Mars-likeness" score; the map-scale-morphology claim firewall is unchanged.
run_real_batch loads real DEMs through the shared loader.

study.py: extracted load_real_units from run_real_study (behavior-preserving refactor so
both the single study and the batch runner load/warp DEMs identically). Verified the
canonical synthetic study package_hash is UNCHANGED.

scripts/run_batch_study.py + config/batch.example.yml (two Mars reference windows × three
Earth candidates). README / docs/method.md / docs/VALIDATION.md updated.

180 fixture tests, all passing, no network required.

---

## 8ff5f9b — Day 3 (cont.) — opt-in geomorphic decision mode (curvature + VRM as Pareto axes)

*Committed 2026-10-10 by Pal Ghevariya*

decision_metrics="geomorphic": the core four axes plus Zevenbergen-Thorne mean curvature
and the Vector Ruggedness Measure as two extra Pareto distances — a third independent
robustness lens alongside core and extended. A recommendation that survives all three
proven axis sets is far more defensible than one that holds under a single set. The mode
also reports per-unit hurst_exponent + curvature/VRM medians in a geomorphic_metrics block.

Gated so the DEFAULT pipeline is untouched: all new computation and the geomorphic_metrics
key run only under decision_metrics=="geomorphic". Verified the canonical synthetic study
package_hash is UNCHANGED (now locked by a regression test), the core/extended packages
carry no geomorphic key, and the bootstrap non-domination frequency extends to the
geomorphic axes consistently with how extended mode already works.

config/aois.example.yml, docs/method.md, and README updated.

174 fixture tests, all passing, no network required.

---

## 67e8ab0 — Day 3 (cont.) — geomorphometric descriptor depth: curvature, VRM, multiscale roughness

*Committed 2026-10-10 by Pal Ghevariya*

features.py: add standard, citable descriptors, each proven on analytic cases:
  - Zevenbergen-Thorne (1987) profile/plan/mean curvature (3x3 local quadratic).
    Bit-exact: 0 on a plane; profile=-2a, plan=+2a, mean=-4a on z=a(x^2+y^2).
  - Vector Ruggedness Measure (Sappington et al., 2007): surface-normal dispersion in
    [0,1], 0 on any plane (even steep), rising with roughness, decoupled from mean slope.
  - Multiscale roughness: structure_function (RMS height difference vs lag) +
    hurst_exponent (log-log scaling slope; 1.0 on a linear ramp, ~0 on white noise).

descriptors.py (new): descriptor_bank(z) assembles the full geomorphometry of a tile
(distribution summaries for the map-valued features + scalars + the structure function)
as one JSON-serialisable dict, plus a bank_vector() convenience. A non-destructive
ANALYSIS layer for analysts and future decision modes.

validation.py: three new scientific-correctness checks (curvature_zero_on_plane,
vrm_discriminates_roughness, roughness_hurst_sane) — run_validation() is now 11/11.

These add NO axes to the DEFAULT decision pipeline: the synthetic study package_hash is
UNCHANGED (verified), so all prior provenance still holds. docs/method.md, VALIDATION.md,
and README updated with definitions, invariances, and citations.

170 fixture tests, all passing, no network required.

---

## dd0ea10 — Day 3 — validation & benchmarking: scientific-correctness suite + ~40x exact relief speedup

*Committed 2026-10-10 by Pal Ghevariya*

validation.py (new): drives the REAL compare pipeline on synthetic terrains with known
relationships and proves correctness — self-distance zero; slope/relief/ruggedness
invariant to a vertical offset and a 90-deg rotation; distance monotonic in roughness
(real discriminating power); a candidate closer on every axis provably dominates and is
the recommendation; a same-statistics twin beats a 5x-rougher impostor (null control);
a flat/water tile is BLOCKED by eligibility; the pipeline is deterministic.
run_validation() emits a hashed, host-independent regression report (8/8 pass).

benchmark.py (new): a pinned behavioural-invariant battery + hash-stability check + a
wall-clock scaling profile. run_benchmark() reports timings honestly (never pass/failed
on an absolute time).

Performance (features.relief): a benchmark-driven optimisation replaced a per-window
nanquantile with an exact min/max (alpha=0) or a single two-quantile call (alpha>0). A
96x96 study dropped from ~12 s to ~0.3 s (~40x) with BIT-IDENTICAL outputs — verified by
unchanged relief arrays and an unchanged study package_hash. The full test suite went
from ~100 s to ~40 s.

scripts/run_validation.py + run_benchmark.py: CI-friendly, exit!=0 on failure, --json.
README / docs/VALIDATION.md / docs/index.md updated.

156 fixture tests, all passing, no network required.

---

## c1f9449 — Day 2 (cont.) — complete data & sources: 10-source catalog, config-schema preflight, idempotent fetch cache

*Committed 2026-10-10 by Pal Ghevariya*

Catalog breadth (catalog.py): add 5 OpenTopography global DEMs — Copernicus GLO-90,
NASADEM, SRTM GL1/GL3, ALOS AW3D30 — each with accurate coverage (SRTM-family 60N-56S,
others global), licence, citation, vertical datum. Every source now carries a
land-morphology `preference` tier and known `nodata_sentinels`. recommend_source()
selects by preference then least-download-that-meets-support, and correctly declines a
source whose footprint misses the AOI (e.g. an SRTM product above 60N, or a US-only
product abroad). nodata_sentinels_for() accessor; validate() checks the new fields.
Registry is now 10 sources.

Config-schema preflight (preflight.py): validate_config() gates the whole config
(types, required keys, duplicate ids/paths, demtype-vs-dataset conflict, per-unit bbox)
and is wired into preflight_config, so a structural error fails fast with a clear
message before any download.

Idempotent fetch cache (fetchcache.py, new): needs_fetch() skips files already on disk
(optionally checksum-verified); record_entry / load / update / save maintain a sha256
provenance manifest. The sha256 is byte-identical to sourcelock's.

fetch_real_dems.py: skips cached files (--force to override), writes
data/fetch_manifest.json, dispatches any global demtype or 3DEP dataset, and applies
each source's known nodata sentinels before the post-fetch QA. README / runbook / docs
updated.

143 fixture tests, all passing, no network required.

---

## bde600e — Day 2 — data & sources: catalog, preflight, QA profiler, batch frontier, resilient ingest

*Committed 2026-10-10 by Pal Ghevariya*

Source catalog (catalog.py): STAC-like registry for MOLA / Copernicus GLO-30 /
USGS 3DEP with spatial-coverage metadata, source_covers(), and recommend_source()
for automatic AOI->product selection; validate() extended with type/domain checks.

Preflight (preflight.py): no-network AOI validation — bbox well-formedness, body
bounds, approximate area/pixel/download sizing vs heuristic ceilings, and coverage
check; preflight_config() reports per unit before any byte is downloaded.

DEM QA profiler (profile.py): valid/water/NaN fractions, robust relief, percentiles,
and advisory flags; water_fraction reuses masks.zero_fraction so WATER_CONTAMINATION
matches the engine's existing 0.6 contamination gate.

Pareto frontier (frontier.py): peeled non-dominated layers + dominance matrix for
multi-candidate batch ranking; wired into study.compare_units and inspect_study.

Ingest hardening (ingest.py): atomic downloads now retry transient 429/5xx with
bounded backoff honouring Retry-After; TIFF magic-byte guard rejects ArcGIS
error-JSON served as HTTP 200; window_from_bbox returns metres for a geographic CRS.

Scripts/docs: fetch_real_dems runs preflight + post-fetch QA and dispatches 3DEP
datasets; new profile_dem.py QA tool; README / runbook / docs updated.

116 fixture tests, all passing, no network required.

---

## 71eade8 — Refresh real study with hardened engine

*Committed 2026-10-10 by Pal Ghevariya*


---

## 8e9ad1a — Day-1 foundation hardening (audited): correctness, robustness, new descriptors

*Committed 2026-10-09 by Pal Ghevariya*

science correctness:
- reference-based fixed per-feature scales so Pareto axes are comparable across
  candidates (was: per-candidate IQR normalizer could flip dominance)
- per-unit REALIZED support (native*factor) used as dx, not the target
- gate the REFERENCE through eligibility (not just candidates)
- paired-reference bootstrap (one reference resample per iteration), scales applied,
  connectivity dropped from CI; docstring states the independent-pixel CI caveat
- non_dominated() excludes NaN vectors; pairwise flip matrix excludes the baseline
- aspect dispersion is gradient-magnitude weighted (flat -> 0, not noise)
- hypsometric integral uses robust p1/p99 (not single-pixel min/max)
- new descriptor: TPI dispersion (ridge/valley organisation), reported in extended
- small-AOI feature guards; reproject uses area-average + NaN nodata; antimeridian centroid

robustness/security:
- API: body-size cap (413), Content-Length validation, 500 on error (no leak),
  loopback Host allowlist (anti DNS-rebind), removed CORS wildcard,
  refuse non-loopback bind without --allow-remote
- CLI validates positive support/posting
- build_viewer escapes state/support/class and uses .get defaults

tests: 68 passing (was 54); added API, build_viewer, cli, feature and decision cases

---

## 2bb85b1 — Real study with bootstrap CIs

*Committed 2026-10-09 by Pal Ghevariya*


---

## 709b474 — Bootstrap respects decision axes + enable n_boot=300 by default

*Committed 2026-10-09 by Pal Ghevariya*

- uncertainty.bootstrap_pareto accepts extra_dims so non-domination frequency is
  computed in the SAME space as the decision (extended adds aspect/hypsometry)
- compare_units passes the extended dims when decision_metrics=extended
- config/aois.example.yml now sets n_boot: 300 so real runs produce CIs
- +1 test (54 total, all green)

---

## a7b596e — Viewer: show bootstrap-uncertainty panel when a study has it

*Committed 2026-10-09 by Pal Ghevariya*

- build_viewer renders a non-domination % + slope-distance 95% CI table when the
  study package includes bootstrap; omitted otherwise (verified both ways)
- regenerate viewer/index.html and site/study/index.html from the real study

---

## 9a9e80b — Add stdlib HTTP API (health/study/compare) + console script

*Committed 2026-10-09 by Pal Ghevariya*

- terratrace/api.py: dependency-free http.server API exposing /health, /study,
  POST /compare (validated/clamped params; bootstrap supported). Unauthenticated,
  binds 127.0.0.1 by default (documented) — add auth before exposing.
- 4 API tests via loopback (53 total, all green); terratrace-api console script;
  README usage.

---

## b7cf920 — Add bootstrap uncertainty: distance CIs + probabilistic Pareto

*Committed 2026-10-09 by Pal Ghevariya*

- terratrace/uncertainty.py: resample feature distributions to put 95% CIs on
  each morphology distance and turn the Pareto decision into a non-domination
  frequency + clear-winner frequency (honest 'B non-dominated in N% of resamples')
- wired through compare_units / run_study / run_real_study via n_boot (default 0,
  so existing deterministic outputs are unchanged); config gains n_boot
- inspect_study prints the bootstrap summary; 3 new tests (49 total, all green)

---

## bef6034 — Fix /study on Vercel: ship study viewer inside site/ (site/study/index.html)

*Committed 2026-10-09 by Pal Ghevariya*

- copy the self-contained study viewer to site/study/index.html so it deploys
  with the site regardless of Vercel root-directory setting
- site/vercel.json (cleanUrls) for when Root Directory = site
- root vercel.json /study now points to /site/study/index.html

---

## b716308 — Add MIT LICENSE at repo root so GitHub recognizes it

*Committed 2026-10-09 by Pal Ghevariya*


---

## 616a056 — Remove internal plan from public repo; keep it local-only

*Committed 2026-10-09 by Pal Ghevariya*

- untrack Planetary-Analog-OS-Plan/ and PLANETARY-ANALOG-OS-MASTER-PLAN.md
  (still on local disk, now git-ignored)
- README no longer references the plan library
- repo now contains only engine + site + data + docs

---

## 8e15f8a — Add committable Mars AOI sample + fix sample CRS

*Committed 2026-10-09 by Pal Ghevariya*


---

## ee8014a — Premium 3D scroll site + include Earth DEMs & data docs

*Committed 2026-10-09 by Pal Ghevariya*

- site/index.html: redesigned cinematic-observatory scroll experience
  (offset planet + orbital rings + Mars->Earth morph tied to scroll + terminator
  lighting + mouse parallax, fixed nav, bottom instrument console, animated
  comparison chart, scrims for legibility, loader)
- commit real Earth GLO-30 AOIs under terratrace/data/earth (small, redistributable)
- data READMEs + scripts/make_mars_sample.py to crop a committable Mars AOI
- .gitignore now excludes only the ~2 GB global MOLA (GitHub 100 MB limit),
  not the whole data/ tree
- engine depth since last commit: masks + water gate, extended decision mode,
  aspect/hypsometric features, source lock, docs site, viewer panels

---

## 59884ca — TerraTrace / Planetary Analog OS: engine, plan library, 3D scroll site

*Committed 2026-10-09 by Pal Ghevariya*

- terratrace engine: real MOLA + Copernicus ingest, per-body AEQD reprojection,
  morphology features (slope/relief/ruggedness/connectivity/aspect/hypsometry),
  Pareto decision with tie/blocked states, water-contamination gate, masks,
  evidence graph + provenance, source lock, 46 passing tests
- 23-module Planetary Analog OS plan library + diagrams
- site/: 3D scroll-animated website (Three.js + GSAP), honest claim-firewall copy
- vercel.json serves the site at / and the study viewer at /study
- large DEMs under terratrace/data/ are git-ignored

---
