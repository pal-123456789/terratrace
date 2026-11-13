# Planetary Analog OS — TerraTrace

[![CI](https://github.com/pal-123456789/terratrace/actions/workflows/ci.yml/badge.svg)](https://github.com/pal-123456789/terratrace/actions/workflows/ci.yml)

**Map-scale terrain-morphology analog screening across five worlds — Earth, Mars, the Moon, Mercury, and Ceres.**

This repository holds two things:

| Path | What it is |
|---|---|
| `terratrace/` | The working engine (pure-NumPy): real DEMs → per-body metric reprojection → morphology descriptors → Pareto decision across six robustness lenses → honest uncertainty → transfer-gap ledger → provenance, report, and viewer. **836 tests**, no network required. |
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
It returns a recommendation only when it survives five independent decision lenses (core,
extended, geomorphic, landform, texture; a sixth, hydro, is opt-in via `decision_metrics`), reports an honest TIE/INDETERMINATE/BLOCKED state
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
python tests/run_tests.py                   # 836 fixtures, offline
python scripts/run_validation.py            # scientific-correctness suite
python -m terratrace.cli --out artifacts    # synthetic study
python -m terratrace.build_viewer           # viewer/index.html
```

Unified CLI: `python -m terratrace.cli {study, batch, validate, benchmark, report, report-html,
dossier, references, sensitivity, classify, confidence, bank, transect, version}`. Real data is
keyless for the planetary bodies **and for Earth** (see below) — no account, no API key. The large
DEMs under `terratrace/data/` are git-ignored; fetch them with
`terratrace/scripts/fetch_real_dems.py`. A single command —
`terratrace/scripts/run_real_analog_study.py` — runs the whole real multi-body pipeline end to end
(config → preflight → fetch → full-depth study → decision confidence → a complete bundle); see
`terratrace/REAL-DATA-RUNBOOK.md`.

## The headline result

**TerraTrace caught its own false analog.** Exploratory real-data runs (Mars MOLA vs three Earth
terrains) favoured Craters of the Moon, Idaho — a well-known basalt analog — and it would have been
easy to stop there. Instead the preference was tested under a protocol **frozen before the data were
seen**: matched physical footprints, supports at or above MOLA's effective resolution, three held-out
Martian volcanic plains, and two contrast terrains. It did not survive: the engine abstains for all
seven Mars references in the honest regime, and Craters is nearest for a cratered highland as readily
as for volcanic plains — a non-specific "least-dissimilar member of a weak shortlist" effect, not a
specific analog. Results: `terratrace/docs/RESULTS-v2.md`; frozen protocol:
`terratrace/docs/BENCHMARK-PROTOCOL-v2.md`; claim-to-evidence ledger: `terratrace/docs/CLAIM-LEDGER.md`.
The method write-up is `terratrace/docs/PAPER.md`; the earlier exploratory runs remain in
`terratrace/docs/REAL-EXAMPLE.md` (marked superseded). The multi-reference **analog atlas** is
documented in `terratrace/docs/ATLAS.md`.

**Then the explanation was tested, not asserted.** Protocol v3 added two **smoothness-matched
non-volcanic** Earth controls — the Nullarbor limestone plain and the Llano Estacado sedimentary
plain — 60 km windows for statistical power, and three fresh confirmatory Martian volcanic plains
alongside two fresh cratered highlands. The frozen v3 rules returned **S supported, V not
supported**: for **every** confirmatory volcanic plain, at **every** honest support, a smooth
**non-volcanic** terrain is on the Pareto front, while basaltic origin confers no advantage — the
basalts come to the front only for the *rough* highlands. So the nearest Earth analog tracks
**km-scale roughness, not volcanic origin**. Resolution robustness held (no reversals in 15
confirmatory honest cells). Recorded with one honest caveat: v3 is *pre-specified but not fully
pre-registered*. Results: `terratrace/docs/RESULTS-v3.md`; protocol:
`terratrace/docs/BENCHMARK-PROTOCOL-v3.md`.

**Reproduce it in three commands — no API key, no account.**

```bash
cd terratrace
python scripts/fetch_earth_candidates.py --config config/matched_footprint_v3.yml --source cog
python scripts/run_matched_benchmark.py --config config/matched_footprint_v3.yml --out artifacts/mf_panel_v3
```

`--source cog` reads the official ESA Copernicus GLO-30 cloud-optimised GeoTIFF mosaic straight
from public AWS Open Data. That path is verified **bit-identical** to the OpenTopography COP30
product the earlier runs used (maximum absolute difference 0.0 m, 100 % of pixels identical;
`tests/test_cop30_cog.py`), so the OpenTopography API key is now optional rather than required. The
Mars side needs no download either: the global MOLA 463 m GeoTIFF is the only Mars input.

## Deploy

Static site. On Vercel, import this repo; `vercel.json` serves `site/index.html` at `/` and the
study viewer at `/study`. No build step required.

## License

MIT (`terratrace/LICENSE`). Source datasets (NASA PDS/MOLA, LRO/LOLA, MESSENGER, Dawn, ESA
Copernicus, USGS 3DEP, SRTM, NASADEM, JAXA ALOS) keep their own terms; cite them per the runbook
and `terratrace/scripts/make_references.py`.
