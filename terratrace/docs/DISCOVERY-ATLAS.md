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

## The 10 cross-artifact reconciliations

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

## What the atlas does not contain

It carries **distances and band memberships**, never a single quality number: there is no composite
analog score anywhere, and `terratrace/verdicts.py` has a structural check that walks a verdict block
— including nested sub-dictionaries — and refuses one. It is map-scale terrain-**morphology**
screening only: no traversability, geologic-equivalence, site-access or mission-readiness claim, and
an "established adequate" verdict would upgrade none of them.

Regenerate with `python scripts/run_discovery_atlas.py`.
