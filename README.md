# Planetary Analog OS — TerraTrace

[![CI](https://github.com/pal-123456789/terratrace/actions/workflows/ci.yml/badge.svg)](https://github.com/pal-123456789/terratrace/actions/workflows/ci.yml)

**Map-scale terrain-morphology analog screening across five worlds — Earth, Mars, the Moon, Mercury, and Ceres.**

This repository holds two things:

| Path | What it is |
|---|---|
| `terratrace/` | The working engine (pure-NumPy): real DEMs → per-body metric reprojection → morphology descriptors → Pareto decision across four robustness lenses → honest uncertainty → transfer-gap ledger → provenance, report, and viewer. **487 tests**, no network required. |
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
curvature, vector ruggedness, roughness/Hurst, topographic openness, geomorphon landforms,
spectral slope, directional fabric, …),
and ranks candidate terrains by **Pareto dominance** — never a composite "Mars-likeness" score.
It returns a recommendation only when it survives four independent decision lenses (core,
extended, geomorphic, landform), reports an honest TIE/INDETERMINATE/BLOCKED state
otherwise, and carries measurement uncertainty, a spatial block-bootstrap, significance tests,
a transfer-gap ledger, and a full provenance appendix. On request it also attaches a map-scale
**scale & fabric** layer — a radially-averaged power spectrum (spectral slope, band roughness,
peak wavelength) and a directional-fabric descriptor (anisotropy strength and orientation) per
unit — rendered as a "Scale & fabric" section in the report and viewer. Every recommendation can
also carry a
one-sided **permutation p-value vs the runner-up** (the second-closest candidate) and a
**non-composite confidence verdict** (`robust` / `qualified` / `fragile` / …) that restates the
bootstrap, significance, and lens/support evidence as three independent signals — never a
weighted score, and never a traversability, hazard, geologic-equivalence, or mission-readiness
claim. Everything is reproducible and hash-anchored; a self-contained HTML report and offline
viewer are generated per study.

## Run the engine

```bash
cd terratrace
pip install -r requirements.txt            # core (NumPy only)
python tests/run_tests.py                   # 487 fixtures, offline
python scripts/run_validation.py            # scientific-correctness suite
python -m terratrace.cli --out artifacts    # synthetic study
python -m terratrace.build_viewer           # viewer/index.html
```

Unified CLI: `python -m terratrace.cli {study, batch, validate, benchmark, report, report-html,
dossier, references, sensitivity, classify, confidence, version}`. Real data (keyless for the planetary
bodies; a free OpenTopography key for Earth) runs on a networked machine — see
`terratrace/REAL-DATA-RUNBOOK.md`. The large DEMs under `terratrace/data/` are git-ignored;
fetch them with `terratrace/scripts/fetch_real_dems.py`. A single command —
`terratrace/scripts/run_real_analog_study.py` — runs the whole real multi-body pipeline end to end
(config → preflight → fetch → full-depth study → decision confidence → a complete bundle); see
`terratrace/REAL-DATA-RUNBOOK.md`.

## The headline result

On real data (a Mars reference vs a Nevada desert and Craters of the Moon, Idaho), the four
**core** morphology axes recommend the lava field, but adding the **extended** descriptors
(aspect dispersion, hypsometric integral) turns the result into an honest **tie** — the "best
analog" depends on what you intend to test. The tool reports that rather than forcing a winner.
See `terratrace/docs/VALIDATION.md`. A full method + results write-up is in
`terratrace/docs/PAPER.md`, and the real worked example (with the four-lens ablation) in
`terratrace/docs/REAL-EXAMPLE.md`. The multi-reference, lens-robustness **analog atlas** (one
command over many references × many candidates) is documented in `terratrace/docs/ATLAS.md`.

## Deploy

Static site. On Vercel, import this repo; `vercel.json` serves `site/index.html` at `/` and the
study viewer at `/study`. No build step required.

## License

MIT (`terratrace/LICENSE`). Source datasets (NASA PDS/MOLA, LRO/LOLA, MESSENGER, Dawn, ESA
Copernicus, USGS 3DEP, SRTM, NASADEM, JAXA ALOS) keep their own terms; cite them per the runbook
and `terratrace/scripts/make_references.py`.
