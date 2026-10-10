# TerraTrace

**Planetary Analog OS nucleus.** TerraTrace compares a Mars reference terrain unit
with candidate Earth terrain units at a declared common metric support, shows which
map-scale morphology transfers, states what cannot transfer, and emits a reproducible,
provenance-tracked study package.

!!! warning "Scope / claim firewall"
    Morphology screening only. TerraTrace does **not** estimate rover traversability,
    validate autonomy, establish geological equivalence, certify site access, or
    certify mission readiness. It is not NASA-endorsed.

## What it does

1. Loads real DEMs for one of **five reference bodies (Earth, Mars, Moon, Mercury,
   Ceres)** — Mars (MOLA), Moon (LRO LOLA LDEM), Mercury (MESSENGER), Ceres (Dawn HAMO),
   and Earth (Copernicus GLO-30 / USGS 3DEP) — the product for each AOI is chosen by a
   source **catalog** with spatial-coverage metadata, after a
   fail-fast **preflight** validates the bounding box and sizes the request (no network),
   and each fetched file gets a **QA profile** (valid / water / NaN fraction, relief).
2. Reprojects each AOI to its own **local azimuthal-equidistant metric grid** using the
   correct body (Mars sphere R=3,396,190 m; Moon sphere R=1,737,400 m; Mercury sphere
   R=2,439,400 m; Ceres sphere R=469,730 m; Earth WGS84).
3. Masks water/sentinel contamination and blocks units that are mostly flat/zero.
4. Computes map-scale descriptors: slope, local relief, detrended ruggedness, low-slope
   connectivity, aspect dispersion, hypsometric integral.
5. Compares distributions to the reference and ranks candidates by **Pareto dominance**
   (no composite score); returns a tie/indeterminate/blocked state when honest. A batch of
   candidates is ranked by a **Pareto frontier** (peeled non-dominated layers + a dominance
   matrix), so the result is a defensible shortlist rather than a single forced winner.
6. Attaches a transfer-gap ledger, a draft study protocol, and an evidence graph; writes
   a hashed study package, a self-contained viewer, and — on request — a citable Markdown
   or self-contained offline HTML report (which can embed an inline, pure-stdlib hillshade
   terrain preview).

## Quick start

```bash
pip install -r requirements.txt
python -m terratrace.cli --out artifacts        # synthetic, offline
python -m terratrace.build_viewer               # viewer/index.html
python tests/run_tests.py                        # 275 fixtures
```

Real data: see the repository `REAL-DATA-RUNBOOK.md`. The only key required is a free
OpenTopography API key (Mars MOLA needs none).

## Why it is credible

Validated at the level it claims, with an automatic degeneracy gate, a water-contamination
ablation, and a core-vs-extended robustness ablation that turns an over-confident
recommendation into an honest tie. Every catalog source carries an approximate 1-sigma
vertical accuracy that `errorprop.py` propagates into honest slope/relief/ruggedness
uncertainty (an optimistic lower bound under the independent-pixel assumption), and the whole
result renders to a single self-contained, offline HTML report with an inline hillshade
preview. See [Validation & ablations](VALIDATION.md).
