# TerraTrace — Project Brief for Strategic Review

> **⚠ INTERNAL WORKING BRIEF — not the submission, and not the current public statement.**
> This is a strategic brief written for our own review. For the project as it actually ships, read the
> root [`README.md`](README.md), [`terratrace/docs/index.md`](terratrace/docs/index.md), and above all
> [`terratrace/docs/RESULTS-v3.md`](terratrace/docs/RESULTS-v3.md). Sections below are kept as written
> with dated supersede notes; where a number here disagrees with the README, **the README is current**.

> **Purpose of this document.** A complete, honest briefing on our NASA Space Apps 2026 project so a
> senior reviewer can judge it and suggest how to push it to the next level. It states what the
> project is, the problem it solves, how it works, what is built, what the real result is, where it is
> weak, and what we are considering next. Nothing here is inflated — the credibility of the project
> rests on rigor and honest claims, so this brief is written the same way.

**Snapshot (as of 2026-10-12 — see the note above; the numbers below have since moved)**

| | |
|---|---|
| Project | **TerraTrace** — reproducible, uncertainty-aware, multi-lens morphological analog screening across five worlds |
| Repo | `github.com/pal-123456789/terratrace` · HEAD `b31a547` at the time of writing · **CI green** on Python 3.10/3.11/3.12 |
| Scale | 5 planetary bodies · 40 descriptor families · 6 decision lenses · **686 → 876** tests across the arc · **51** validation oracles · **27** method citations |
| Engine | Pure-NumPy core (no SciPy/rasterio needed offline); dependency-free test runner |
| Status | Engine deep and green; the exploratory real-data finding was withdrawn and its mechanism measured under protocol v3 — see `terratrace/docs/RESULTS-v3.md`; positioned as public research / prior art |

---

## 1. The hackathon

**NASA Space Apps Challenge 2026** is NASA's annual global hackathon, held **November 14–15, 2026**
(48 hours, hundreds of host cities). NASA publishes a set of **14 official challenges** written by its
subject-matter experts, spanning Earth science, planetary science, AI, data visualization,
storytelling, games, and design; teams pick one and build with open NASA data over the weekend.

**One rule that shapes our strategy:** the *submitted* solution is meant to be built **during** the
event. Because we are building now (weeks ahead), this repository is framed as a **public research
project / prior art** (open source), not an official submission unless it is rebuilt or substantially
extended during the event window. This is deliberate and stated openly in the repo.

**Challenge mapping (closed 2026-11-13):** TerraTrace is pinned to the 2026 challenge recorded in the
project's master plan (`PLANETARY-ANALOG-OS-MASTER-PLAN.md` — kept locally and deliberately **not**
published in this repository) — *“Identify Earth Locations that Analog the Permanent Moon Base
Locations and Mars”* — now stated in the README and in
[`terratrace/docs/event/eligibility-evidence.md`](terratrace/docs/event/eligibility-evidence.md). The
official site confirms 14 challenges for 2026 but renders its list client-side, so the exact wording
should be re-confirmed against the official page at the event. The project also supports a Moon
reference, so the Moon half of the challenge is covered by the engine.

## 2. The problem statement we chose

**Planetary analog site selection is done by expert judgment and reported as a single qualitative
verdict** ("X is a good Earth analog for Y"), usually without a defined spatial scale, an uncertainty,
or a procedure anyone else can re-run. Analogs underpin instrument testing, operational rehearsal, and
the interpretation of orbital data, so this informality is a real gap.

**Our problem statement:** *make planetary-terrain analog screening quantitative, reproducible, and
honest* — compare a planetary reference terrain to candidate Earth terrains at a declared common
scale, on each body's correct geometry, and say defensibly **what transfers, at what scale, and with
what confidence** — without inventing a false precision.

## 3. What TerraTrace is

TerraTrace brings a planetary reference terrain and candidate Earth terrains to a **common metric
support** on each body's own geometry, computes a large battery of **map-scale morphology
descriptors**, and ranks candidates by **Pareto dominance across several independent descriptor
"lenses"** — deliberately refusing to collapse the comparison into one composite "likeness" score.
When the lenses disagree it returns an explicit **TIE / INDETERMINATE** state instead of inventing a
winner, and attaches a spatial bootstrap, a permutation significance test, a non-composite
decision-confidence verdict, and a full provenance record to every result.

