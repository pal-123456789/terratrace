# TerraTrace Benchmark — Protocol v3 (FROZEN, with a recorded qualification)

**Frozen 2026-11-05.** Supersedes the proposal `BENCHMARK-PROTOCOL-v3-PROPOSAL.md`
(2026-10-16). The decision rules, candidate classes, reference classes and stopping
rule below are fixed and were NOT edited after any v3 result was produced.

## READ THIS FIRST — an honest qualification on the freeze

In v2 the protocol was committed **before** the run, on its own, and that is the
standard this project holds itself to. **For v3 that ordering was not achieved.**
What actually happened, in order:

1. The v3 **decision rules** (`terratrace/panel_v3.py`: S, V, R, the
   resolution-change classifier, the comparability gate) were written and committed
   on 2026-10-16 in `60c7d63` and `d04faa5` — **before any v3 data existed**.
2. The v3 **config** (`config/matched_footprint_v3.yml`: the reference set, the
   candidate classes, the predeclared S and V expectations, the supports) was
   written at 19:55:05 on 2026-11-05 — **before any Earth tile was fetched**
   (first tile written 19:55:58) and **708 s before the result bundle**
   (20:06:54).
3. The **referenced coordinate/class verification** was performed independently
   against the IAU Gazetteer before freezing (see below).
4. The **run was executed**, and only then was this document committed.

So: **the rules and the config were fixed before the data was read, and the file
hashes prove the config and rule code are unmodified since** — but the protocol
*document* was committed after the run, not before it. A reader should therefore
treat v3 as a **pre-specified** test rather than a fully pre-registered one. The
distinction is real and is not being papered over. The rule code hash
(`sha256 terratrace/panel_v3.py = 518ed669…`) is identical to the committed
version, and `git diff HEAD` on that file is empty, which is the strongest
available evidence that the rules were not tuned to the outcome.

Verdicts produced under this qualification are labelled accordingly in
`RESULTS-v3.md`.

## Artefacts and hashes (recorded at freeze)

| artefact | sha256 |
|---|---|
| `config/matched_footprint_v3.yml` | `70eeafd4160f11502a35c898dfc47daef4f7087dd311adbd9a8c9c2aa236de4f` |
| `terratrace/panel_v3.py` | `518ed66959bc68ee775ad9e0fabc38149b3569ce53277abb7c49f89024814edb` |
| `terratrace/confirmation.py` | `7b0e436012ce1c031a33fca5e978110eca49e3b91db4d9a11f9e7ab7b76e9190` |
| `artifacts/mf_panel_v3/matched_panel_v3_real.json` | `4a4922e3396c3531641066a4f8fa8334590ec22f16ba5df69cb11339b689b695` |

Engine HEAD at freeze: `d04faa5`.

## Why v3 (from the frozen v2 result)

Protocol v2 (`RESULTS-v2.md`) **withdrew** the Craters-of-the-Moon analog claim:
under matched footprints and honest supports the engine abstained in all 14 cells,
and Craters was the nearest candidate for a cratered highland (Noachis) as readily
as for volcanic plains. The leading explanation — **a smoothness / shortlist
effect** (Martian terrain at km scale is smoother than the Earth candidates, and
Craters was the smoothest of them) — was *consistent* with v2 but was **never
tested directly**. v2 also had low power (12–16 cells per side) and one over-broad
rule (H3 fired on any change).

## The question

When Earth candidates include terrains that are **as smooth as Craters but not
volcanic**, does a basaltic lava plain still match Martian volcanic plains better —
and does that advantage disappear for Martian highlands?

- **S (shortlist / smoothness):** the nearest Earth candidate tracks km-scale
  smoothness, not volcanic origin; a smooth non-volcanic control is non-dominated
  alongside, or instead of, the basaltic plains.
- **V (volcanic specificity):** basaltic candidates dominate the smooth
  non-volcanic controls for Martian volcanic plains, but not for Martian highlands.

Both outcomes are informative; neither is assumed.

## Design

