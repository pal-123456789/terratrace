# TerraTrace — Planetary Analog Terrain-Transfer Workbench (v0.3)

**Planetary Analog OS** nucleus. TerraTrace compares a Mars reference terrain unit
with candidate Earth terrain units at a declared common spatial support, shows which
map-scale morphology transfers, states what cannot transfer, and emits a reproducible,
provenance-tracked study package.

> **Scope / claim firewall.** TerraTrace screens terrain **morphology** between curated
> map products. It does **not** estimate rover traversability, validate autonomy,
> establish geological equivalence, certify site access, or certify mission readiness.
> It is not NASA-endorsed.

## Status — the headline result

TerraTrace **caught its own false analog**, with rules fixed before the data were seen. An exploratory
real-data screen appeared to endorse **Craters of the Moon, Idaho** as a Mars analog; a matched-footprint
benchmark **withdrew** that claim (the engine abstains in the honest regime, and Craters is nearest for a
cratered highland as readily as for volcanic plains); and protocol v3 then **measured** the explanation —
the nearest Earth analog tracks **km-scale roughness, not volcanic origin** (S **supported**, V **not
supported**, R **supported**; 15/15 confirmatory honest cells, 0 comparability-gate violations). One
caveat is recorded with the result rather than hidden: v3 is *pre-specified but not fully pre-registered*, and its confirmatory verdicts use the **core
decision lens** (of 15 cells: 11 unchanged, 3 membership-changed, 1 destabilised, 0 reversed)
(the rules and config were frozen before the data, the protocol document was committed after the run).
See [RESULTS-v3.md](docs/RESULTS-v3.md), its [frozen protocol](docs/BENCHMARK-PROTOCOL-v3.md), and the
claim-to-evidence ledger [CLAIM-LEDGER.md](docs/CLAIM-LEDGER.md).

**Current: 952 offline tests, 0 failing; 51 scientific-correctness oracles; package version 0.3.0.**

## Why this exists

Finding a landscape that *looks* like Mars is easy. Designing a terrestrial study whose
result legitimately transfers to a Mars decision is hard. TerraTrace makes the transfer
logic explicit: measurable requirements, common-support comparison, an explicit
transfer-gap ledger, and a draft study protocol — with every number traceable to a
source and a transformation.

## What runs today (verified)

- **One-command real multi-body study:** `scripts/run_real_analog_study.py` runs the entire real
  pipeline from one config — preflight, fetch (or offline `--synthetic` / `--dry-run`), a
  full-depth study (significance, block bootstrap, landform, terrain spectra, previews), decision
  confidence, and a complete bundle (study.json, report.md, report.html, offline viewer,
  REFERENCES, CHECKSUMS, confidence.json). See [REAL-DATA-RUNBOOK.md](REAL-DATA-RUNBOOK.md).
- Pure-NumPy morphology engine: slope, local relief, detrended ruggedness, low-slope
  connectivity.
- **Multi-body screening — five reference bodies (Earth, Mars, Moon, Mercury, Ceres):**
  the engine screens Earth candidates against a Mars, Moon, Mercury, *or* Ceres reference.
  `reproject.py` warps each AOI on its own figure — Mars sphere (R=3,396,190 m), Moon
  sphere (R=1,737,400 m, LRO/LOLA), Mercury sphere (R=2,439,400 m, MESSENGER), Ceres sphere
  (R=469,730 m, Dawn), Earth WGS84 — so slope and relief are true metres on every body;
  `catalog.py` carries keyless planetary DEMs for the non-Earth bodies (Mars MOLA, the Moon
  LRO LOLA LDEM ~118 m, Mercury MESSENGER ~665 m, Ceres Dawn HAMO ~137 m) and `preflight.py`
  accepts each body with its own longitude convention. Strongly irregular bodies such as
  Vesta are deliberately **not** offered — a single sphere would misrepresent them.
  Mars/Earth/Moon behaviour and the gated synthetic study hash are unchanged.
- **Self-contained HTML report:** `report_html.py` renders a study package or a
  cross-reference batch into a single polished, fully self-contained, offline HTML document
  — inline CSS only, no external or CDN assets, every dynamic value HTML-escaped, and
  deterministic (no timestamps). It mirrors the Markdown report section-for-section and
  reproduces the claim firewall verbatim; `scripts/make_html_report.py` renders it and the
  existing Markdown report remains.
