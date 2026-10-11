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
7. On request, adds a **line-of-sight terrain-structure** layer: **topographic openness**
   (Yokoyama, Shirasawa & Pike 2002) and **geomorphon landform classification** (Jasiewicz &
   Stepinski 2013), both pure-NumPy. These power a fourth, opt-in `landform` decision lens —
   the four core axes plus a geomorphon-spectrum and a topographic-openness distance — and,
   when a study is run with `landform=True, previews=True`, a landform-composition table,
   openness medians, and categorical landform / grayscale openness map previews in the report
   and viewer. All of it is off by default, so the synthetic study package and its provenance
   hash are unchanged. These are map-scale morphology descriptors only — not traversability,
   hazard, geologic-unit identification, or mission readiness.
8. On request, attaches **statistical confidence for the analog decision** (opt-in, gated). A
   one-sided **permutation test** (`study.compare_units(..., significance=True, n_perm=1000)`)
   asks whether the recommended unit is genuinely closer to the reference than the **runner-up**
   (the second-closest candidate), computed per sample-based morphology metric (slope, relief,
   ruggedness) with the decision's own scales, returning per-metric one/two-sided p-values, an
   effect size, and a `recommendation_significant` flag — connectivity is a scalar and reported
   as such. `confidence.decision_confidence()` then restates the robustness evidence already in
   the study as **three independent signals** — bootstrap non-domination frequency, the
   permutation significance vs the runner-up, and lens/support stability — and returns a single
   categorical **verdict** (`robust` / `qualified` / `fragile` / `tie` / `indeterminate` /
   `blocked` / `not_comparable` / `unverified`) with a plain-language rationale and an explicit
   list of the signals that were **not** evaluated. There is no weighted score; a missing signal
   degrades to "not evaluated" rather than being invented. Both are off by default, so the frozen
   study package and its provenance hash are unchanged, and the HTML report and offline viewer
   render these only when a robustness signal was actually computed. This is distribution-shape
   resampling statistics and morphology screening only — never a traversability, hazard,
   geologic-equivalence, or mission-readiness claim.
9. On request, adds a **scale & fabric** layer: two pure-NumPy map-scale roughness descriptors.
   `spectral.py` computes a **radially-averaged 2-D power spectral density** (detrend the plane,
   Hann-window, FFT, radially average the periodogram over wavenumber) and reports the log-log
   **spectral slope** (how power is shared between long and short wavelengths), the **band
   roughness** (RMS amplitude in long/mid/short wavelength bands), the **peak wavelength**, and a
   total power that recovers the detrended variance by Parseval. `anisotropy.py` computes the
   **directional structure function** — the RMS elevation difference along a fan of azimuths — and
   reports an anisotropy **strength** (0 = isotropic, →1 = strongly lineated), the fabric
   **orientation** (azimuth of minimum roughness, the strike along which ridges or dunes run), and
   an isotropy ratio. Both are opt-in and gated: `study.compare_units(..., terrain_spectra=True)`
   (and `run_real_study(terrain_spectra=True)`) attach `package["spectral"]` and
   `package["anisotropy"]` per compared unit, the HTML report and offline viewer render a "Scale &
   fabric" section when present, and `descriptor_bank` and the terrain `fingerprint` gained opt-in
   spectral/anisotropy terms — all off by default, so the synthetic study package and its
   provenance hash are unchanged (Perron, Kirchner & Dietrich 2008; Shepard et al. 2001). These
   summarise the sampled DEM's roughness spectrum and directional structure only — not a
   traversability, hazard, geologic, or mission-readiness claim, and they say nothing about
   rock-scale obstacles below the pixel.

## Quick start

```bash
pip install -r requirements.txt
python -m terratrace.cli --out artifacts        # synthetic, offline
python -m terratrace.build_viewer               # viewer/index.html
python tests/run_tests.py                        # 613 fixtures
```

Real data: see the repository `REAL-DATA-RUNBOOK.md`. The only key required is a free
OpenTopography API key (Mars MOLA needs none).

## Why it is credible

Validated at the level it claims, with an automatic degeneracy gate, a water-contamination
ablation, and a core-vs-extended robustness ablation that turns an over-confident
recommendation into an honest tie. A **sensitivity ablation** goes further, reporting whether the
recommendation stays stable across all three decision lenses and a sweep of common supports.
Every catalog source carries an approximate 1-sigma vertical accuracy that `errorprop.py`
propagates into honest slope/relief/ruggedness uncertainty (an optimistic lower bound under the
independent-pixel assumption); on request the study carries those **per-source
measurement-uncertainty bands** and **inline hillshade previews**, and the whole result renders to
a single self-contained, offline HTML report (and viewer) that shows them. See
[Validation & ablations](VALIDATION.md).
