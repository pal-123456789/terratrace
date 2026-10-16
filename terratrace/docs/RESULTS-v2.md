# TerraTrace — Protocol v2 Results (reference panel, real data)

**Run:** 2026-10-16, on the data machine, `config/matched_footprint_v2.yml` → `artifacts/mf_panel/matched_panel_real.json`.
**Protocol:** `docs/BENCHMARK-PROTOCOL-v2.md`, frozen and committed (`ab1854a`) **before** the runner
existed or any v2 output was seen. Verdicts below are copied **exactly as produced**; nothing was
re-run, re-tuned, or re-labelled after the fact.

> Scope: map-scale terrain-morphology screening only — no traversability, geologic-equivalence,
> site-access, or mission-readiness claim.

## Conditions actually achieved

- Common extent **24,000 m** for every unit, untruncated (limited by the Craters of the Moon tile, 24,360 m).
- Support floor **1,389 m** (MOLA effective resolution, 3 × 463 m heuristic). Honest supports **1,500 / 2,000 m**
  (16 and 12 cells per side). 500 / 1,000 m run as **diagnostics only**.
- Every honest cell passed the comparability gate (regime `honest`) — so, unlike v1, this comparison is
  footprint-matched and at or above the source's effective resolution.
- Candidates: Craters of the Moon (basaltic lava field), Nevada basin (basin-and-range), Andean volcano.

## Frozen verdicts (exactly as produced)

| Hypothesis | Verdict | Rule outcome |
|---|---|---|
| **H1** confirmation (held-out volcanic plains recommend Craters) | **NOT SUPPORTED** | 0 of 3 confirmatory plains references hold |
| **H2** specificity (Craters not chosen for contrast terrains) | **INCONCLUSIVE** | not evaluable — no reference produced a recommendation in the honest regime |
| **H3** not a source-smoothing artifact | **NOT SUPPORTED** | the primary (Daedalia) result changed at both honest supports under resolution matching |
| **H4** absolute adequacy | reported | no recommended unit to assess (7 × `no_recommendation`) |

## Honest-regime decisions

| Mars reference | class / status | 1,500 m | 2,000 m |
|---|---|---|---|
| Daedalia Planum | plains / exploratory | INDETERMINATE — nearest: Craters | INDETERMINATE — nearest: Craters |
| Elysium Planitia | plains / exploratory | INDETERMINATE — Craters | INDETERMINATE — Craters |
| Amazonis Planitia | plains / confirmatory | INDETERMINATE — Craters | INDETERMINATE — Craters |
| Syria Planum | plains / confirmatory | INDETERMINATE — Craters | TIE — Craters, Andes |
| Hesperia Planum | plains / confirmatory | INDETERMINATE — Craters | INDETERMINATE — Craters |
| **Noachis Terra** | **contrast (cratered highland)** / confirmatory | INDETERMINATE — **Craters** | INDETERMINATE — **Craters** |
| Coprates Chasma | contrast (canyon) / confirmatory | TIE — Craters, Andes | TIE — Craters, Andes |

"Nearest" = the sole unit in the baseline Pareto layer 1. **INDETERMINATE** is the engine's own state for
"one candidate is nearest in the baseline, but the ranking flips under the engine's built-in perturbation
scenarios by more than 10%" (`decision.resolve_state`) — i.e. a nearest candidate exists but is not stable
enough to recommend.

## Descriptive analyses (NOT pre-registered — reported for interpretation, not as confirmation)

1. **Craters is the nearest candidate for 11 of 14 honest cells — including the contrast terrain Noachis
   Terra at both supports.** Only the very rough canyon (Coprates) and Syria at 2 km bring the Andean
   volcano into a tie. The pattern does not separate volcanic plains from a cratered Noachian highland.
2. **Below the resolution floor (diagnostic):** Craters is *recommended* for 6 of 7 references at 500 m
   and 1,000 m — again including Noachis Terra; Coprates is a TIE. This is the regime the original v1 /
   atlas result came from.
3. **Under resolution matching** (every unit low-passed to 1,389 m FWHM): Craters becomes the stable
   recommendation in **the same 11 cells** where it was already nearest; the panel's own specificity verdict
   is **non_specific**. The resolution control therefore did **not** change *which* candidate is nearest — it
   changed INDETERMINATE (unstable) into RECOMMEND (stable). The frozen H3 rule fires on *any* change and so
   reads NOT SUPPORTED; the rule did not distinguish "stabilised" from "reversed". That is a protocol-design
   lesson, recorded here; the verdict is not altered.
4. **Adequacy** (3 × 3 held-out sub-windows of each reference, 95th percentile, at 1,500 m): Craters lies
   within the own-variability band of Amazonis, Hesperia — **and Noachis Terra** — but **not** within Daedalia's
   or Elysium's (no candidate is adequate for those two, the references the original claim was built on).
   Syria and Coprates admit all three candidates (wide bands at low power).
5. **Robustness of the primary (exploratory):** adversarial stress test on Daedalia at 1,500 m: verdict
   `qualified`, 71% of 17 perturbations leave the outcome unchanged; reversing conditions: a 3-pixel
   crop-origin shift, support steps to 1,005 m and 2,250 m, and dropping either other candidate.
6. **Lens ablation (primary, 1,500 m):** core / geomorphic / landform → INDETERMINATE; extended / texture /
   hydro → TIE. No lens recommends a unit.

## Interpretation

The exploratory claim — *"TerraTrace independently re-identifies Craters of the Moon as the analog for
Martian volcanic plains"* — **does not survive a footprint-matched, resolution-aware, pre-registered test.**

- In the honest regime the engine abstains everywhere (H1 not supported).
- Across every regime examined (honest, below-floor, resolution-matched), Craters' advantage appears for a
  **cratered highland as readily as for volcanic plains**, and it is outside the own variability of the two
  plains that generated the claim.

The most economical explanation is a **shortlist effect**: at kilometre scale, Martian plains *and*
highlands are smoother than all three Earth tiles, and Craters is the smoothest of the three, so it is the
least-dissimilar member of a weak shortlist rather than a specific morphological analog. This explanation
is **consistent with** the data but **not yet tested directly** — that is the job of protocol v3
(smoothness-matched non-volcanic controls).

**What this establishes:** with these sources (MOLA, COP30), this candidate set, and 24 km windows, the data
do not support a specific Craters-of-the-Moon ↔ Mars-volcanic-plains morphological relationship, and the
earlier preference is explained at least in part by footprint mismatch and comparisons below MOLA's
effective resolution.

**What it does not establish:** that Craters of the Moon is a poor analog for *other* purposes (it is a
well-documented field analog for reasons these map-scale descriptors do not measure); that no Earth terrain
matches Martian plains; or anything at scales below ~1.4 km. Power is low (12–16 cells per side), and all
references share one source, so the 14 decisions are not independent replications.

## What changed in TerraTrace because of this

The headline result moved from *"we found an analog"* to *"TerraTrace caught its own false analog using
rules fixed before the data were seen"* — footprint matching, a resolution floor, held-out and contrast
references, and an adequacy check together turned an attractive exploratory match into an interpretable,
reproducible negative result.

## Next (per the stopping rule)

No references, candidates or supports are added to this protocol. The next step is a **new** protocol
(v3, proposed in `docs/BENCHMARK-PROTOCOL-v3-PROPOSAL.md`): wider Earth windows for statistical power,
fresh Mars references, and **smoothness-matched non-volcanic Earth controls** to test the shortlist
explanation directly.