- **DEM co-registration + vertical datum:** `coregister.py` aligns two elevation grids
  before they are differenced or compared. It recovers a horizontal pixel shift via an
  overlap-RMSE search with sub-pixel parabola refinement and estimates a single
  vertical-datum (bias) offset — translation only, NaN-aware, pure NumPy. It performs **no**
  rotation, scaling, or non-rigid warp and makes no mechanical or mission claim.
- **Terrain fingerprint + similarity search:** `fingerprint.py` distils the descriptor bank
  into a compact 11-field normalized morphology signature, scores two signatures with a
  bounded similarity in (0, 1] (1.0 iff identical), and `rank_library()` ranks a library of
  reference terrains to find the nearest morphological match. This is a morphology signature
  and ranking, **not** a classification, identity, or geological-equivalence claim.
- **Elevation-error propagation:** every catalog source now carries an approximate 1-sigma
  vertical accuracy (`vertical_accuracy_m`), and `errorprop.py` propagates it analytically
  into map-scale feature uncertainty — a central-difference model gives a slope-angle sigma
  `sigma_z / (dx*sqrt(2)) / (1 + tan(slope)^2)`, a local-relief sigma `sqrt(2)*sigma_z`, and a
  rough ruggedness bound `~ sigma_z`. Like the independent-pixel bootstrap it assumes
  **independent** per-pixel errors, so every figure is an **optimistic lower bound** — real
  DEM errors are spatially correlated. Map-scale morphology uncertainty only; no mechanical or
  mission claim.
- **Inline hillshade previews:** `hillshade.py` renders a Horn shaded-relief image of an
  elevation grid and encodes it as a base64 PNG **data URI using only the standard library**
  (`zlib` / `struct` / `base64` — no PIL or other image dependency), so a terrain preview can
  be embedded inline in the self-contained HTML report with no external assets. It is a
  visualisation aid only: the shading encodes illuminated surface orientation and makes no
  quantitative, mechanical, or trafficability claim.
