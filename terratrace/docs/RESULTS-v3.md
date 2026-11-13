# Protocol v3 — RESULTS

Recorded exactly as produced by the frozen rules (`docs/BENCHMARK-PROTOCOL-v3.md`),
from `artifacts/mf_panel_v3/matched_panel_v3_real.json`
(sha256 `4a4922e3396c3531641066a4f8fa8334590ec22f16ba5df69cb11339b689b695`, written
2026-11-05 20:06:54 IST). Engine at `d04faa5`.

**Status: PRE-SPECIFIED, not fully pre-registered.** The rules and the config were
fixed before the data was read; the protocol document was committed after the run. See the
qualification at the top of the protocol, and
[`V3-ARCHIVAL-CLARIFICATION.md`](V3-ARCHIVAL-CLARIFICATION.md) for the full chronology and
the exact commit times. The verdicts below are reported as produced; read them with that
caveat attached.

**Scope of the confirmatory experiment.** The S/V/R verdicts below were produced with
`decision_metrics="core"` — the core decision lens. TerraTrace ships five default lenses and
an opt-in sixth, but those are **not** independent scientific replications of this finding;
they are alternative analytical views of the same terrain. The lens is recorded in the result
JSON itself (`"decision_metrics": "core"`), not only in prose.

**Config identity, reconciled.** The sha256 recorded above for the v3 config is
`70eeafd4160f11502a35c898dfc47daef4f7087dd311adbd9a8c9c2aa236de4f` — the config **as it stood
at the result commit `820c17d`**. The file shipped at HEAD hashes to
`985350769cc7d347a4d524b11cd47da04b3e36948e1eff7f40e3eaccbd324f0c`, because commit `ddb2247`
(9 minutes after the result) corrected one **comment**: the Nevada Basin σ annotation, from
~244 m to the measured 562 m. Every analytical parameter is byte-identical between the two
revisions. An earlier revision of this page said the config was "unmodified since"; that was
true when written and was falsified by `ddb2247`. Both hashes and the parameter-only
difference are asserted by `tests/test_v3_archival.py`, so the claim cannot drift again.

## Headline

> **S — SUPPORTED. V — NOT SUPPORTED. R — SUPPORTED.**
>
> The smoothness / shortlist explanation of the withdrawn Craters claim is
> **directly confirmed**. For all three confirmatory Martian volcanic plains, a
> **smooth non-volcanic** Earth terrain sits on the Pareto front at every honest
> support — and basaltic origin buys **nothing**: the basaltic candidates fail to
> dominate those non-volcanic controls for plains, while they *do* dominate them
> for cratered highlands. The nearest Earth analog tracks **km-scale roughness,
> not volcanic origin.**

This is the clean answer to the v3 question, and it is the second reproducible
scientific result of the project — the first being v2's negative result. It also
retires the last standing explanation of the original (withdrawn) Craters finding.

## 1. Design integrity (checked before reading the verdicts)

| check | result |
|---|---|
| Comparability gate — honest-support cells of confirmatory references leaving the honest regime | **0 of 15** (`regime_violation.flag = false`, empty cell list) |
| Honest supports demoted for being below the support floor | **none** (1500/2000/3000 m all ≥ 1389 m floor) |
| Footprint match across units | 65.8–66.4 km available per unit; ratio ≤ 1.01 |
| Confirmatory references per class | exactly 3 `volcanic_plains`, exactly 2 `highland` — as the rules require |
| Confirmatory reference contaminated by a ≥25 km IAU crater within 30 km | none (checked against the Gazetteer) |

Unlike v2 — where every cell fell outside the honest regime and the engine
abstained everywhere — **v3 compared 15 confirmatory honest cells that are all
genuinely in regime.** The panel has the power the rules assume.

## 2. S (smoothness / shortlist) — SUPPORTED

Rule: ≥ 2 of 3 confirmatory plains references have a `smooth_control` candidate in
Pareto layer 1 at **every** honest support.