| | v2 | v3 (frozen) |
|---|---|---|
| Common extent | 24 km | **60 km** |
| Cells per side @ 1.5 / 2 / 3 km | 16 / 12 / — | **40 / 30 / 20** |
| Earth candidates | 3 | **7, each with a stated class** |
| Smooth non-volcanic controls | none | **2** (the direct test of S) |
| Confirmatory Mars references | 5 | **3 volcanic plains + 2 highland, all fresh** |
| H3-type rule | fired on any change | **distinguishes reversed / stabilised / destabilised / membership_changed** |

### Candidate classes (assigned from the literature BEFORE the run)

Every class assignment is backed by a source, and the km-scale smoothness stated
was **measured** from the public Copernicus GLO-30 COG mosaic at each centre
(60 km window, elevation σ in metres) — it is not assumed. The measurement is what
makes "smoothness-matched control" a testable design rather than a label.

| id | class | 60 km σ (m) | basis for the class |
|---|---|---|---|
| earth_deccan_traps | basaltic | 31.6 | Deccan Traps flood basalt, India |
| earth_harrat_khaybar | basaltic | 102.5 | Harrat Khaybar, basaltic volcanic field, Saudi Arabia (GVP) |
| earth_snake_river_plain | basaltic | 95.3 | Snake River Plain, underlain by basalt from shield volcanoes |
| earth_odadahraun | basaltic | 182.0 | Ódáðahraun, Iceland — basaltic lava field |
| **earth_nullarbor** | **smooth_control** | **5.2** | Nullarbor Plain — Miocene **limestone**, a former seabed; world's largest single limestone exposure; non-volcanic |
| **earth_llano_estacado** | **smooth_control** | **14.3** | Llano Estacado — Ogallala / Permian **sedimentary** high plain; non-volcanic |
| earth_nevada_basin | other | 244 | basin-and-range near-miss; never part of an S or V claim |

**Why these two controls are the pivot.** S can only be tested if the controls are
genuinely smooth *and* genuinely non-volcanic. Nullarbor is limestone karst on a
former seabed; Llano Estacado is an alluvial/sedimentary mesa. Neither is lava.
Their measured 60 km σ (5 and 14 m) is in the same band as the Martian volcanic
plains references (5–32 m), which is exactly what makes them a fair shortlist
competitor to the basalts rather than a straw man.

**Falsification check on our own controls (stated before the run).** The strongest
argument against each: Nullarbor has karst dolines and caves, so its fine-scale
roughness could be non-representative of a "pristine" smooth surface; and its
flatness is *extreme* (σ 5 m against 102–182 m for the basalts), which could make
it a degenerate near-flat control that wins on scale rather than on morphology.
Llano Estacado has playa lakes (seasonal water-filled depressions) and active
agriculture — both visible in a DSM — and its south end blends into the Edwards
Plateau. These weaknesses are recorded here so that a null or positive S result is
read with them in view.

### Mars references (MOLA, already on disk — no download)

All coordinates were verified against the **IAU Gazetteer of Planetary Nomenclature**
(`MARS_nomenclature_center_pts.zip`, 2052 features). Each point was additionally
checked to have **no IAU-named crater ≥ 25 km within 30 km**, and its 60 km
roughness was measured on the real MOLA DEM.

**Corrections found by that verification (recorded for transparency):**

- **`Solis Lacus` is an *albedo feature*, not a plain.** The only IAU-named feature
  at that location suitable as a plains reference is **Solis Planum** (Planum,
  1811 km). The proposal's "25.9 S, 270.2 E" is also a bad point — it straddles the
  Solis Dorsa / Claritas Fossae fracture belt (1059 m relief at 60 km). The point
  was **moved to 30.0 S, 278.0 E**, inside Solis Planum only, 234 m relief.
- **`Lunae Planum` was reclassified, not just re-coordinated.** Measured 60 km
  σ = 41 m and it is a Hesperian degraded highland plateau dissected by Kasei Valles
  (ridge-and-groove terrain: Sacra Dorsa / Fossae / Sulci), *rougher* than the
  confirmed volcanic plains. Calling it "volcanic plains" would have put a
  misclassified unit into the confirmatory class. It was **dropped**; **Cerberus
  Palus** (young lava plain, lava coils documented in Athabasca Valles) took its place.
