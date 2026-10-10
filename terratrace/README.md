# TerraTrace — Planetary Analog Terrain-Transfer Workbench (v0.1)

**Planetary Analog OS** nucleus. TerraTrace compares a Mars reference terrain unit
with candidate Earth terrain units at a declared common spatial support, shows which
map-scale morphology transfers, states what cannot transfer, and emits a reproducible,
provenance-tracked study package.

> **Scope / claim firewall.** TerraTrace screens terrain **morphology** between curated
> map products. It does **not** estimate rover traversability, validate autonomy,
> establish geological equivalence, certify site access, or certify mission readiness.
> It is not NASA-endorsed.

## Why this exists

Finding a landscape that *looks* like Mars is easy. Designing a terrestrial study whose
result legitimately transfers to a Mars decision is hard. TerraTrace makes the transfer
logic explicit: measurable requirements, common-support comparison, an explicit
transfer-gap ledger, and a draft study protocol — with every number traceable to a
source and a transformation.

## What runs today (verified)

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
- Cross-reference, multi-lens **batch studies** (`run_batch` / `run_real_batch`): the
  full comparison is rerun for every Mars-reference × decision-lens cell, then
  synthesised into each candidate's layer-1 (non-dominated) frequency across references
  and lenses, a **consensus shortlist** of candidates non-dominated in *every* cell, and
  a robust ordering — a transparent robustness synthesis, not a composite score.
- Transfer-gap ledger (T0–T4 classes) and a draft study protocol.
- Evidence graph + content hashing; deterministic study package + a self-contained,
  offline **viewer** that now shows a target-body badge, a per-axis decision matrix, a
  Pareto-frontier panel, and a bootstrap-uncertainty panel.
- **Data & sources layer (13-source registry):** a citeable **catalog** of real DEM
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
- 275 fixture tests with known analytic answers, all passing, no network required.

```
passed=275 failed=0
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
PYTHONPATH=. python3 tests/run_tests.py              # 275 tests
```

Open `viewer/index.html` in any browser — it is self-contained and works offline.

### Unified CLI

Every entry point lives behind one dispatcher — `python -m terratrace.cli <command>`:

```bash
PYTHONPATH=. python3 -m terratrace.cli validate      # scientific-correctness suite
PYTHONPATH=. python3 -m terratrace.cli benchmark     # reproducibility + scaling profile
PYTHONPATH=. python3 -m terratrace.cli report        # render a Markdown study report
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
registry), `POST /compare` (body `{"target_support_m", "n_boot"}`, inputs
validated/clamped), `POST /validate` (scientific-correctness suite), `POST /batch`
(synthetic cross-reference batch), and `POST /report` (study + Markdown report). The
`n_boot` bootstrap count is capped at 500 for interactive responsiveness. The server is
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
| Earth (global) | **Copernicus GLO-30 / GLO-90** via OpenTopography | 30 / 90 m | free key |
| Earth (near-global) | **NASADEM**, **SRTM GL1 / GL3**, **ALOS AW3D30** via OpenTopography | 30 / 90 m | free key |
| Earth (US, higher-res) | **USGS 3DEP** 1/3″ (~10 m) / 1 m lidar via OpenTopography / ImageServer | 10 / 1 m | free key / none |

The full 13-source registry (coverage, preference tier, nodata sentinels, licence,
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
    features.py      slope / relief / ruggedness / connectivity + curvature / VRM / roughness
    support.py       common-support aggregation
    distances.py     Wasserstein-1, KS, fingerprints
    decision.py      eligibility, Pareto, tie policy, rank flips
    frontier.py      multi-candidate Pareto layers + dominance matrix
    gaps.py          transfer-gap taxonomy (T0-T4)
    provenance.py    evidence graph + hashing
    protocol.py      draft study protocol
    study.py         compare_units + run_study + run_real_study
    batch.py         cross-reference, multi-lens batch synthesis
    descriptors.py   full geomorphometric descriptor bank (analysis layer)
    catalog.py       13-source registry: coverage, preference, nodata, vertical accuracy, selection
    preflight.py     fail-fast config-schema + AOI/bbox/size/coverage checks
    profile.py       DEM QA report (valid/water/NaN, relief, advisory flags)
    ingest.py        real DEM download (atomic + retry/backoff) + raster read
    fetchcache.py    idempotent fetch decisions + sha256 provenance manifest
    validation.py    scientific-correctness suite (drives the real engine)
    benchmark.py     reproducibility invariants + wall-clock scaling profile
    report.py        publication-grade Markdown report (study or batch package)
    report_html.py   self-contained offline HTML report (study or batch)
    significance.py  permutation test + effect size + bootstrap distance CI
    autocorr.py      spatial autocorrelation length -> data-driven block size
    repro.py         recompute/verify package hash + diff + reproduce check
    coregister.py    translational DEM alignment + vertical-datum offset
    fingerprint.py   compact morphology signature + similarity + library ranking
    fingerprint_library.py  cross-body fingerprint library + similarity search
    errorprop.py     vertical-accuracy -> slope / relief / ruggedness uncertainty
    hillshade.py     Horn shaded-relief PNG data URI (pure stdlib, self-contained)
    dossier.py       per-candidate decision brief (structured dict + Markdown)
    build_viewer.py  self-contained HTML viewer
    cli.py           unified dispatcher: study / validate / benchmark / report / version
  tests/             275 fixture tests + dependency-free runner
  artifacts/         generated study package (JSON + checksums + manifest)
  viewer/            generated offline HTML viewer
  config/            AOI configuration for real runs
  scripts/           fetch (+preflight) / profile / validate / benchmark / make_report / make_html_report / verify_study / fingerprint_search / run / run_batch_study
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
