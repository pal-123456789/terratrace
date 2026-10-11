# TerraTrace: Reproducible, Uncertainty-Aware, Multi-Lens Morphological Analog Screening Across Five Worlds

**NASA Space Apps 2026 — research preview.** Repository: `github.com/pal-123456789/terratrace`

> **Scope / claim firewall.** TerraTrace screens terrain *morphology* between curated map
> products. It does **not** estimate rover traversability, validate autonomy, establish
> geological equivalence, certify site access, or certify mission readiness. Earth sites named
> here are *illustrative analogs*, not endorsed field sites. It is not NASA-endorsed.

## Abstract

Choosing a terrestrial analog for a planetary terrain is usually done by expert judgment and
reported as a single qualitative verdict. TerraTrace makes that screening **quantitative,
reproducible, and honest**. It brings a planetary reference terrain and candidate Earth
terrains to a common metric support on each body's own geometry, computes a battery of
map-scale morphology descriptors, and ranks candidates by **Pareto dominance across several
independent descriptor "lenses"** — deliberately refusing to collapse the comparison into one
composite "likeness" score. When lenses disagree it returns an explicit TIE / INDETERMINATE
state instead of inventing a winner, and attaches a spatial block-bootstrap, a permutation
significance test, a non-composite decision-confidence verdict, and a full provenance record to
every result. On a real five-world run (Mars MOLA vs three Copernicus GLO-30 Earth terrains)
the method independently re-identifies a documented basalt analog — Craters of the Moon, Idaho
— as the closest match on the core roughness/relief axes, while honestly reporting that the
recommendation does not survive every lens. Everything is offline-reproducible from one command
and covered by 522 automated tests.

## 1. Problem and approach

Analog site selection underpins instrument testing, operational rehearsal, and the
interpretation of orbital data. Yet "X is a good analog for Y" is rarely stated with a defined
support scale, an uncertainty, or a falsifiable procedure. TerraTrace treats analog screening as
a transparent, auditable computation with three commitments: (i) **comparison at a declared
common support** on each body's correct geometry; (ii) **no composite score** — candidates are
ranked by Pareto dominance over interpretable axes, and ties are reported, not broken; and
(iii) **every number carries provenance and uncertainty**. The goal is not to declare a winner
but to say, defensibly, *what transfers, at what scale, and with what confidence.*

## 2. Method

**2.1 Common support and per-body reprojection.** Each area of interest is warped to its own
local azimuthal-equidistant metric grid using the correct body radius (Mars 3,396,190 m; Moon
1,737,400 m; Mercury 2,439,400 m; Ceres 469,730 m; Earth WGS84) and aggregated to a declared
common support (e.g. 1000 m), so descriptors compare like with like rather than conflating
pixel size with terrain.

