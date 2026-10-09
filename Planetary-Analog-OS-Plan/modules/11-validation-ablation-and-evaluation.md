# 11 — Validation, Ablation, and Evaluation

## Evaluation claim boundary

The v0.1 evaluation establishes software correctness, data handling, metric behavior, assumption sensitivity, provenance, and user comprehension. It does **not** establish physical transfer to Mars, rover mobility, autonomy performance, or mission readiness.

## Validation layers

| Layer | Question | Evidence |
|---|---|---|
| Source validation | Is the exact product known, lawful, and appropriately interpreted? | Product label, catalog metadata, terms, checksum |
| Geospatial validation | Are CRS, datum, bounds, units, and support handled correctly? | Round trips, map inspection, independent GIS result |
| Algorithm validation | Do features/comparisons behave on known fixtures? | Synthetic tests with expected values |
| Sensitivity validation | Does the result survive reasonable choices? | Scenario table and rank-flip matrix |
| Construct validation | Do experts accept the observable/claim pairing? | Structured reviewer protocol |
| Usability validation | Do users understand comparison versus proof? | Moderated task test |
| Reproducibility validation | Can a clean environment rebuild the artifact? | Clean build, hashes, logs |
| Transfer validation | Does an Earth result inform an off-world behavior? | Not available in v0.1; requires later outcome data |

## Synthetic fixture suite

- Constant plane with known slope.
- Plane with rotated aspect.
- Ridge with known local relief.
- Crater/rim with known connectivity change.
- Equal physical surface sampled at different postings.
- Missing-data wedge.
- AOI edge/truncation.
- Tile seam.
- Same morphology under different vertical offsets.
- Candidate with good morphology and unknown access.
- Pairwise trade-off with no Pareto winner.
- Scenario-driven rank reversal.

## Independent calculation protocol

1. Select a bounded raster sample.
2. Compute metrics in the production pipeline.
3. Recompute independently in another GIS/toolchain.
4. Compare values within a predeclared tolerance.
5. Investigate any tolerance failure before UI presentation.
6. Record tool versions, units, support, masks, and exact sample coordinates.

## Ablation matrix

| Ablation | Full system | Degraded system | Metric |
|---|---|---|---|
| Task conditioning | Requirement-specific metrics/thresholds | Generic equal-weight profile | Pairwise flip matrix; reviewer rationale |
| Common support | Aggregated to verified common support | Native posting comparison | Feature change and eligibility shift |
| Quality/missingness | Explicit masks and valid fractions | Silent fill/ignore | False-eligibility rate; prohibited state count |
| Sensitivity | Scenario-aware comparison | Single method run | Rank-state change frequency |
| Transfer gaps | Morphology plus non-transferable ledger | Morphology only | User overclaim/misinterpretation rate |
| Provenance | Full source-transform-result chain | Source names only | Evidence trace success/time |
| Constraints | Data/access/governance filters | Terrain-only ranking | Invalid candidate state count |
| Human readable | Plain-language scope and limits | Technical-only display | Comprehension score |

Do not claim “system improvement” unless the test measures an outcome and the result is actually run.

## Ranking and uncertainty metrics

- Pairwise rank-flip matrix under scenarios.
- Pareto membership frequency (explicitly called scenario frequency, not probability).
- Rank interval across declared scenarios.
- Feature contribution range.
- Valid-data fraction.
- Sensitivity to AOI boundary and support.
- Number of eligible, blocked, and not-comparable candidates.
- Tie/indeterminate frequency.

Do not use top-three stability with three candidates; it is vacuous. Use top-one scenario frequency and pairwise flips, while preserving tie states.

## User evaluation protocol

### Participants

Target five participants: two geospatial/planetary/robotics-literate, two technically literate non-specialists, one student/educator. If fewer are available, report raw counts and do not imply population estimates.

### Task

“Compare the Mars terrain unit with the available Earth units. Select a candidate for follow-up study or choose indeterminate. Explain one morphology result, one uncertainty, one transfer gap, and one next measurement.”

### Measurements

- decision completion/time;
- correct identification of common support;
- ability to trace a visible metric to source;
- correct distinction between similarity and transfer;
- ability to interpret tie/blocked states;
- protocol completeness;
- unsupported inference rate;
- keyboard-only completion.

### Targets

- At least 4/5 identify one similarity and one unassessed gap.
- At least 4/5 avoid interpreting result as rover/mission validation.
- Median task completion ≤3 minutes after guided context.
- Every critical task works without map interaction.

## Release scorecard

| Gate | Required artifact | Pass/fail |
|---|---|---|
| Product integrity | Claim ledger | No unsupported claims |
| Data integrity | Source lock | All critical sources M2+ |
| Algorithm | Fixture report | All critical fixtures pass |
| Support | Resolution audit | No feature at unsupported scale |
| Sensitivity | Scenario matrix | Stable or appropriately indeterminate |
| Provenance | Claim trace | Every displayed number resolvable |
| Usability | Test log | No critical misconception |
| Accessibility | Manual + automated report | Core path keyboard/non-map accessible |
| Reproduction | Clean run and manifest | Truthful runtime/rebuild statement |
| Release | Cross-link audit | App/docs/video/claims consistent |

## Evaluation report structure

1. Purpose and maturity level.
2. Data sources and exact versions.
3. Feature definitions and support.
4. Baselines and scenarios.
5. Fixtures and expected outcomes.
6. Results, including null/unstable findings.
7. Limitations and transfer gaps.
8. User study sample and protocol.
9. Reproducibility instructions.
10. Prohibited interpretations.
