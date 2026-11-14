# TerraTrace — scale-resolved planetary morphology evidence atlas

**Assembled, not asserted.** Every number below is read from a committed record, and every number that appears in more than one record is reconciled in `reconciliations` — one disagreement and this file is not written.

## What the atlas answers

| question | answer |
|---|---|
| Which candidate is closest, among those tested? | definite at 18 of 18 lunar cells |
| Is any candidate inside the reference's own variability? | **not established** at 18 cells |
| Is the evidence enough? | **marginal** |
| Is the frontier robust to the AXIS SET? | **no** — 0 of 141 candidate axes move it further than an arbitrary coordinate does (see below) |

## The frontier is bounded by the number of axes

Adding a fourth axis to the Pareto comparison changed the layer-1 set in 0 to 18 of 18 lunar cells across 141 candidate descriptors — but a **uniformly random** fourth coordinate, carrying no information at all, changes it in 15.90 of 18 on average over 300 draws. **No candidate axis exceeds that control's 95th percentile.** The most independent descriptor the probe found (`/variogram/nugget`, median adjusted R² -0.511 against a chance level of 0.4286) changes the decision at 0 cells.

Read as: the lunar panel's **sole-non-dominated** property is a property of running a Pareto rule over eight units in three dimensions, not evidence about candidates. The ranking stands as published — relative and provisional — and this bounds it.

## Regimes — declared and kept apart

| regime | body | footprint | supports | cells/side | source | status |
|---|---|---|---|---|---|---|
| `mars_panel_v3` | mars | 60.0 km | 1500, 2000, 3000 m | 40/30/20 | MOLA 463 m/pixel (USGS) | CONFIRMATORY |
| `lunar_panel_v2` | moon | 9.0 km | 500, 750, 1000 m | 18/12/9 | LOLA 5 m/pixel (NASA Goddard PGDA) | CORRECTED EXPLORATORY REANALYSIS |

The two regimes are NOT comparable to each other: different footprint, different supports, different bodies and different source resolutions. Nothing in this atlas pools across them.

## Where the conclusion breaks

36 rows below are cells where the engine abstains or the absolute question is unanswered. They are listed rather than summarised, because a count of abstentions is what this project keeps finding gets read as a score.

| stress perturbation or finding | value |
|---|---|
| perturbations declared before the run | 30 |
| perturbations that left the ordering untouched | **28** |
| reversing conditions | `footprint:3000m`, `add_unit:earth_andean_volcano` |
| nearest unit is a sibling lunar site | **18 of 24** site x descriptor statistics |

## Cross-artifact reconciliations

| check | expected | observed | ok |
|---|---|---|---|
| `documented_hash:v3_bundle` | `"4a4922e3396c3531641066a4f8fa8334590ec22f16ba5df69cb11339b68` | `"4a4922e3396c3531641066a4f8fa8334590ec22f16ba5df69cb11339b68` | yes |
| `documented_hash:v3_config` | `"985350769cc7d347a4d524b11cd47da04b3e36948e1eff7f40e3eaccbd3` | `"985350769cc7d347a4d524b11cd47da04b3e36948e1eff7f40e3eaccbd3` | yes |
| `lunar_headline:panel` | `[["earth_nevada_basin"]]` | `[["earth_nevada_basin"]]` | yes |
| `lunar_headline:stress_baseline` | `true` | `true` | yes |
| `ranking:adequacy_matches_panel` | `{"Site01@500m": "earth_nevada_basin", "Site04@500m": "earth_` | `{"Site01@500m": "earth_nevada_basin", "Site04@500m": "earth_` | yes |
| `dependence:agrees_with_stress` | `[true, {"drop_axis:mean_slope_deg": 0, "drop_axis:mean_relie` | `[true, {"drop_axis:mean_slope_deg": 0, "drop_axis:mean_relie` | yes |
| `stress:summary_matches_rows` | `30` | `30` | yes |
| `adequacy:summary_matches_cells` | `{"of": 24, "count": 18}` | `{"of": 24, "count": 18}` | yes |
| `regimes:disjoint_supports` | `[]` | `[]` | yes |
| `v3:hypothesis_counts_sum` | `15` | `15` | yes |
| `axis:probe_reproduces_panel` | `{"mismatches": [], "frontier_sizes": {"1": 18}}` | `{"mismatches": [], "frontier_sizes": {"1": 18}}` | yes |
| `axis:no_pareto_removals` | `true` | `true` | yes |
| `axis:control_is_present` | `{"draws": 300, "n_cells": 18}` | `{"draws": 300, "n_cells": 18}` | yes |

## Uncertainty, and what could not be measured

- error ensemble: 6 of 100 published realisations, Site01 only
- adequacy bands calibrated: 0 of 18 attempted
- Only the lunar DEM has a published error model, and only six of its 100 realisations were retrieved. The Earth side is treated as exact, which is a stated limitation rather than a finding.

## The firewall

map-scale terrain-MORPHOLOGY screening only. no composite analog score; distances and band memberships only.

Regenerate with `python scripts/run_discovery_atlas.py`.