> **Scope / claim firewall (load-bearing).** TerraTrace screens terrain *morphology* between curated
> map products. It does **not** estimate rover traversability, validate autonomy, establish geological
> equivalence, certify site access, or certify mission readiness. Earth sites are *illustrative
> analogs*, not endorsed field sites. It is not NASA-endorsed. This boundary is printed in every report
> and is the reason the method is credible rather than hype.

## 4. How it works (method pipeline)

1. **Common support & per-body reprojection.** Each area of interest is warped to its own local
   azimuthal-equidistant metric grid using the correct body radius (Mars 3,396,190 m; Moon 1,737,400 m;
   Mercury 2,439,400 m; Ceres 469,730 m; Earth WGS84) and aggregated to a declared common support
   (e.g. 1000 m), so descriptors compare like with like rather than conflating pixel size with terrain.
2. **Morphology descriptors.** 40 families (see §5), each a cited geomorphometry method implemented in
   pure NumPy; distributions compared to the reference with scale-normalized Wasserstein/KS distances.
3. **Decision = Pareto, not a score.** Candidates become vectors of distances-to-reference and are
   ranked by Pareto dominance (peeled non-dominated layers + a dominance matrix). The result is one of
   `RECOMMEND_FOLLOW_UP`, `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, or `BLOCKED`. **Six lenses** (core /
   extended / geomorphic / landform / texture / hydro) are **distinct** axis sets, all built on the
   four core bulk metrics; a recommendation that
   holds under more lenses is more robust, and lens disagreement is surfaced, not hidden.
4. **Uncertainty, significance, confidence.** A spatial moving-block bootstrap gives
   autocorrelation-aware distance intervals and a non-domination frequency; a one-sided permutation test
   asks whether the recommended unit is genuinely closer than the runner-up; and a **non-composite
   decision-confidence** verdict (`robust` / `qualified` / `fragile` / …) restates the bootstrap,
   significance, and lens-stability evidence as independent signals, naming any signal it could not
   evaluate.
5. **Provenance & reproducibility.** Every study is sha256 hash-anchored, carries an evidence graph and
   a transfer-gap ledger, and exports a self-contained bundle (study JSON, Markdown + offline HTML
   report, viewer, references, checksums, confidence). A fixed synthetic study is byte-reproducible
   within an environment and gated by portable invariants across platforms.

## 5. What is built (capability inventory)

**Descriptor battery (40 families, 27 cited):**
- *Core:* slope, local relief, detrended ruggedness, low-slope connectivity.
- *Extended:* aspect dispersion, hypsometric integral, TPI dispersion.
- *Geomorphic:* Zevenbergen–Thorne profile/plan/mean curvature, Vector Ruggedness Measure.
- *Landform / line-of-sight:* geomorphons (Jasiewicz & Stepinski 2013), topographic openness (Yokoyama 2002), openness-difference slope position.
- *Scale & fabric:* radially-averaged 2-D power-spectral slope (Perron 2008), directional structure-function anisotropy, geostatistical semivariogram (Matheron 1963), RMS/Allan-deviation roughness length (Shepard 2001), Woodcock (1977) normal-orientation fabric.
- *Planetary roughness / classification:* Kreslavsky–Head (2000) differential-slope baseline roughness (the metric behind NASA's MOLA roughness maps), Iwahashi–Pike (2007) three-signature terrain class.
- *Dissection / hydro-geometric:* D8 flow-accumulation dissection, Flint (1974) slope–area concavity, Topographic Wetness Index (Beven & Kirkby 1979), convergence index.
- *Texture / complexity:* Haar wavelet multiscale energy (Mallat 1989), differential box-counting fractal dimension, gliding-box lacunarity, Shannon entropy, surface-normal dispersion roughness.
- *Position / relief:* Weiss (2001) single- and two-scale TPI landform classes, Wood (1996) curvature feature classes, Strahler (1952) hypsometric curve, Melton (1965) ruggedness number.

**Decision & statistics:** 6 Pareto lenses; paired + spatial block bootstrap; permutation significance; non-composite decision confidence; sensitivity (lens/support ablation); terrain fingerprint + similarity search (opt-in geostatistical term).

**Interfaces & tooling:** unified CLI (incl. new `bank`, `transect`); loopback-only HTTP API (incl. `POST /bank`, `/transect`); self-contained HTML report + offline interactive viewer; pure-stdlib hillshade/PNG encoder; one-command real-study orchestrator (preflight → fetch → study → confidence → bundle); multi-reference **analog atlas**; scale-resolved profile; swath/transect profiler.

**Data & ingest:** Mars **MOLA 463 m** (USGS Astrogeology, keyless); Earth **Copernicus GLO-30** — via OpenTopography (free key) **or keylessly** from the public AWS COG mosaic (`--source cog`, the matched-benchmark default). A source catalog of **15** products across the five bodies with coverage, licence, and 1-sigma vertical-accuracy metadata; a no-network preflight validates each bounding box, picks the covering product, and sizes the request before any download.

## 6. The real result (our headline finding)

> **Update 2026-10-16 — this section is superseded.** The finding below was exploratory. A
> pre-registered, footprint-matched, resolution-aware test (`terratrace/docs/RESULTS-v2.md`) found it
> does **not** survive: H1 (held-out plains) not supported, the engine abstains in the honest regime,
> and Craters is nearest for a cratered highland as readily as for volcanic plains — a non-specific
> shortlist effect. The headline became that TerraTrace **caught its own false analog** with rules
> fixed before the data were seen.
>
> **Update 2026-11-05 — the explanation was then measured, not asserted.** Protocol v3
> (`terratrace/docs/BENCHMARK-PROTOCOL-v3.md` → `RESULTS-v3.md`) added two smoothness-matched
> **non-volcanic** Earth controls, 60 km windows, and three fresh confirmatory plains plus two fresh
> highlands. The frozen rules returned **S supported / V not supported / R supported**: a smooth
> **non-volcanic** terrain sits on the Pareto front for every confirmatory Martian volcanic plain at
> every honest support, while basaltic origin confers no advantage (the basalts come to the front only
> for the *rough* highlands). So the nearest Earth analog tracks **km-scale roughness, not volcanic
> origin**. 15/15 confirmatory honest cells were in-regime, 0 comparability-gate violations. One
> honest caveat: v3 is *pre-specified but not fully pre-registered* (rules and config frozen before the
> data; the protocol document committed after the run).
>
> The original exploratory text is kept below as history.

On a **real five-world run** — Mars MOLA 463 m vs three real Copernicus GLO-30 Earth terrains (Nevada
basin, Craters of the Moon ID, Andean volcano) at 1000 m common support — the method **independently
re-identifies a documented basalt analog, Craters of the Moon, Idaho**, as the closest match on the
core roughness/relief axes, *without being told to*. Honest nuance, surfaced not hidden:

- The best analog is **lens-conditional.** Under core (raw roughness/relief/ruggedness) and geomorphic
  (curvature/vector-ruggedness) lenses, Craters of the Moon is the decisive recommendation; under the
  extended lens (aspect/hypsometry) the Nevada basin matches Mars better and even shares its ~45° fabric,
  turning the decision into an honest **TIE**; the landform lens cannot separate the three.
- **Corroboration at scale.** Running the one-command atlas over four Mars terrains (Jezero, Gale,
  Daedalia Planum, Elysium Planitia) × the three Earth candidates (16 reference×lens cells), Craters of
  the Moon is Pareto non-dominated in **every** cell — the sole consensus analog — and is the *decisive*
  recommendation for the volcanic plains, while the crater floors tie more often (no clean crater-floor
  analog among the three). The engine points confidently where morphology agrees and abstains where it
  does not.
- **Stated transfer gap.** The Mars window (~10°) and the Earth windows (~0.4°) differ in footprint by
  ~15×, so the worked example mixes regional Mars structure with local Earth structure — a real gap the
  ledger flags (fix: comparable-footprint AOIs).

## 7. Validation & reproducibility

- **876 automated tests**, 0 failing, pure-NumPy, offline, via a dependency-free runner.
- **51 scientific-correctness oracles** drive the real engine on synthetic terrains with known answers:
  self-distance zero; slope/relief/ruggedness invariant to vertical offset and 90° rotation; monotone
  roughness discrimination; a planted close twin recovered over an impostor; a water tile BLOCKED;
  openness 90° on a plane and >90° at a peak; geomorphons label a cone apex a peak; a sinusoid's spectral
  peak lands at its wavelength; white noise spectrally flat (Parseval holds); correct fabric orientation;
  plus analytic oracles for every new descriptor.
- **CI** runs the suite + the oracles on Python 3.10/3.11/3.12 each push.
- **Gated determinism:** the default synthetic study `package_hash = 8f4890777ee462a2…` stays
  byte-identical in-environment; every opt-in feature (all 6 lenses, significance, previews, the whole
  descriptor bank) leaves it unchanged — proven, so new capability cannot silently alter the decision.

## 8. Progress & what we have done

The engine started as a Mars-vs-Earth 4-metric comparator and has been hardened one capability area at
a time, each increment cited, tested, gated, and pushed green. Recent arc:

- **Data & provenance:** source catalog + coverage/licence/accuracy metadata, no-network preflight,
  idempotent fetch cache + checksums, DEM QA profiler.
- **Science depth:** grew from 4 to roughly thirty descriptor families (11+ literature methods added in a dedicated
  research loop), 2 → 6 decision lenses, spatial bootstrap, permutation significance, non-composite
  confidence, co-registration + vertical-datum metadata.
- **Multi-world & scale:** 5 bodies; multi-reference analog atlas; scale-resolved analog profile.
- **Interfaces:** unified CLI, loopback API, HTML report + offline viewer, one-command real-study
  orchestrator, publication-grade methods paper (`docs/PAPER.md` → typeset PDF).
- **Last three pushes (Day 26–29):** `c3e016b` five-lens atlas/ablation; `84ac241` descriptor batch (wetness,
  convergence, sky-view factor, two-scale TPI); `b31a547` finale (semivariogram, roughness-length,
  curvature classes, normal-fabric eigen-analysis, openness-difference, Melton ruggedness, a swath
  transect tool, a 6th "hydro" decision lens, `bank`/`transect` CLI+API, and a geostatistical fingerprint
  term). Suite 583 → **686** tests across these, gated hash unchanged throughout.
- **Then the research arc (2026-10-16 → 2026-11-05):** a matched-footprint benchmark harness (spatial
  support vs extent, a comparability gate, resolution matching, specificity controls); protocol **v2**
  (frozen *before* any v2 data — it withdrew the Craters claim); engine extensions (adversarial
  robustness, absolute adequacy, per-class confirmation rules, and the `classify_resolution_change` fix
  that separates stabilisation from reversal); and protocol **v3** (S supported / V not supported /
  R supported). Plus a **keyless** Copernicus GLO-30 COG Earth path proven **bit-identical** to
  OpenTopography, and CI hygiene that actually **runs** the tests with optional dependencies blocked.
  Suite 686 → **843**; validation 51/51 throughout; gated study hash unchanged.

## 9. Honest limitations & transfer gaps (stated, not hidden)

- **Morphology only.** Says nothing about composition, rock-scale obstacles below the pixel,
  trafficability, or mission suitability — reproduced verbatim in every report.
- **Footprint mismatch** in the worked example (~15×) mixes regional Mars with local Earth structure.
- **Bootstrap optimism:** the independent-pixel interval is optimistic relative to the spatial block
  bootstrap on autocorrelated terrain.
- **Faithful-but-adapted methods:** the geomorphon 10-form reduction is our own explicit *antisymmetric*
  rule (validated, not a verbatim GRASS lookup — we could not fetch the authoritative table offline and
  refused to fake byte-identity); curvature feature classes use principal curvatures because the engine's
  profile/plan curvature vanish at flat extrema. Both documented.
- **Some descriptor overlap** (e.g. variogram range vs autocorrelation length; roughness-length vs
  structure function) — distinct, cited outputs, but a reviewer may reasonably ask which are load-bearing.
- **Event rule:** this repo is prior art unless rebuilt/extended during the Nov 14–15 window; not
  NASA-endorsed.

## 10. What we are considering next

> **Status 2026-11-13.** Two of these were since acted on: the real evidence was strengthened by the
> matched-footprint **v2/v3** benchmark (bounded, comparable 60 km units; support ≥ effective
> resolution; abstention under the honest regime), and the keyless COG path removed the download/key
> blocker entirely. Still open: wiring `hydro` into the atlas/ablation *defaults* (it remains opt-in by
> design, so the gated hash is untouched), and propagating co-registration/vertical-datum error
> end-to-end into the decision.
>
> **The challenge title is no longer open** — the master plan (header line) names it: *“Identify Earth
> Locations that Analog the Permanent Moon Base Locations and Mars”*. It is now recorded in the README
> and in [`docs/event/eligibility-evidence.md`](terratrace/docs/event/eligibility-evidence.md), with
> one honest qualification: the official 2026 site confirms 14 challenges but its list is
> client-rendered behind a GraphQL API, so the wording should be re-confirmed at the event.
>
> Every requirement in the master plan, its 23-module library, and the S/E/U backlog has now been
> traced item by item in [`terratrace/docs/PLAN-COMPLIANCE.md`](terratrace/docs/PLAN-COMPLIANCE.md),
> which also names the six items that are genuinely not delivered.

- **Make the new science matter to the decision & the demo:** wire the `hydro` lens into the atlas/
  ablation defaults; add a report/viewer panel that visualizes the new descriptors + a transect figure.
- **Strengthen the real evidence (highest leverage):** widen the real atlas with more Earth candidates
  (Hawaii, Iceland, Atacama, Devon Island) and tighten the Mars AOI to a comparable footprint for an
  airtight, apples-to-apples comparison. (Downloads run on our own machine; sandbox has no network.)
- **Deeper rigor:** propagate DEM co-registration + vertical-datum error end-to-end into the decision;
  replace the optimistic independent-pixel interval everywhere with the block bootstrap.
- **Positioning:** map TerraTrace to the best-fitting official 2026 challenge; produce a one-page judge
  brief + a short narrated demo; keep the methods paper current.

## 11. Questions we want the senior reviewer to answer

*(Kept for the record. The ones we could answer from our own evidence we did, rather than waiting —
see `terratrace/docs/RESULTS-v2.md` and `RESULTS-v3.md`.)*

1. **Thesis:** Is "no composite likeness score — Pareto dominance + explicit TIE/INDETERMINATE + honest
   confidence" the right differentiator for a NASA-judged audience, or should we *also* offer a defensible
   composite (clearly labeled) because judges like a single answer? What is the strongest version of our
   stance?
2. **Focus vs breadth:** ~30 descriptors is comprehensive but risks reading as padding. Which families are
   genuinely load-bearing for the analog decision, and what should we prune or consolidate?
3. **Single highest-leverage move:** With ~1 month to the event, what one addition most increases
   credibility with expert judges — more real worlds/sites, a sharper worked result, co-registration rigor,
   a specific visualization, or a scientific validation against an external ground truth?
4. **Making the result airtight:** Best way to close the footprint-mismatch and co-registration gaps so the
   Craters-of-the-Moon finding is unimpeachable?
5. **Lenses:** Is six decision lenses clarifying or confusing? Should any merge, and how should we present
   lens-robustness to a non-specialist judge?
6. **Demo:** What single interactive artifact or figure would land best in a 2-minute judging window?
7. **Novelty check:** Where does this sit relative to existing planetary-GIS / geomorphometry tooling —
   what is genuinely new, and what claim of novelty is defensible?

---

*Scope / claim firewall: map-scale terrain-morphology screening and resampling statistics only — not a
traversability, geologic-equivalence, site-access, or mission-readiness claim. Earth sites are
illustrative analogs. Not NASA-endorsed.*

**Sources (hackathon facts):** [NASA Space Apps 2026 — official](https://www.spaceappschallenge.org/resources/participant-faqs/) · [NASA: Prizes, Challenges & Crowdsourcing (Nov 14–15, 2026)](https://www.nasa.gov/prizes-challenges-and-crowdsourcing/) · [Space Apps 2026 overview — 14 challenges](https://www.therecursive.com/nasa-space-apps-challenge-2026-where-to-join-it-in-cee/)