**2.2 Morphology descriptors.** Core: slope, local relief, detrended ruggedness, low-slope
connectivity. Extended: aspect dispersion, hypsometric integral. Geomorphic: Zevenbergen–Thorne
curvature and the Vector Ruggedness Measure. Landform: geomorphon landform composition and
topographic openness. Scale & fabric: the radially-averaged power-spectral slope and a
directional-structure-function anisotropy (fabric strength and orientation). Planetary
roughness: the Kreslavsky–Head (2000) differential-slope baseline roughness (the metric behind
NASA's global MOLA roughness maps) and the Iwahashi–Pike (2007) three-signature
(slope / convexity / texture) nested-means terrain class. Dissection: a depression-filled
D8 flow-accumulation surface-dissection texture (a purely geometric routing descriptor). Distributions are
compared to the reference with scale-normalized Wasserstein/KS distances.

**2.3 Decision: Pareto, not a score.** Candidates become vectors of distances-to-reference and
are ranked by **Pareto dominance** (peeled non-dominated layers + a dominance matrix). The
result is one of `RECOMMEND_FOLLOW_UP`, `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, or `BLOCKED`.
Four **lenses** — core, extended, geomorphic, landform — are independent axis sets; a
recommendation that holds under more lenses is more robust, and lens disagreement is surfaced,
not hidden.

**2.4 Uncertainty, significance, confidence.** A spatial moving-block bootstrap gives
autocorrelation-aware distance intervals and a non-domination frequency; a one-sided permutation
test asks whether the recommended unit is genuinely closer to the reference than the runner-up;
and a **non-composite decision-confidence** verdict (`robust` / `qualified` / `fragile` / …)
restates the bootstrap, significance, and lens-stability evidence as three independent signals,
explicitly naming any signal it could not evaluate.

**2.5 Provenance and reproducibility.** Every study is hash-anchored (sha256), carries an
evidence graph and a transfer-gap ledger, and exports a self-contained bundle (study package,
Markdown + offline-HTML report, viewer, references, checksums, confidence). A fixed synthetic
study is byte-reproducible within an environment; portable invariants (not pinned digests) gate
it across platforms.

## 3. Data

Mars reference: MGS **MOLA 463 m** (USGS Astrogeology, keyless). Earth candidates: **Copernicus
GLO-30** via OpenTopography. The engine's source catalog carries 13 products across the five
bodies with coverage, licence, and 1-sigma vertical-accuracy metadata; a no-network preflight
validates each bounding box, selects the covering product, and sizes the request before any
download.

## 4. Result: a real five-world screen

Mars MOLA versus three real Copernicus GLO-30 Earth terrains at 1000 m support. Distance to the
Mars reference per axis (lower = closer):

| candidate | slope | relief | ruggedness | connectivity | aspect | hypsometric |
|---|---|---|---|---|---|---|
| **Craters of the Moon, ID** | **0.75** | **0.78** | **0.76** | **0.018** | 0.39 | 0.28 |
| **Nevada basin** | 1.33 | 1.38 | 1.45 | 0.030 | **0.011** | **0.14** |
| Andean volcano | 1.73 | 1.50 | 1.85 | 0.057 | 0.012 | 0.17 |

Four-lens ablation on the **same** data (one command, `--ablation`):

| lens | result | recommended | non-dominated set |
|---|---|---|---|
| core | RECOMMEND | **Craters of the Moon** | {Craters} |
| extended | TIE | — | {Craters, Nevada} |
| geomorphic | RECOMMEND | **Craters of the Moon** | {Craters} |
| landform | TIE | — | {Craters, Nevada, Andes} |

**Reading.** On raw roughness/relief/ruggedness (core) and on curvature/vector-ruggedness
(geomorphic), Craters of the Moon is decisively the closest match — the method *independently
re-identifies a terrain already used as a basalt analog*. Adding aspect-dispersion and
hypsometric structure (extended), where the Nevada basin matches Mars better and even shares its
~45° fabric, turns the decision into an honest TIE; the landform lens cannot separate the three.
The defensible conclusion is therefore **lens-conditional**: *Craters of the Moon is the robust
analog for surface roughness and local shape; it is not uniquely best for directional/elevation
structure.* No single number could have said that honestly.

**Corroboration at scale.** Running the one-command atlas over four distinct Mars terrains
(Jezero and Gale crater floors; Daedalia Planum and Elysium Planitia volcanic plains) against the
same three Earth candidates under all four lenses (16 reference×lens cells) makes the result
sharper: Craters of the Moon is Pareto non-dominated in **every** cell — the sole consensus analog
— and is the *decisive* recommendation for the volcanic plains under three of four lenses, while
the crater floors tie more often (no clean crater-floor analog among the three). The engine points
confidently where the morphology agrees and abstains where it does not. See `REAL-EXAMPLE.md`.

## 5. Validation

Correctness is pinned by a scientific-correctness suite of 32 oracles that drive the real
engine on synthetic terrains with known answers: self-distance is zero; slope/relief/ruggedness
are invariant to a constant offset and to 90° rotation; roughness discrimination is monotone; a
planted close twin is recovered over an impostor; a water tile is BLOCKED; openness is 90° on a
plane and exceeds 90° at a peak; geomorphons label a cone apex a peak and a basin centre a pit;
a sinusoid's spectral peak lands at its wavelength; white noise is spectrally flat (Parseval
holds); a ridged surface reports the correct fabric orientation. The real-data run adds an
external check: the method re-identifies a documented basalt analog on the core axes without
being told to.

## 6. Limitations and transfer gaps (stated, not hidden)

TerraTrace compares *map-scale morphology of sampled DEMs* and nothing else. It says nothing
about composition, rock-scale obstacles below the pixel, trafficability, or mission suitability;
those bounds are reproduced verbatim in every report. Two concrete limits of the worked example:
the Mars window (~10°) and the Earth windows (~0.4°) differ in footprint by ~15×, so the screen
mixes regional Mars structure with local Earth structure (a transfer gap the ledger flags; the
fix is comparable-footprint AOIs); and the independent-pixel bootstrap is optimistic relative to
the spatial block bootstrap on autocorrelated terrain. Deferred work: DEM co-registration and
vertical-datum error propagation end-to-end into the decision, and a multi-pair "analog atlas."

## 7. Reproducibility

```bash
pip install -r terratrace/requirements.txt      # core: NumPy only
python terratrace/tests/run_tests.py             # 522 offline tests
python terratrace/scripts/run_validation.py      # 32 correctness oracles
# real five-world study, one command (needs a free OpenTopography key):
python terratrace/scripts/run_real_analog_study.py --config config/real_multibody.example.yml
```

CI runs the suite and the validation oracles on Python 3.10/3.11/3.12. Large DEMs and generated
bundles are git-ignored; everything else regenerates deterministically.

## References

Yokoyama, Shirasawa & Pike (2002), *Visualizing topography by openness*, PE&RS 68(3).
Jasiewicz & Stepinski (2013), *Geomorphons*, Geomorphology 182.
Perron, Kirchner & Dietrich (2008), *Spectral signatures of characteristic spatial scales*, JGR-ES 113.
Shepard et al. (2001), *The roughness of natural terrain*, JGR-Planets 106(E12).
Sappington et al. (2007), *Vector Ruggedness Measure*, J. Wildl. Manage. 71.
Riley, DeGloria & Elliot (1999), *Terrain Ruggedness Index*.
Zevenbergen & Thorne (1987), *Quantitative analysis of land surface topography*.
Efron & Tibshirani (1993), *An Introduction to the Bootstrap*. Good (2005), *Permutation, Parametric, and Bootstrap Tests of Hypotheses*.
Kreslavsky & Head (2000), *Kilometer-scale roughness of Mars: Results from MOLA data analysis*, JGR‑Planets 105(E11).
Iwahashi & Pike (2007), *Automated classifications of topography from DEMs by an unsupervised nested-means algorithm and a three-part geometric signature*, Geomorphology 86.
O'Callaghan & Mark (1984), *The extraction of drainage networks from digital elevation data*, CVGIP 28.
Barnes, Lehman & Mulla (2014), *Priority-flood: an optimal depression-filling and watershed-labeling algorithm*, Computers & Geosciences 62.
Horton (1945), *Erosional development of streams and their drainage basins*, GSA Bulletin 56.

*Morphology screening and resampling statistics only — not a traversability, geologic-equivalence, site-access, or mission-readiness claim.*

