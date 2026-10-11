# Planetary Analog OS — TerraTrace

[![CI](https://github.com/pal-123456789/terratrace/actions/workflows/ci.yml/badge.svg)](https://github.com/pal-123456789/terratrace/actions/workflows/ci.yml)

**Map-scale terrain-morphology analog screening across five worlds — Earth, Mars, the Moon, Mercury, and Ceres.**

This repository holds two things:

| Path | What it is |
|---|---|
| `terratrace/` | The working engine (pure-NumPy): real DEMs → per-body metric reprojection → morphology descriptors → Pareto decision across four robustness lenses → honest uncertainty → transfer-gap ledger → provenance, report, and viewer. **379 tests**, no network required. |
| `site/` | A 3D scroll-animated website telling the project story (deployed on Vercel). |

> **Scope / claim firewall.** TerraTrace screens terrain **morphology** between curated
> map products. It does **not** estimate rover traversability, validate autonomy,
> establish geological equivalence, certify site access, or certify mission readiness.
> It is not NASA-endorsed.

## What it does

Loads real elevation models (Mars MOLA; Moon LOLA; Mercury MESSENGER; Ceres Dawn; Earth
Copernicus GLO-30/90, USGS 3DEP, SRTM, NASADEM, ALOS — a 13-product catalog with coverage,
licence, and vertical-accuracy metadata), warps each AOI to its own local metric grid on the
correct body, computes map-scale descriptors (slope, relief, ruggedness, connectivity,
curvature, vector ruggedness, roughness/Hurst, topographic openness, geomorphon landforms, …),
and ranks candidate terrains by **Pareto dominance** — never a composite "Mars-likeness" score.
It returns a recommendation only when it survives four independent decision lenses (core,
extended, geomorphic, landform), reports an honest TIE/INDETERMINATE/BLOCKED state
otherwise, and carries measurement uncertainty, a spatial block-bootstrap, significance tests,
a transfer-gap ledger, and a full provenance appendix. Everything is reproducible and
hash-anchored; a self-contained HTML report and offline viewer are generated per study.

## Run the engine

```bash
cd terratrace
pip install -r requirements.txt            # core (NumPy only)
python tests/run_tests.py                   # 379 fixtures, offline
python scripts/run_validation.py            # scientific-correctness suite
python -m terratrace.cli --out artifacts    # synthetic study
python -m terratrace.build_viewer           # viewer/index.html
```

Unified CLI: `python -m terratrace.cli {study, batch, validate, benchmark, report, report-html,
dossier, references, sensitivity, classify, version}`. Real data (keyless for the planetary
bodies; a free OpenTopography key for Earth) runs on a networked machine — see
`terratrace/REAL-DATA-RUNBOOK.md`. The large DEMs under `terratrace/data/` are git-ignored;
fetch them with `terratrace/scripts/fetch_real_dems.py`.

## The headline result

On real data (a Mars reference vs a Nevada desert and Craters of the Moon, Idaho), the four
**core** morphology axes recommend the lava field, but adding the **extended** descriptors
(aspect dispersion, hypsometric integral) turns the result into an honest **tie** — the "best
analog" depends on what you intend to test. The tool reports that rather than forcing a winner.
See `terratrace/docs/VALIDATION.md`.

## Deploy

Static site. On Vercel, import this repo; `vercel.json` serves `site/index.html` at `/` and the
study viewer at `/study`. No build step required.

## License

MIT (`terratrace/LICENSE`). Source datasets (NASA PDS/MOLA, LRO/LOLA, MESSENGER, Dawn, ESA
Copernicus, USGS 3DEP, SRTM, NASADEM, JAXA ALOS) keep their own terms; cite them per the runbook
and `terratrace/scripts/make_references.py`.
