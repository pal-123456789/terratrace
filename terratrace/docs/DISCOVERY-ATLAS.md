# The scale-resolved evidence atlas

**One question this page answers:** how much evidence supports a terrain relationship here, at what
scale, and where does the conclusion break.

Everything below is read from a committed record by `scripts/run_discovery_atlas.py`, which writes
`artifacts/discovery_atlas/discovery_atlas.json` and `.md`. Every number that appears in more than
one record is read from **both** and compared; if any pair disagrees the atlas **refuses to publish**
rather than merging them into a confident-looking table. That refusal is tested — a seeded
disagreement exits 1 naming the check.

## The three answers, kept apart

| question | answer on this project's real data |
|---|---|
| Which candidate is closest, among those tested? | **definite at 18 of 18** lunar cells |
| Is any candidate inside the reference's own morphological variability? | **not established** at 18 cells |
| Is the evidence enough to answer either? | **marginal** |

These are three answers to three questions, and the third does not qualify the first two away — it
qualifies them. The full rules, including the demotion of a variability band that admits
known-different terrain, are in `terratrace/verdicts.py` and the results in
[LUNAR-DEMONSTRATION.md](LUNAR-DEMONSTRATION.md).

## Two regimes, declared and never pooled

| regime | body | footprint | supports | cells/side | source | status |
|---|---|---|---|---|---|---|
| `mars_panel_v3` | Mars | 60.0 km | 1500, 2000, 3000 m | 40/30/20 | MOLA 463 m/pixel (USGS) | **confirmatory** — frozen, pre-specified but not pre-registered |
| `lunar_panel_v2` | Moon | 9.0 km | 500, 750, 1000 m | 18/12/9 | LOLA 5 m/pixel (NASA Goddard PGDA) | **corrected exploratory reanalysis** — the same data was examined before the correction |

They are not comparable to each other: different footprint, different supports, different bodies,
different source resolutions. The atlas records them side by side and pools **nothing** across them,
and a reconciliation asserts that they share no support so that pooling them cannot even look
plausible.

## Where the conclusion breaks

**Abstention rows: 36.** Every one is listed in the atlas rather than summarised, because a count of
abstentions is exactly the kind of number this project keeps finding gets read as a score. The two
headline breaks:

| finding | value |
|---|---|
| perturbations declared before the run | 30 |
| perturbations that left the ordering untouched | **28** |
| reversing conditions | `footprint:3000m` (11 of 18 cells), `add_unit:earth_andean_volcano` (7 of 18) |
| nearest unit to a lunar reference is **another lunar site** | **18 of 24** site × descriptor statistics |
| adequacy bands calibrated and rejecting known-different controls | **0** of 18 |
| error realisations sampled | 6 of 100 published, Site01 only |

The atlas-level evidence-sufficiency verdict is **marginal**, and the declared reasons are the
ensemble size, the one-dimensional axis set, and nothing else — the two-regime scope is recorded as
a property of the atlas rather than as a weakness of the evidence, because refusing to pool is a
virtue and charging it as a defect would have been a way of making an honest scope look like a fault.

## The 13 cross-artifact reconciliations

| check | what it holds together |
|---|---|
| `documented_hash:v3_bundle` | the hash printed in the v3 protocol equals the bundle on disk |
| `documented_hash:v3_config` | the hash printed in RESULTS-v3 equals the config on disk |
| `lunar_headline:panel` | all 18 lunar cells share one single-member non-dominated set, and it is Nevada |
| `lunar_headline:stress_baseline` | the stress test re-derived the panel's headline instead of assuming it |
| `ranking:adequacy_matches_panel` | every cell the adequacy report ranks recommends the panel's survivor |
| `dependence:agrees_with_stress` | the audit says one axis **and** dropping any axis changes nothing |
| `stress:summary_matches_rows` | stable + reversing perturbations equal the counted total |
| `adequacy:summary_matches_cells` | the sibling-nearest count is what the cells say |
| `regimes:disjoint_supports` | the two regimes share no support |
| `v3:hypothesis_counts_sum` | the v3 change counts sum to the cells they classify |

Two of these are the ones that would have caught the project's own past mistakes: the documented
hashes are the check that a cited checksum refers to a file that actually exists, and the
dependence/stress agreement is the check that two documents describing the same finding cannot
quietly drift apart.

## Is the frontier robust to the axis set? No — and the control says why

The lunar panel decides a winner by Pareto dominance over three declared axes. The
independent-axis probe (see [`AXIS-PROBE.md`](AXIS-PROBE.md)) added every admissible scalar in the
engine's own descriptor bank as a **fourth** axis in turn and recomputed the layer-1 set at all 18
cells. The answer:

| measurement | value |
|---|---|
| candidate axes decision-tested | 141 |
| cells whose winner set changed | 0 to 18 of 18 |
| axes that changed nothing at all | 42 |
| **an arbitrary coordinate** | **15.90 of 18 cells on average** over 300 random draws |
| axes beating that control | **0** |
| most independent descriptor | `/variogram/nugget`, adjusted R² -0.511 against a chance level of 0.4286 |

**The last two rows are the finding.** An arbitrary fourth coordinate — one carrying no information
whatsoever — moves the frontier in nearly sixteen of eighteen cells, and **no candidate axis exceeds
that control's 95th percentile**. Every change in the row above it is what adding a dimension does to
a Pareto rule over eight points in three dimensions, not evidence about any candidate. Meanwhile the
most independent descriptor the probe could find, `/variogram/nugget`, changes the decision at **0** of the 18
cells: independence and decision-relevance are different properties, and this panel separates them.

So the atlas's own headline — Nevada sole non-dominated at every lunar cell — must be read as a
property of the *rule*, and it is bounded here rather than left implicit. It does **not** demote the
ranking, which stands as published, relative and provisional; and it does **not** promote any Earth
candidate, because adding dimensions promotes co-winners without discriminating between them.

The analytic half of the same probe establishes that the three declared axes are exactly blind to a
quarter-turn rotation of a planar surface (invariant to 1e-13), of which 48 of the bank's 180
computable scalars are not.


## What the atlas does not contain

It carries **distances and band memberships**, never a single quality number: there is no composite
analog score anywhere, and `terratrace/verdicts.py` has a structural check that walks a verdict block
— including nested sub-dictionaries — and refuses one. It is map-scale terrain-**morphology**
screening only: no traversability, geologic-equivalence, site-access or mission-readiness claim, and
an "established adequate" verdict would upgrade none of them.

Regenerate with `python scripts/run_discovery_atlas.py`.