- **Terra Cimmeria at 34.7 S, 145.0 E sampled the** ***interior of Martz crater***
  (92.7 km): 60 km relief 2237 m, σ 604 m — a crater, not a highland. Replaced.
- **Arabia Terra at ~20 N, 30 E sat on Cassini crater's rim** (the coordinate came
  from a fan wiki, not the Gazetteer). The USGS centre for Arabia Terra itself
  (21.25 N, 5.72 E) also falls inside Acidalia Planitia's boundary, so it is not a
  clean highland sample either. Replaced.

Because v3 was **not frozen** at that point and **no v3 result existed**, changing
these was the correct time to change them — this is a *pre-run* design fix, not a
rescue edit. The stopping rule below governs anything after the freeze.

| id | class | status | centre (lat, lon E) | IAU feature | 60 km σ (m) |
|---|---|---|---|---|---|
| mars_daedalia | volcanic_plains | exploratory | −21.5, 226.5 | Daedalia Planum | 33.5 |
| mars_elysium | volcanic_plains | exploratory | 4.5, 150.0 | Elysium Planitia | 6.0 |
| mars_amazonis | volcanic_plains | exploratory | 24.8, 196.0 | Amazonis Planitia | 10.7 |
| mars_syria | volcanic_plains | exploratory | −12.0, 256.0 | Syria Planum | 94.6 |
| mars_hesperia | volcanic_plains | exploratory | −21.4, 109.9 | Hesperia Planum | 59.4 |
| mars_noachis | highland | exploratory | −45.0, 10.0 | Noachis Terra | 142.1 |
| mars_coprates | highland | exploratory | −13.4, 298.6 | Coprates Chasma | 936.2 |
| **mars_arcadia** | volcanic_plains | **confirmatory** | 49.02, 188.15 | Arcadia Planitia | 7.4 |
| **mars_cerberus** | volcanic_plains | **confirmatory** | 5.78, 148.15 | Cerberus Palus | 5.4 |
| **mars_solis** | volcanic_plains | **confirmatory** | −30.0, 278.0 | Solis Planum | 31.5 |
| **mars_terra_sabaea** | highland | **confirmatory** | 2.72, 51.3 | Terra Sabaea | 148.2 |
| **mars_terra_sirenum** | highland | **confirmatory** | −39.49, 205.85 | Terra Sirenum | 255.6 |

The exploratory/calibration references were all *seen* in v1 or v2. They are
reported but **never counted** as confirmation (they cannot confirm a hypothesis
they helped form).

## Decision rules (frozen; implemented in `terratrace/panel_v3.py`)

Rules read **honest supports only** (≥ the support floor), **core lens**, and
**confirmatory references only**. A predeclared S or V expectation that is missing
or declared differently makes its rule inconclusive rather than failing it.

- **S supported** iff **≥ 2 of the 3** confirmatory `volcanic_plains` references
  hold S, where S holds for a reference iff *some `smooth_control` candidate is in
  the baseline Pareto layer 1 at **every** honest support*.
- **V supported** iff **≥ 2 of 3** confirmatory plains references hold V **and
  ≥ 1 of 2** confirmatory highland references does not, where V holds for a
  reference iff *some `basaltic` candidate Pareto-dominates **every**
  `smooth_control` candidate*.
- **R (resolution robustness) supported** unless any confirmatory honest cell is
  classified `reversed` under resolution matching (the v2 lesson: a *stabilised* or
  *membership_changed* cell is not a reversal and must not be read as one).
- **Comparability gate:** if any honest-support cell of a confirmatory reference
  (raw or resolution-matched) leaves the honest regime, S, V and R are all
  inconclusive; each rule's own result is retained as `rule_verdict`.

Honest supports: 1500 / 2000 / 3000 m. Diagnostic supports (never evidence):
500 / 1000 m.

## Stopping rule

The outcome is recorded **exactly as produced**. No rescue edits. If the result is
inconclusive or the panel is under-powered, that is reported as such and any
follow-up is a **new versioned protocol**, not an amendment to this one.
