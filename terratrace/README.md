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
- Common-support aggregation with valid-fraction tracking (missingness never hidden).
- Distribution distances (Wasserstein-1, KS, quantile fingerprint) with no SciPy.
- Eligibility filters + Pareto/tie/indeterminate decision (no composite "Mars-likeness"
  score).
- Multi-candidate Pareto **frontier** ranking (peeled non-dominated layers + dominance
  matrix) so a batch run yields a defensible shortlist, not just a winner.
- Sensitivity across scenarios with a pairwise rank-flip matrix.
- Transfer-gap ledger (T0–T4 classes) and a draft study protocol.
- Evidence graph + content hashing; deterministic study package + static viewer.
- **Data & sources layer (10-source registry):** a citeable **catalog** of real DEM
  products — Mars MOLA, and for Earth: Copernicus GLO-30/90, USGS 3DEP (10 m / 1 m),
  SRTM GL1/GL3, NASADEM, and ALOS AW3D30 — each with spatial-coverage metadata, a
  land-morphology **preference** tier, and known nodata sentinels; `recommend_source()`
  auto-picks the covering product for an AOI + target support (and refuses a US-only
  product for a non-US bbox, or an SRTM product above 60°N). A fail-fast **preflight**
  validates the config schema and every AOI bbox and sizes the request before any
  download; **idempotent** fetching (skip-if-present + a sha256 provenance manifest)
  avoids re-downloading gigabytes; downloads are atomic with retry/backoff honouring
  `Retry-After`; and a DEM **QA profiler** reports valid / water / NaN fractions, robust
  relief, and advisory flags (sentinels applied first).
- **Validation & benchmarking:** a scientific-correctness suite that drives the *real*
  engine on synthetic terrains with known relationships and proves it behaves correctly —
  self-distance is zero, slope/relief/ruggedness are invariant to vertical offset and 90°
  rotation, distance grows monotonically with roughness (real discriminating power), a
  closer candidate provably dominates and is recommended, a flat/water tile is blocked,
  and the whole pipeline is deterministic. A reproducibility + performance harness pins
  behavioural invariants, checks hash stability, and profiles wall-clock scaling.
- 156 fixture tests with known analytic answers, all passing, no network required.

```
passed=156 failed=0
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
PYTHONPATH=. python3 tests/run_tests.py              # 156 tests
```

Open `viewer/index.html` in any browser — it is self-contained and works offline.

## HTTP API (stdlib, no extra deps)

```bash
PYTHONPATH=. python3 -m terratrace.api --port 8000     # localhost only
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/compare -H "content-type: application/json" \
     -d '{"n_boot": 300}'
```

Endpoints: `GET /health`, `GET /study`, `POST /compare` (body
`{"target_support_m", "n_boot"}`, inputs validated/clamped). The server is
**unauthenticated and binds to 127.0.0.1 by default** — put auth and rate limiting
in front of it before exposing it to a network.

## Run with REAL data

See [REAL-DATA-RUNBOOK.md](REAL-DATA-RUNBOOK.md). Minimal real stack:

| Layer | Source | Native | API key? |
|---|---|---|---|
| Mars | USGS Astrogeology **Mars MGS MOLA DEM 463m** GeoTIFF | 463 m | none |
| Earth (global) | **Copernicus GLO-30 / GLO-90** via OpenTopography | 30 / 90 m | free key |
| Earth (near-global) | **NASADEM**, **SRTM GL1 / GL3**, **ALOS AW3D30** via OpenTopography | 30 / 90 m | free key |
| Earth (US, higher-res) | **USGS 3DEP** 1/3″ (~10 m) / 1 m lidar via OpenTopography / ImageServer | 10 / 1 m | free key / none |

The full 10-source registry (coverage, preference tier, nodata sentinels, licence,
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
    features.py      slope / relief / ruggedness / connectivity
    support.py       common-support aggregation
    distances.py     Wasserstein-1, KS, fingerprints
    decision.py      eligibility, Pareto, tie policy, rank flips
    frontier.py      multi-candidate Pareto layers + dominance matrix
    gaps.py          transfer-gap taxonomy (T0-T4)
    provenance.py    evidence graph + hashing
    protocol.py      draft study protocol
    study.py         compare_units + run_study + run_real_study
    catalog.py       10-source registry: coverage, preference, nodata, selection
    preflight.py     fail-fast config-schema + AOI/bbox/size/coverage checks
    profile.py       DEM QA report (valid/water/NaN, relief, advisory flags)
    ingest.py        real DEM download (atomic + retry/backoff) + raster read
    fetchcache.py    idempotent fetch decisions + sha256 provenance manifest
    validation.py    scientific-correctness suite (drives the real engine)
    benchmark.py     reproducibility invariants + wall-clock scaling profile
    build_viewer.py  self-contained HTML viewer
    cli.py           study runner
  tests/             156 fixture tests + dependency-free runner
  artifacts/         generated study package (JSON + checksums + manifest)
  viewer/            generated offline HTML viewer
  config/            AOI configuration for real runs
  scripts/           fetch (+preflight) / profile / validate / benchmark / run
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