| reference | 1500 m | 2000 m | 3000 m | outcome |
|---|---|---|---|---|
| mars_arcadia | TIE {llano_estacado, **nullarbor**} | RECOMMEND {**llano_estacado**} | RECOMMEND {**llano_estacado**} | **holds** |
| mars_cerberus | RECOMMEND {**nullarbor**} | RECOMMEND {**nullarbor**} | RECOMMEND {**nullarbor**} | **holds** |
| mars_solis | RECOMMEND {**llano_estacado**} | TIE {deccan, **llano_estacado**} | TIE {deccan, **llano_estacado**} | **holds** |

**3 of 3 hold** (≥ 2 required) → **S SUPPORTED**.

A smooth **non-volcanic** terrain — Nullarbor limestone or the Llano Estacado
sedimentary plain — is on the Pareto front for every confirmatory Martian volcanic
plain at every honest support. The smoothness explanation is not an inference any
more; it is measured.

## 3. V (volcanic specificity) — NOT SUPPORTED

Rule: ≥ 2 of 3 confirmatory plains references have some `basaltic` candidate
Pareto-dominating **every** `smooth_control` candidate, **and** ≥ 1 of 2
confirmatory highland references does not.

| reference | class | V outcome |
|---|---|---|
| mars_arcadia | volcanic_plains | **fails** |
| mars_cerberus | volcanic_plains | **fails** |
| mars_solis | volcanic_plains | **fails** |
| mars_terra_sabaea | highland | holds |
| mars_terra_sirenum | highland | holds |

**0 of 3 plains hold V** (≥ 2 required) — and V holds for *every* highland
reference, which fails the second condition of the rule as well. **V NOT SUPPORTED.**

> **Scope of this negative result.** Within the tested candidate panel and the core-lens
> benchmark, smooth non-volcanic candidates remained non-dominated for all three confirmatory
> volcanic-plains references. The benchmark did not establish the pre-declared
> volcanic-specific dominance advantage. It does **not** show that volcanic origin is
> irrelevant to planetary analog work in general — only that it carried no measurable
> advantage here, for these candidates, at these supports, under this lens.

The rule's own message is the finding: *"the basaltic advantage is not specific to
volcanic plains."* A basaltic lava plain is **not** a better analog for Martian
volcanic plains than a smooth limestone or sedimentary plain is. And the reverse
holds too — for cratered *highlands* the rough basalts (Harrat Khaybar,
Ódáðahraun, Snake River Plain) do come to the front.

## 4. The mechanism, visible in the cells

Putting S and V together, the discriminator is unmistakable:

- **Smooth references → smooth candidates.** Arcadia (σ 7 m) and Cerberus
  (σ 5 m) are matched by the two smoothest Earth candidates — Nullarbor (σ 5 m,
  limestone) and Llano Estacado (σ 14 m, sedimentary).
- **Rough references → rough candidates.** Terra Sabaea (σ 148 m) and Terra
  Sirenum (σ 256 m) are matched by Harrat Khaybar (σ 102 m) — a *basaltic* field.
  The basalts win where the terrain is rough, not where it is volcanic.
- **The one smooth basalt behaves as a smooth candidate.** Deccan Traps (σ 32 m,
  flood basalt) enters Pareto layer 1 for Solis Planum — the roughest of the three
  plains references — precisely when the window is large enough to average its
  relief. It competes *because it is comparatively smooth*, not because it is
  volcanic.

Within this panel and the core lens, origin did no work that roughness did not already do.

## 5. R (resolution robustness) — SUPPORTED

15 confirmatory honest cells classified raw vs resolution-matched (all units
low-passed to 1389 m):

| unchanged | stabilised | destabilised | reversed | membership_changed | error |
|---|---|---|---|---|---|
| 11 | 0 | 1 | **0** | 3 | 0 |

