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
every result. In exploratory runs on real data (Mars MOLA vs three Copernicus GLO-30 Earth
terrains) the method favoured a documented basalt analog — Craters of the Moon, Idaho — on the
core roughness/relief axes. A **pre-registered** follow-up then tested that preference under
matched physical footprints, supports at or above MOLA's effective resolution, three held-out
Martian volcanic plains, and two contrast terrains. **The preference did not survive:** in the
honest regime the engine abstained for all seven Mars references, and Craters was the nearest
candidate for a cratered highland as readily as for volcanic plains — the signature of a
non-specific "least-dissimilar member of a weak shortlist" effect rather than a specific analog.
TerraTrace's contribution is therefore a screening method that **detects its own false analogs**
with rules fixed before the data are seen. Everything is offline-reproducible from one command
and covered by 884 automated tests.

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
D8 flow-accumulation surface-dissection texture (a purely geometric routing descriptor). The
bank also carries a Haar wavelet multiscale-energy spectrum, the Strahler hypsometric curve,
surface-normal-dispersion roughness, and a Weiss (2001) TPI slope-position classification. A Topographic Wetness Index (Beven & Kirkby 1979) and a convergence index (Köthe & Lehmeier 1996) summarise flow-geometric convergence; a sky-view factor (Zakšek et al. 2011) captures hemispherical openness; and a two-scale TPI slope-position classification (Weiss 2001) resolves nested landform position. Finally
a differential box-counting fractal dimension, gliding-box lacunarity, Shannon terrain entropy,
and a Flint (1974) slope-vs-contributing-area concavity complete the battery. A geostatistical semivariogram (range/sill/nugget; Matheron 1963) and an RMS/Allan-deviation roughness length (Shepard et al. 2001) summarise spatial structure; Wood (1996) morphometric curvature classes and a Woodcock (1977) surface-normal orientation-tensor fabric add shape descriptors; an openness-difference slope position (Yokoyama 2002) and the Melton (1965) ruggedness number complete the batch. Distributions are
compared to the reference with scale-normalized Wasserstein/KS distances.

