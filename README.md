# Planetary Analog OS — TerraTrace

**Mars ↔ Earth map-scale terrain-morphology transfer intelligence.**

This repository holds two things:

| Path | What it is |
|---|---|
| `terratrace/` | The working engine (Python): real MOLA + Copernicus DEMs → per-body reprojection → morphology features → Pareto decision → transfer-gap ledger → provenance + viewer. 46 tests. |
| `site/` | A 3D scroll-animated website telling the project story (deployed on Vercel). |

> **Scope / claim firewall.** TerraTrace screens terrain **morphology** between curated
> map products. It does **not** estimate rover traversability, validate autonomy,
> establish geological equivalence, certify site access, or certify mission readiness.
> It is not NASA-endorsed.

## Run the engine

```bash
cd terratrace
pip install -r requirements.txt            # core (NumPy only)
python tests/run_tests.py                   # 46 fixtures
python -m terratrace.cli --out artifacts    # synthetic study
python -m terratrace.build_viewer           # viewer/index.html
```

Real data (Mars MOLA + Copernicus GLO-30) runs on a networked machine — see
`terratrace/REAL-DATA-RUNBOOK.md`. The large DEMs under `terratrace/data/` are
git-ignored; regenerate them with `scripts/fetch_real_dems.py`.

## The headline result

On real data (Mars reference vs a Nevada desert and Craters of the Moon, Idaho),
the four **core** morphology axes recommend the lava field, but adding the two
**extended** descriptors (aspect dispersion, hypsometric integral) turns the result
into an honest **tie** — the "best analog" depends on what you intend to test. The
tool reports that rather than forcing a winner. See `terratrace/docs/VALIDATION.md`.

## Deploy

Static site. On Vercel, import this repo; `vercel.json` serves `site/index.html` at `/`
and the study viewer at `/study`. No build step required.

## License

MIT (`terratrace/LICENSE`). Source datasets (NASA PDS/MOLA, ESA Copernicus, USGS)
keep their own terms; cite them per the runbook.