- **Measurement-uncertainty bands + previews, now in the report and viewer (opt-in):**
  `compare_units` / `run_real_study` accept an opt-in `vertical_accuracy` (a scalar, or
  per-unit; a real study auto-resolves it from each source's catalog vertical accuracy) and
  `previews=True`. When supplied, the study package carries `feature_uncertainty` (propagated
  1-sigma slope / relief / ruggedness bands per unit) and `previews` (one self-contained
  hillshade PNG data-URI per unit), and both the HTML report and the offline viewer render a
  **"Measurement uncertainty"** table and inline terrain previews. Both are **off by default**,
  so the synthetic study package and its gated provenance hash stay byte-for-byte unchanged. The
  bands assume independent per-pixel error, so (like the independent-pixel bootstrap) they are an
  optimistic lower bound — map-scale morphology uncertainty only, no mechanical or mission claim.
- **Sensitivity / ablation report:** `sensitivity.py` re-runs the finished screen to ask whether
  the recommendation actually survives the analyst's choices. `lens_ablation` re-runs it under the
  default decision lenses (`core` / `extended` / `geomorphic` / `landform` / `texture`, plus the opt-in
  `hydro`), `support_ablation` re-runs it across
  a set of common-support scales, and `ablation_report` combines them into an `overall_stable`
  verdict — reporting whether the same unit is recommended throughout, or flagging that the
  recommendation is fragile. It is a robustness diagnostic over the existing morphology screen and
  adds no new claim.
- **Transparent terrain-type classifier:** `terrain_classify.py` assigns a tile a single
  descriptive map-scale morphology type — `flat_plain`, `rolling`, `dissected_upland`, or
  `rough_rugged` — by a fully auditable set of documented threshold rules over the descriptor bank
  (no ML, no training, no randomness), returning the label with its supporting evidence, per-type
  scores, and a confidence margin. It is a **descriptive** morphology label only, explicitly
  **not** a geological, genetic, lithological, hazard, or mission/rover classification.
- **Data sources & credits bundle:** `references.py` (+ `scripts/make_references.py`) reads the
  15-source catalog and renders a complete, deterministic "Data sources & credits" section —
  product, provider, citation, and licence per source, grouped by body — so every study is
  properly attributed to its upstream providers (NASA PDS / USGS Astrogeology / ESA Copernicus /
  NASA-JAXA). The exact product a given run ingested stays pinned in `sources.lock.yml`.
- **Cross-body fingerprint similarity search:** `fingerprint_library.py` (+
  `scripts/fingerprint_search.py`) builds a library of reference-terrain fingerprints and
  ranks candidates against them — including the cross-**body** case, ranking Earth candidates
  against each planetary (Mars-like, Moon-like) reference and naming the single reference each
  candidate most resembles. A morphological similarity ranking only, **not** a classification,
  identity, or geological-equivalence claim; it inherits the fingerprint layer's firewall
  unchanged.
- **Per-candidate site dossiers:** `dossier.py` distils the whole study package into a focused
  per-candidate decision brief — its per-metric morphology distances, Pareto-frontier layer,
  eligibility verdict, bootstrap non-domination / clear-winner frequencies and distance CIs
  (when a bootstrap was run), whether it is the recommendation, and the transfer-gap ledger +
  prohibited claims — as a structured dict and as Markdown. It only re-presents what the engine
  already decided; it never widens a claim.
- **Expanded stdlib HTTP API:** the dependency-free localhost API adds `GET /bodies`
  (supported bodies + source registry), `POST /validate` (scientific-correctness suite),
  `POST /batch` (synthetic cross-reference batch), and `POST /report` (study + Markdown
  report) beside the existing `GET /health`, `GET /study`, and `POST /compare`. It stays
  loopback-only with a Host allowlist and a 64 KiB body cap; the bootstrap `n_boot` is
  capped at 500 for interactive responsiveness.
- Expanded geomorphometric descriptors (non-destructive analysis layer): Zevenbergen-Thorne
  profile / plan / mean curvature, the Vector Ruggedness Measure (surface-normal dispersion,
  decoupled from mean slope), and a multiscale roughness structure function with its Hurst
  scaling exponent — each proven on analytic cases (zero on a plane, bit-exact on a
  paraboloid, VRM rising with roughness, Hurst = 1 on a linear ramp). They power an opt-in
  `geomorphic` decision mode (curvature + VRM as extra Pareto axes) as a third robustness
  lens, and leave the default study pipeline and its provenance hash unchanged.
- **Expanded geomorphometry (analysis layer):** `features.py` adds the surface-area ratio
  (rugosity — exactly 1 on flat ground, `sec(slope)` on a tilted plane), the Riley (1999)
  Terrain Ruggedness Index, a Topographic Position Index map, and a ridge/valley/flat
  landform-fraction mix. All four are surfaced in `descriptors.descriptor_bank`; like the
  other descriptors they sit outside the default decision, so the study package and its
  provenance hash are unchanged.
- **Line-of-sight terrain structure — topographic openness + geomorphons (opt-in):**
  `openness.py` computes positive/negative **topographic openness** (Yokoyama, Shirasawa &
  Pike 2002) from zenith/nadir sight-line angles averaged over eight azimuths — exactly 90° on
  a flat surface, high on peaks/ridges (positive) or in pits/valleys (negative) — and
  `geomorphons.py` performs **geomorphon landform classification** (Jasiewicz & Stepinski 2013):
  a per-cell ternary line-of-sight signature `(n_plus, n_minus)` reduced to the ten common
  landforms (flat, peak, ridge, shoulder, spur, slope, hollow, footslope, valley, pit). The
  ternary signature is computed exactly as the method prescribes; the 10-form reduction uses an
  explicit, antisymmetric rule validated against canonical synthetic landforms — **not** a
  verbatim copy of any particular GIS lookup table — and a normalised 9×9 geomorphon spectrum is
  also exposed. Both are pure NumPy and relief/orientation-invariant. They power a fourth, opt-in
  `decision_metrics="landform"` lens (the core axes plus a geomorphon-spectrum total-variation
  distance and a topographic-openness distance), optional landform terms in the descriptor bank
  and terrain fingerprint, and — with `landform=True, previews=True` — a landform-composition
  table, openness medians, and categorical landform / grayscale openness map previews in the HTML
  report and offline viewer. Everything is **off by default**, so the synthetic study package and
  its gated provenance hash stay byte-unchanged. Map-scale **morphology only** — it does not
  estimate traversability, hazard, geologic-unit identification, or mission readiness, and it is
  not NASA-endorsed.
- **Scale & fabric — spectral roughness + directional anisotropy (opt-in):** `spectral.py`
  reduces an elevation grid to a **radially-averaged 2-D power spectral density** (detrend the
  plane, Hann-window, FFT, radially average over wavenumber) and reports the log-log **spectral
  slope** (how power is shared between long and short wavelengths), the per-band RMS **roughness**
  (long/mid/short wavelength bands), the **peak wavelength**, and a total power that recovers the
  detrended variance by Parseval; `anisotropy.py` measures the **directional structure function**
  (RMS elevation difference along a fan of azimuths) and reports anisotropy **strength** (0 =
  isotropic → 1 = strongly lineated), the fabric **orientation** (azimuth of minimum roughness —
  the strike along which ridges or dunes run), and an isotropy ratio. Both are pure NumPy.
  `study.compare_units(..., terrain_spectra=True)` / `run_real_study(terrain_spectra=True)` attach
  a per-unit `spectral` + `anisotropy` block, the HTML report and offline viewer render a **"Scale
  & fabric"** section when present, and the descriptor bank and terrain fingerprint gain opt-in
  spectral/anisotropy terms. **Off by default**, so the synthetic study package and its gated
  provenance hash stay byte-unchanged. Map-scale **morphology only** — a roughness spectrum and
  directional fabric of the sampled DEM, **not** a traversability, hazard, geologic, or
  mission-readiness claim, and nothing about rock-scale obstacles below the pixel. (Perron,
  Kirchner & Dietrich 2008; Shepard et al. 2001.)
- Common-support aggregation with valid-fraction tracking (missingness never hidden).
- Distribution distances (Wasserstein-1, KS, quantile fingerprint) with no SciPy.
- Eligibility filters + Pareto/tie/indeterminate decision (no composite "Mars-likeness"
  score).
- Multi-candidate Pareto **frontier** ranking (peeled non-dominated layers + dominance
  matrix) so a batch run yields a defensible shortlist, not just a winner.
- Sensitivity across scenarios with a pairwise rank-flip matrix.
- **Bootstrap uncertainty, two ways:** confidence intervals on every distance and a
  non-domination *frequency* per candidate, computed either by the default
  `independent`-pixel bootstrap or by a spatial **block** bootstrap
  (`bootstrap_method: block`). The block method moving-block-resamples block×block patches
  so spatial autocorrelation is preserved, giving honest, autocorrelation-aware CIs that
  are typically **wider** than the optimistically narrow independent ones — selectable
  end-to-end and active whenever `n_boot > 0`.
- **Data-driven block size:** `autocorr.py` estimates a DEM's spatial autocorrelation
  curve and its correlation length (the 1/e e-folding lag) and suggests a block size from
  it. That size feeds the spatial block bootstrap above, so the block length is chosen from
  the terrain's own autocorrelation rather than guessed.
- **Statistical significance:** `significance.py` adds a one-sided permutation test — *is
  candidate A significantly closer to the reference than B, or could the closeness gap
  arise by chance under random relabelling?* — returning a p-value and a standardized
  effect size, plus a bootstrap confidence interval on each distance. Closeness gaps are
  now tested, not merely asserted.
- **Statistical confidence for the analog decision (opt-in, gated):** `compare_units` /
  `run_study` / `run_real_study` accept `significance=True, n_perm=1000` to attach a
  `significance` block — a one-sided permutation test (`significance.permutation_closer_test`)
  of whether the recommended unit is genuinely closer to the reference than the **runner-up**
  (the second-closest candidate), computed per sample-based morphology metric (slope, relief,
  ruggedness) with the decision's own scales, with per-metric one/two-sided p-values, an effect
  size, and a `recommendation_significant` flag (connectivity is a scalar and reported as such).
  `confidence.decision_confidence()` then restates the robustness evidence a study already holds
  as **three independent signals** — bootstrap non-domination frequency, significance vs the
  runner-up, and lens/support stability — and returns a single **non-composite verdict** (`robust`
  / `qualified` / `fragile` / `tie` / `indeterminate` / `blocked` / `not_comparable` /
  `unverified`) with a plain-language rationale and an explicit list of the signals that were
  **not** evaluated; there is no weighted score, and a missing signal degrades to "not evaluated"
  rather than being invented. The HTML report and offline viewer render a "Decision confidence"
  section and a "Significance vs runner-up" table only when a robustness signal was actually
  computed, the CLI gains `study --significance --n-perm` and a `confidence` subcommand, and the
  HTTP API gains `POST /confidence`. Both are **off by default**, so the synthetic study package
  and its gated provenance hash stay byte-unchanged. Distribution-shape resampling statistics and
  map-scale morphology only — never a traversability, hazard, geologic-equivalence, or mission
  claim.
- Cross-reference, multi-lens **batch studies** (`run_batch` / `run_real_batch`): the
  full comparison is rerun for every Mars-reference × decision-lens cell, then
  synthesised into each candidate's layer-1 (non-dominated) frequency across references
  and lenses, a **consensus shortlist** of candidates non-dominated in *every* cell, and
  a robust ordering — a transparent robustness synthesis, not a composite score.
- Transfer-gap ledger (T0–T4 classes) and a draft study protocol.
- Evidence graph + content hashing; deterministic study package + a self-contained,
  offline **viewer** that now shows a target-body badge, a per-axis decision matrix, a
  Pareto-frontier panel, and a bootstrap-uncertainty panel.
- **Data & sources layer (15-source registry):** a citeable **catalog** of real DEM
  products — Mars MOLA, the **Moon LRO LOLA LDEM** (~118 m), **Mercury MESSENGER** (~665 m)
  and **Ceres Dawn HAMO** (~137 m) — all keyless — and for Earth:
  Copernicus GLO-30/90, USGS 3DEP (10 m / 1 m), SRTM GL1/GL3, NASADEM, and ALOS AW3D30 —
  each with spatial-coverage metadata, a
  land-morphology **preference** tier, and known nodata sentinels; `recommend_source()`
  auto-picks the covering product for an AOI + target support (and refuses a US-only
  product for a non-US bbox, or an SRTM product above 60°N). A fail-fast **preflight**
  validates the config schema and every AOI bbox and sizes the request before any
  download; **idempotent** fetching (skip-if-present + a sha256 provenance manifest)
  avoids re-downloading gigabytes; downloads are atomic with retry/backoff honouring
  `Retry-After`; and a DEM **QA profiler** reports valid / water / NaN fractions, robust
  relief, and advisory flags (sentinels applied first).
- **Publication-grade reporting:** `report.py` turns a study package or a cross-reference
  batch into a single citable Markdown document — result plus a plain-language verdict, the
  per-axis decision table across the chosen lens, eligibility, an uncertainty section when a
  bootstrap was run, scenario sensitivity, the transfer-gap ledger, and a provenance
  appendix carrying the package hash. It reproduces the claim firewall verbatim and never
  widens it; `scripts/make_report.py` renders it and the CLI has a `report` subcommand.
- **Reproducibility verifier:** `repro.py` recomputes and verifies a package's content hash
  (detecting any tamper or truncation), diffs two packages key-by-key, and confirms the
  synthetic study reproduces bit-for-bit; `scripts/verify_study.py` is the CLI and exits 0
  only on a match, so a reviewer can confirm a published study is authentic.
- **Validation & benchmarking:** a scientific-correctness suite that drives the *real*
  engine on synthetic terrains with known relationships and proves it behaves correctly —
  self-distance is zero, slope/relief/ruggedness are invariant to vertical offset and 90°
  rotation, distance grows monotonically with roughness (real discriminating power), a
  closer candidate provably dominates and is recommended, a flat/water tile is blocked,
  and the whole pipeline is deterministic. A reproducibility + performance harness pins
  behavioural invariants, checks hash stability, and profiles wall-clock scaling.
- 952 fixture tests with known analytic answers, all passing, no network required.

```
passed=952 failed=0 skipped=0
```

## Install

The engine core needs only Python 3.10+ and NumPy. Real-data ingestion adds `rasterio`
and `requests`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt           # numpy (core)
pip install -r requirements-real.txt      # rasterio + requests (real DEMs)
```

## Run (synthetic, offline, reproducible)

```bash
PYTHONPATH=. python3 -m terratrace.cli --out artifacts
PYTHONPATH=. python3 -m terratrace.build_viewer      # writes viewer/index.html
PYTHONPATH=. python3 tests/run_tests.py              # 952 tests
```

Open `viewer/index.html` in any browser — it is self-contained and works offline.

### Unified CLI

Every entry point lives behind one dispatcher — `python -m terratrace.cli <command>`:

```bash
PYTHONPATH=. python3 -m terratrace.cli validate      # scientific-correctness suite
PYTHONPATH=. python3 -m terratrace.cli benchmark     # reproducibility + scaling profile
PYTHONPATH=. python3 -m terratrace.cli report        # render a Markdown study report
PYTHONPATH=. python3 -m terratrace.cli report-html   # render a self-contained HTML report
PYTHONPATH=. python3 -m terratrace.cli dossier       # per-candidate site decision brief
PYTHONPATH=. python3 -m terratrace.cli confidence    # non-composite decision confidence for a study JSON
PYTHONPATH=. python3 -m terratrace.cli bank          # full geomorphometric descriptor bank for a tile
PYTHONPATH=. python3 -m terratrace.cli transect      # extract a swath / elevation profile across a DEM
PYTHONPATH=. python3 -m terratrace.cli version       # print version + schema
```

With no known command, options route to the implicit `study` command, so the legacy
`python -m terratrace.cli --out artifacts` call above keeps working unchanged.

## HTTP API (stdlib, no extra deps)

```bash
PYTHONPATH=. python3 -m terratrace.api --port 8000     # localhost only
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/compare -H "content-type: application/json" \
     -d '{"n_boot": 300}'
```

Endpoints: `GET /health`, `GET /study`, `GET /bodies` (supported bodies + source
registry), `POST /compare` (body `{"target_support_m", "n_boot", "significance", "n_perm"}`,
inputs validated/clamped; `significance` opts in to the permutation block), `POST /validate`
(scientific-correctness suite), `POST /batch` (synthetic cross-reference batch), `POST /report`
(study + Markdown report), `POST /dossier` (per-candidate decision briefs), `POST /report.html`
(the report as a standalone HTML document), `POST /confidence` (non-composite decision
confidence for a posted study package), `POST /bank` (the full geomorphometric descriptor bank
for a posted tile), and `POST /transect` (a swath / elevation profile across a posted DEM). The `n_boot` bootstrap count is capped at 500 and the
`n_perm` permutation count at 2000 for interactive responsiveness. The server is
**unauthenticated and binds to 127.0.0.1 by default** — put auth and rate limiting
in front of it before exposing it to a network.

## Run with REAL data

See [REAL-DATA-RUNBOOK.md](REAL-DATA-RUNBOOK.md). Minimal real stack:

| Layer | Source | Native | API key? |
|---|---|---|---|
| Mars | USGS Astrogeology **Mars MGS MOLA DEM 463m** GeoTIFF | 463 m | none |
| Moon | USGS Astrogeology / LRO **LOLA LDEM** (global ~118 m) | 118 m | none |
| Mercury | USGS Astrogeology / **MESSENGER global DEM** (~665 m) | 665 m | none |
| Ceres | USGS Astrogeology / **Dawn HAMO global DTM** (~137 m) | 137 m | none |
| Earth (keyless) | **Copernicus GLO-30 COG mosaic** on AWS Open Data — the matched-footprint benchmark default (`--source cog`) | 30 m | **none** |
| Earth (global) | **Copernicus GLO-30 / GLO-90** via OpenTopography | 30 / 90 m | free key |
| Earth (near-global) | **NASADEM**, **SRTM GL1 / GL3**, **ALOS AW3D30** via OpenTopography | 30 / 90 m | free key |
| Earth (US, higher-res) | **USGS 3DEP** 1/3″ (~10 m) / 1 m lidar via OpenTopography / ImageServer | 10 / 1 m | free key / none |

The full 15-source registry (coverage, preference tier, nodata sentinels, licence,
citation, vertical datum) lives in `terratrace/catalog.py`;
`catalog.recommend_source(bbox, body, target_support_m)` picks the right product for an
AOI automatically — preferring the best land-morphology product that covers the box and
reaches the target support, and declining a source whose footprint does not reach the AOI
(e.g. SRTM north of 60°N, or a US-only product abroad).

```bash
export OPENTOPO_API_KEY=...            # from portal.opentopography.org (My Account)
python3 scripts/fetch_real_dems.py --config config/aois.example.yml --preflight-only  # dry run
python3 scripts/fetch_real_dems.py --config config/aois.example.yml                   # fetch
python3 scripts/profile_dem.py data/earth/candidate_b_cop30.tif                       # QA a file
PYTHONPATH=. python3 scripts/run_real_study.py --config config/aois.example.yml
```

`fetch_real_dems.py` runs a no-network **preflight** first (schema + every bbox), chooses
the covering source, and prints an approximate download size so a malformed or oversized
AOI is caught before a byte moves. Fetching is **idempotent** — a file already present is
skipped (`--force` to override) and every fetch is recorded in `data/fetch_manifest.json`
with its sha256. Downloads must run on a networked machine; the engine then compares the
real arrays through the identical pipeline used by the synthetic path.

## Project layout

```
terratrace/
  terratrace/        engine package (synthetic + real share one comparison core)
    # --- comparison core ---------------------------------------------------
    __init__.py      package version — the single source of truth for pyproject + the manifest
    features.py      slope / relief / ruggedness / connectivity + curvature / VRM / roughness
    support.py       common-support aggregation (valid-fraction tracked)
    masks.py         sentinel / water / nodata masking to NaN
    reproject.py     per-body azimuthal-equidistant metric reprojection (five bodies)
    distances.py     Wasserstein-1, KS, quantile fingerprints
    decision.py      eligibility, Pareto, tie policy, rank flips
    frontier.py      multi-candidate Pareto layers + dominance matrix
    uncertainty.py   bootstrap resampling (independent pixels + spatial block)
    study.py         compare_units + run_study + run_real_study
    synthetic.py     deterministic offline terrains for the tests and the gated study
    regions.py       named multi-region reference / candidate sets
    gaps.py          transfer-gap taxonomy (T0-T4)
    provenance.py    evidence graph + content hashing
    protocol.py      draft study protocol
    bundle.py        export a study into a self-contained bundle
    repro.py         recompute / verify a package hash + diff + reproduce check
    coregister.py    translational DEM alignment + vertical-datum offset
    errorprop.py     vertical accuracy -> slope / relief / ruggedness uncertainty
    # --- geomorphometric descriptor bank (analysis layer) ------------------
    descriptors.py   the full descriptor bank, one call per tile
    curvature_classes.py  Wood (1996) morphometric curvature classes
    fabric_eigen.py  Woodcock (1977) surface-normal orientation-tensor fabric
    openness.py      topographic openness (positive / negative, Yokoyama 2002)
    openness_difference.py  Yokoyama (2002) slope position from the openness difference
    geomorphons.py   geomorphon landform classification (Jasiewicz & Stepinski 2013)
    tpi_landform.py  Weiss (2001) single-scale TPI slope-position classes
    multiscale_tpi.py  Weiss (2001) two-scale nested TPI classes
    spectral.py      radially-averaged 2-D PSD: spectral slope / band roughness / peak wavelength
    anisotropy.py    directional structure function: terrain-fabric strength + orientation
    multiscale.py    Haar wavelet multiscale-energy spectrum
    wavelet_roughness.py  wavelet-based multiscale roughness signature
    variogram.py     Matheron (1963) semivariogram range / sill / nugget
    roughness_length.py  Shepard (2001) RMS / Allan-deviation roughness length
    kh_roughness.py  Kreslavsky-Head (2000) baseline roughness (the MOLA-roughness metric)
    iwahashi_pike.py Iwahashi-Pike (2007) three-signature terrain class
    normal_roughness.py  surface-normal-dispersion roughness
    fractal.py       differential box-counting fractal dimension
    lacunarity.py    gliding-box lacunarity
    entropy_terrain.py  Shannon slope entropy
    hypsometry.py    Strahler hypsometric curve + integral
    slope_area.py    Flint (1974) slope-area concavity
    drainage.py      depression-filled D8 flow accumulation + dissection texture
    twi.py           Topographic Wetness Index (Beven & Kirkby 1979)
    convergence.py   convergence index (Kothe & Lehmeier 1996)
    svf.py           sky-view factor (Zaksek, Ostir & Kokalj 2011)
    melton_relief.py Melton (1965) relief scalars + elevation-relief ratio
    transect.py      swath / elevation-profile extractor
    terrain_classify.py  rule-based descriptive terrain-type label (map-scale)
    hillshade.py     Horn shaded-relief PNG data URI (pure stdlib, self-contained)
    # --- decision robustness ----------------------------------------------
    sensitivity.py   lens / support ablation -> recommendation-stability report
    significance.py  permutation test + effect size + bootstrap distance CI
    confidence.py    non-composite decision confidence (three signals -> verdict)
    autocorr.py      spatial autocorrelation length -> data-driven block size
    batch.py         cross-reference, multi-lens batch synthesis
    fingerprint.py   compact morphology signature + similarity + library ranking
    fingerprint_library.py  cross-body fingerprint library + similarity search
    dossier.py       per-candidate decision brief (structured dict + Markdown)
    # --- matched-footprint benchmark (protocol v1 -> v3) -------------------
    matched_benchmark.py  support-vs-extent harness (synthetic method validation)
    matched_real.py  real per-body reprojected crops -> matched / mismatched / scale-grid panel
    comparability.py the honest-regime gate (footprint match + support >= effective resolution)
    resolution.py    resolution-matching control (source-smoothing false analogs)
    confirmation.py  per-class S / V confirmation rules + specificity controls
    adversarial.py   bounded-perturbation robustness stress
    adequacy.py      absolute adequacy from the reference's own variability
    panel_v3.py      the v3 confirmatory reference panel + classify_resolution_change
    # --- data, interfaces, meta -------------------------------------------
    catalog.py       15-source registry: coverage, preference, nodata, vertical accuracy, selection
    preflight.py     fail-fast config-schema + AOI/bbox/size/coverage checks
    profile.py       DEM QA report (valid / water / NaN, relief, advisory flags)
    ingest.py        real DEM download (atomic + retry/backoff) + raster read
    fetchcache.py    idempotent fetch decisions + sha256 provenance manifest
    sourcelock.py    sources.lock.yml: sha256 / size / CRS / bounds / citation per input
    cop30_cog.py     keyless ESA Copernicus GLO-30 COG reader (windowed HTTP range reads)
    references.py    data sources & credits bundle (citation + licence per source)
    report.py        publication-grade Markdown report (study or batch package)
    report_html.py   self-contained offline HTML report (study or batch)
    build_viewer.py  self-contained HTML viewer
    cli.py           unified dispatcher: study / validate / benchmark / report / report-html /
                     dossier / confidence / bank / transect / version
    api.py           loopback-only stdlib HTTP API
    validation.py    scientific-correctness suite (51 oracles, drives the real engine)
    benchmark.py     reproducibility invariants + wall-clock scaling profile
  tests/             952 automated tests across 100 test modules + a dependency-free runner (house style:
                     module-level `def test_*`, no pytest)
  artifacts/         generated study package (JSON + checksums + manifest)
  viewer/            generated offline HTML viewer (tracked snapshot; CI regenerates it)
  config/            AOI configs, incl. matched_footprint_v3.yml and real_multibody.example.yml
  scripts/           fetch / profile / validate / benchmark / make_reports / make_references /
                     verify_study / fingerprint_search / export_bundle / inspect_study /
                     make_source_lock / make_mars_sample / fetch_earth_candidates /
                     run_matched_benchmark / run_analog_atlas / run_scale_profile / run_batch_study /
                     run_benchmark / run_validation / run_real_study / run_real_analog_study /
                     ci_hygiene_check / doc_consistency_check / make_paper_pdf.sh /
                     make_site_viewer.py
```

## Scientific method

See [docs/method.md](docs/method.md) for the comparison method, [docs/limitations.md](docs/limitations.md)
for what the engine deliberately does not claim, and [docs/VALIDATION.md](docs/VALIDATION.md)
for the validation evidence.

## Compliance

This repository is a **public research/production project**. NASA Space Apps 2026 runs
**Nov 14–15, 2026**, and the official rules say the *submitted* solution must be
developed during the event. If you intend to submit to the official event, treat this
code as prior public work and build the submission fresh during the event window, or
confirm eligibility in writing with the organizer. See
[CLEAN-ROOM-NOTE.md](CLEAN-ROOM-NOTE.md).

## License

MIT — see [LICENSE](LICENSE). Source datasets keep their own terms (NASA PDS / USGS /
Copernicus); cite them per [REAL-DATA-RUNBOOK.md](REAL-DATA-RUNBOOK.md).
