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
- Sensitivity across scenarios with a pairwise rank-flip matrix.
- Transfer-gap ledger (T0–T4 classes) and a draft study protocol.
- Evidence graph + content hashing; deterministic study package + static viewer.
- 24 fixture tests with known analytic answers, all passing, no network required.

```
passed=24 failed=0
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
PYTHONPATH=. python3 tests/run_tests.py              # 24 tests
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

| Layer | Source | API key? |
|---|---|---|
| Mars | USGS Astrogeology **Mars MGS MOLA DEM 463m** GeoTIFF | none |
| Earth | **Copernicus GLO-30** via OpenTopography API | free key |

```bash
export OPENTOPO_API_KEY=...            # from portal.opentopography.org (My Account)
python3 scripts/fetch_real_dems.py --config config/aois.example.yml
PYTHONPATH=. python3 scripts/run_real_study.py --config config/aois.example.yml
```

Downloads must run on a networked machine; the engine then compares the real arrays
through the identical pipeline used by the synthetic path.

## Project layout

```
terratrace/
  terratrace/        engine package (synthetic + real share one comparison core)
    features.py      slope / relief / ruggedness / connectivity
    support.py       common-support aggregation
    distances.py     Wasserstein-1, KS, fingerprints
    decision.py      eligibility, Pareto, tie policy, rank flips
    gaps.py          transfer-gap taxonomy (T0-T4)
    provenance.py    evidence graph + hashing
    protocol.py      draft study protocol
    study.py         compare_units + run_study + run_real_study
    ingest.py        real DEM download + raster read (rasterio/requests)
    build_viewer.py  self-contained HTML viewer
    cli.py           study runner
  tests/             24 fixture tests + dependency-free runner
  artifacts/         generated study package (JSON + checksums + manifest)
  viewer/            generated offline HTML viewer
  config/            AOI configuration for real runs
  scripts/           real-data fetch + run helpers
```

## Scientific method

See the full planning library in `../Planetary-Analog-OS-Plan/` (23 module plans,
diagrams, equations, validation, ablations, governance, economics, roadmap).

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
