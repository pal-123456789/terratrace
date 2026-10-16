# TerraTrace Matched-Footprint Benchmark — Protocol v2 (reference panel)

**Frozen 2026-10-16, before any v2 result was produced.** Inputs: `config/matched_footprint_v2.yml`.
v1 (`BENCHMARK-PROTOCOL.md`) is kept unchanged as the historical record.

## Why v2 (defects found by inspecting the v1 real output, not by assumption)

The v1 real run (Daedalia Planum vs three Earth candidates) recommended Craters of the Moon at
every support, and the mismatched-footprint control agreed. Inspecting the bundle's own provenance
with `comparability.assess_cell` showed **no v1 cell was in an honest comparison regime**:

| v1 support | regime | why |
|---|---|---|
| 500 m | footprint-mismatched + below-effective-resolution | Earth tiles truncated (Craters 24.4 km vs Mars 39.8 km, ratio 1.63); 500 m < MOLA effective resolution ≈ 1389 m |
| 1000 m | footprint-mismatched + below-effective-resolution | same |
| 2000 m | footprint-mismatched | ratio 1.63 |

Both defects bias toward the **smoothest, smallest-window** candidate — which is Craters. So the v1
result is **exploratory and unconfirmed**. It is the hypothesis v2 tests, not a result v2 must keep.

## Hypotheses and frozen decision rules

Regime for all evidence: common extent = the largest window every unit provides untruncated
(24 km, limited by the Craters tile); supports **≥ the support floor** (1500 m, 2000 m). Supports
500/1000 m are **diagnostic only** and never count as evidence. Core lens. Same three Earth
candidates for every reference. Panel references are never compared with each other.

- **H1 — Confirmation.** For held-out Mars volcanic plains, Craters of the Moon is the sole
  core-lens recommendation. *Supported* if **≥ 2 of the 3 confirmatory plains references**
  (Amazonis, Syria, Hesperia) have outcome `holds` (recommended at both honest supports).
  *Not supported* if ≤ 1. Daedalia and Elysium are exploratory and are reported but **never counted**.
- **H2 — Specificity.** The relationship is specific to volcanic plains, not a generic
  "closest member of a weak shortlist" effect. *Supported* if **both** contrast references
  (Noachis Terra, Coprates Chasma) have outcome `holds` for `not_sole` (Craters is not the sole
  recommendation at either honest support) **and** the panel specificity verdict is `specific`.
  *Not supported* if Craters is the sole recommendation for the contrast terrains too — then any
  plains result is reported as **non-specific**.
- **H3 — Not a source-smoothing artifact.** Re-running with every unit low-passed to the coarsest
  effective resolution (`resolution.match_effective_resolution`) leaves the primary reference's
  honest-support recommendation unchanged, and changes no H1 confirmatory outcome from `holds` to
  `fails`. *Not supported* if the matched-resolution run reverses the primary recommendation.
  Diagnostic (not evidence): whether the v1 500 m result changes under resolution matching.
- **H4 — Absolute adequacy (reported, no predeclared direction).** For each reference, is the
  recommended candidate within that reference's own internal variability
  (`adequacy.adequacy_assessment`, 95th percentile, 3×3 held-out sub-windows, at 1500 m)?
  If no candidate is adequate, the honest statement is: *"best among these candidates, but outside
  the reference's own morphological variability."*

**Robustness (exploratory, primary reference only):** `adversarial.stress_test` — crop-origin shift,
support step, correlated-noise / tilt / smoothing DEM perturbations, lens family, candidate dropout.
Reported as trust bounds, never as confirmation.

## What this cannot establish (stated before the run)

- **Not independent replications:** all Mars references share one source (MOLA) and all Earth
  candidates share one (COP30); the candidate set is the same three tiles. 7 references × 2 honest
  supports = 14 decisions — multiple comparisons, reported as such.
- **Low statistical power:** at 24 km extent the honest supports give only 16 and 12 cells per side.
  The block bootstrap and adequacy bands are correspondingly coarse.
- **Representativeness:** each 24 km window samples a small part of a named Mars unit; coordinates
  are approximate named-feature centres.
- **The 3× effective-resolution figure is a heuristic**, not a measured MOLA transfer function.
- **Morphology only:** no traversability, geologic-equivalence, site-access, or mission claim.

## Stopping rule

After this run: record the H1–H4 outcomes in `CLAIM-LEDGER.md` exactly as produced, and do not add
references, candidates, or supports to rescue or strengthen a result within this protocol. If the run
is underpowered or inconclusive, the next action is a **new protocol (v3)** with wider Earth windows
and purposefully chosen new candidates (requires new downloads; resource estimate first).

## Resources (estimated before running)

Seven windowed MOLA reads of ~26 km (~57×57 px each) plus three cached COP30 tiles (~1100×1200 px);
~100 small `compare_units` calls plus three FFT low-pass filters. Expected < 3 min and < 1 GB RAM,
no network, no API key.