**2.3 Decision: Pareto, not a score.** Candidates become vectors of distances-to-reference and
are ranked by **Pareto dominance** (peeled non-dominated layers + a dominance matrix). The
result is one of `RECOMMEND_FOLLOW_UP`, `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, or `BLOCKED`.
Six **lenses** — core, extended, geomorphic, landform, texture, hydro — are **distinct but
correlated** axis sets, each containing the four core bulk metrics and adding to them, so
agreement between lenses is a robustness read rather than an independent replication (the hydro lens adds a Topographic Wetness Index, aspect convergence, and flow-dissection distance-to-reference axes); a
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
it across platforms. The full geomorphometric descriptor bank and a swath/profile `transect`
extractor are reachable from the unified CLI (`bank`, `transect`) and the loopback-only HTTP API
(`POST /bank`, `POST /transect`, the same host-allowlist and body-cap guards as the existing
endpoints), and the terrain fingerprint carries an opt-in geostatistical similarity term
(`include_geostat`).

## 3. Data

Mars reference: MGS **MOLA 463 m** (USGS Astrogeology, keyless). Earth candidates: **Copernicus
GLO-30**, read either via OpenTopography or keylessly from the public AWS COG mosaic (§4.2). The
engine's source catalog carries 15 products across the five
bodies with coverage, licence, and 1-sigma vertical-accuracy metadata; a no-network preflight
validates each bounding box, selects the covering product, and sizes the request before any
download.

## 4. Results: an exploratory screen, then a pre-registered test

### 4.1 Exploratory screen (not controlled — retained as history)

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

**Exploratory reading (superseded by 4.2).** On the core and geomorphic lenses Craters of the
Moon was the closest of the three candidates, which looked like an independent re-identification
of a known basalt analog; the extended and landform lenses tied. Running the one-command atlas over
four Mars terrains (Jezero, Gale, Daedalia Planum, Elysium Planitia) kept Craters non-dominated in
all 16 reference×lens cells. These runs, however, compared a ~10° Mars window with ~0.4° Earth
windows and used supports below MOLA's effective resolution, so they were treated as a
**hypothesis to test**, not a result.

### 4.2 Pre-registered matched-footprint test (protocol v2)

The hypothesis was tested under a protocol frozen and committed before the runner existed
(`docs/BENCHMARK-PROTOCOL-v2.md`): every unit cropped to the same untruncated 24 km window;
evidence only at supports ≥ MOLA's effective resolution (1.5 and 2 km); three held-out Martian
volcanic plains (Amazonis, Syria, Hesperia) as confirmation; two contrast terrains (Noachis Terra
highland, Coprates Chasma canyon) as a specificity control; a resolution-matching control; and an
absolute-adequacy check against each reference's own variability.

| hypothesis | frozen verdict |
|---|---|
| H1 — held-out plains recommend Craters | **not supported** (0 of 3) |
| H2 — Craters not chosen for contrast terrains | inconclusive (no honest-regime recommendation anywhere) |
| H3 — not a source-smoothing artifact | not supported (primary changed under resolution matching) |
| H4 — absolute adequacy | reported (no recommended unit) |

**Reading.** In the honest regime the engine abstained for all seven references. Craters was
nonetheless the nearest candidate in 11 of 14 cells — **including the cratered highland Noachis
Terra** — and under resolution matching it became the stable recommendation in those same cells,
with the engine's own specificity verdict `non_specific`. It also fell outside the own variability
of Daedalia and Elysium, the two plains the exploratory claim was built on. The most economical
explanation is a shortlist effect: at kilometre scale Martian terrain is smoother than all three
Earth tiles, and Craters is simply the smoothest of them. The exploratory analog claim is
therefore **withdrawn**; full results, including the non-pre-registered descriptive analyses and a
protocol-design lesson, are in `docs/RESULTS-v2.md`.

**The shortlist explanation was then tested directly (protocol v3).** With two smoothness-matched
**non-volcanic** controls (Nullarbor limestone, σ ≈ 5 m; Llano Estacado sedimentary plain, σ ≈ 14 m),
60 km windows for power, and three fresh confirmatory volcanic plains plus two fresh cratered
highlands, the frozen v3 rules returned **S — supported**: a smooth non-volcanic terrain sits on the
Pareto front for *every* confirmatory Martian volcanic plain at *every* honest support (3 of 3). And
**V — not supported**: the pre-declared volcanic-specific dominance advantage was **not established**,
since no basaltic candidate dominated the smooth controls for plains, while the basalts *did* come to
the front for the rough highlands. Resolution robustness held in the narrow sense the rule supports —
**no outright candidate reversal** among 15 confirmatory honest cells (11 unchanged, 3 membership
changes and 1 destabilisation, correctly distinguished from reversal). Within this panel and lens the
nearest Earth analog tracked **km-scale roughness rather than volcanic origin**: the withdrawn Craters
preference is explained, and the explanation is measured rather than inferred.

*Scope, carried with the result rather than qualified after it.* The confirmatory verdicts rest on
three volcanic-plains and two highland references, seven Earth candidates, honest supports of
1500/2000/3000 m, and the **core decision lens**. That is a small, spatially dependent sample; the
single top-of-shortlist pick is a near-tie that reverses under a six-pixel crop-origin shift; and no
independent researcher has replicated the panel. The additional lenses are alternative analytical
views of the same terrains — they are **not** independent replications. One further caveat is recorded
with the result: v3 is *pre-specified but not fully pre-registered* (the rules and config were fixed
before the data were read, but the protocol document was committed after the run). See
`docs/RESULTS-v3.md`, `docs/V3-ARCHIVAL-CLARIFICATION.md` and `docs/BENCHMARK-PROTOCOL-v3.md`.

**Data access.** Earth elevations are read from the **public ESA Copernicus GLO-30 COG mosaic** on
AWS, with no API key; that path is verified bit-identical to the OpenTopography COP30 product
(maximum absolute difference 0.0 m), so the keyed service is optional rather than required.

## 5. Validation

Correctness is pinned by a scientific-correctness suite of 51 oracles that drive the real
engine on synthetic terrains with known answers: self-distance is zero; slope/relief/ruggedness
are invariant to a constant offset and to 90° rotation; roughness discrimination is monotone; a
planted close twin is recovered over an impostor; a water tile is BLOCKED; openness is 90° on a
plane and exceeds 90° at a peak; geomorphons label a cone apex a peak and a basin centre a pit;
a sinusoid's spectral peak lands at its wavelength; white noise is spectrally flat (Parseval
holds); a ridged surface reports the correct fabric orientation. Separate synthetic ground truths
validate the comparison controls themselves: a footprint mismatch that flips the recommended
analog is detected and corrected; a source-smoothing false analog is removed by resolution
matching; and a non-specific "wins everywhere" candidate is distinguished from a specific one.
Passing these tests establishes software and method correctness, not a scientific discovery —
the real-data hypothesis test is reported separately in §4.2.

## 6. Limitations and transfer gaps (stated, not hidden)

TerraTrace compares *map-scale morphology of sampled DEMs* and nothing else. It says nothing
about composition, rock-scale obstacles below the pixel, trafficability, or mission suitability;
those bounds are reproduced verbatim in every report. Two concrete limits of the exploratory
example (§4.1): the Mars window (~10°) and the Earth windows (~0.4°) differed in footprint by ~15×,
and supports below MOLA's effective resolution compared interpolated Mars detail with real Earth
detail — both corrected in the pre-registered test of §4.2. That test is itself limited: 12–16
cells per side at 24 km, one source per body (not independent replications), a 3× effective-
resolution heuristic rather than a measured MOLA transfer function, and only three Earth
candidates. The independent-pixel bootstrap is optimistic relative to the spatial block bootstrap
on autocorrelated terrain. Deferred work: DEM co-registration and vertical-datum error propagation
end-to-end into the decision; wider Earth windows and smoothness-matched controls (protocol v3).

## 7. Reproducibility

```bash
pip install -r terratrace/requirements.txt      # core: NumPy only
python terratrace/tests/run_tests.py             # 884 offline tests
python terratrace/scripts/run_validation.py      # 51 correctness oracles
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
Mallat (1989), *A theory for multiresolution signal decomposition*, IEEE PAMI 11.
Strahler (1952), *Hypsometric (area-altitude) analysis of erosional topography*, GSA Bulletin 63.
Hobson (1972), *Surface roughness in topography*; McKean & Roering (2004), *Objective landslide detection and surface morphology mapping*, Geomorphology 57.
Weiss (2001), *Topographic position and landforms analysis*.
Sarkar & Chaudhuri (1994), *An efficient differential box-counting approach to compute fractal dimension of images*, IEEE SMC 24.
Plotnick, Gardner & O'Neill (1993), *Lacunarity indices as measures of landscape texture*, Landscape Ecology 8.
Shannon (1948), *A mathematical theory of communication*, Bell System Technical Journal 27.
Flint (1974), *Stream gradient as a function of order, magnitude, and discharge*, Water Resources Research 10.
Beven & Kirkby (1979), *A physically based, variable contributing area model of basin hydrology*, Hydrological Sciences Bulletin 24(1).
Köthe & Lehmeier (1996), *SARA: System zur automatischen Relief-Analyse* (convergence index); see also Kiss (2004), *Determination of drainage network in digital elevation models, utilities and limitations*, J. Hungarian Geomathematics 2.
Zakšek, Oštir & Kokalj (2011), *Sky-view factor as a relief visualization technique*, Remote Sensing 3(2).
Matheron (1963), *Principles of geostatistics*, Economic Geology 58(8).
Wood (1996), *The geomorphological characterisation of digital elevation models*, PhD thesis, University of Leicester; Dikau (1989), *The application of a digital relief model to landform analysis in geomorphology*, in Three-Dimensional Applications in Geographic Information Systems.
Woodcock (1977), *Specification of fabric shapes using an eigenvalue method*, Geological Society of America Bulletin 88(9).
Melton (1965), *The geomorphic and paleoclimatic significance of alluvial deposits in southern Arizona*, The Journal of Geology 73(1); Pike & Wilson (1971), *Elevation-relief ratio, hypsometric integral, and geomorphic area-altitude analysis*, Geological Society of America Bulletin 82(4).

*Morphology screening and resampling statistics only — not a traversability, geologic-equivalence, site-access, or mission-readiness claim.*