**No fatal reversal** → **R SUPPORTED** — in the narrow sense the rule actually supports:
*no outright candidate reversal occurred under the tested resolution-matching control.*
Membership change and destabilisation are shown separately above rather than folded into the
pass, because neither is a reversal: a layer-1 set that gains a member, or a recommendation
that loosens into a tie, is a change under resolution, not a contradiction. This is **not** a
claim of universal resolution independence — a single-cell recommendation is demonstrably
fragile (§6).

This is where the v2 protocol lesson paid off. In v2 the over-broad H3 rule
("any change") fired on a *stabilisation*. v3's classifier separates the cases:

- `mars_solis @ 1500 m` — **destabilised**: RECOMMEND {llano_estacado} → TIE
  {deccan, llano_estacado}. The recommendation loosened; the nearest unit did not
  change. Under v2's rule this would have looked like a failure; it is not one.
- `mars_arcadia @ 1500 m`, `mars_solis @ 3000 m`, `mars_terra_sabaea @ 3000 m` —
  **membership_changed**: the layer-1 sets overlap but differ. No reversal.

Robustness re-check: re-evaluating S and V on the resolution-matched panel gives
S = supported, V = not_supported — identical to the raw verdicts (`differs: false`).

## 6. Adequacy, adversarial stress test, and warnings (reported, never evidence)

- **Adequacy** @1500 m: for every reference, *some* candidate is within that
  reference's own internal variability. Notably Arcadia and Cerberus admit only
  the two smooth controls as adequate — the same two that win S.
- **Adversarial** on the primary reference (mars_arcadia @1500 m): verdict
  **fragile** — stable in 0.86 of 21 bounded perturbations, reversing under a
  6-pixel crop-origin shift and under dropping either smooth control. This is
  honestly reported: the *primary single-cell* recommendation is not robust, even
  though the class-level S pattern is (it holds at every support and is unchanged
  under resolution matching). The fragility is itself consistent with "the top of
  the shortlist is a near-tie among similarly smooth terrains."
- **Warnings:** none. No honest support needed demotion or diagnostic reclassification.

## 7. What this does and does not say

**Does say:** with MOLA + Copernicus GLO-30, real 60 km windows, honest supports
and matched footprints, the Earth terrain that best matches a Martian volcanic
plain is a **smooth** terrain — and it is at least as likely to be **non-volcanic**.
The withdrawn Craters-of-the-Moon preference is explained by smoothness, and that
explanation is now tested rather than asserted. The project's headline stands:
*TerraTrace caught its own false analog* — and v3 shows *why* it was false.

**Does not say:** that no Earth terrain resembles a Martian plain (the morphometric
similarity is real and measured); that basalts are irrelevant to Mars analog work
(they matter where the target is rough); or anything about traversability,
geologic equivalence, site access or mission readiness.

**Limits (unchanged and load-bearing):** one DEM source per body (MOLA, COP30), so
references × supports are multiple comparisons and not independent replications;
COP30 is a DSM including vegetation and buildings; each 60 km window samples a
small part of a named unit; the 3× effective-resolution figure is a heuristic; and
candidate classes are literature assignments made before the run.

**Falsifier for the next iteration:** a pre-registered test in which a smooth
*specifically volcanic* Earth terrain (a smooth basaltic plain with no relief
structure) beats the smooth non-volcanic controls for Martian volcanic plains but
not for highlands. Deccan Traps is the closest thing in this panel and it does not
do that — it competes as a smooth unit. Should a future panel find the opposite,
S would not be the whole story.

## 8. Reproducing this

```bash
cd terratrace
python scripts/fetch_earth_candidates.py --config config/matched_footprint_v3.yml --source cog
python scripts/run_matched_benchmark.py --config config/matched_footprint_v3.yml --out artifacts/mf_panel_v3
```

No OpenTopography API key is required: the default `--source cog` reads the public
ESA Copernicus GLO-30 COG mosaic on AWS. That path is verified to reproduce the
OpenTopography COP30 elevations **exactly** (max absolute difference 0.0 m over the
Craters of the Moon and Nevada AOI tiles — `tests/test_cop30_cog.py`).
