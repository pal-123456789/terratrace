# 05 — Transfer Gap and Uncertainty

## Core distinction

Similarity is not transferability. Transferability is not validation. Validation is not operational certification.

TerraTrace uses a matrix, not a single gap number.

## Transfer-gap matrix

| Gap category | Earth morphology comparison | v0.1 representation | Future evidence required |
|---|---|---|---|
| Gravity | Not reproduced | Non-transferable ledger | Physics model, reduced-gravity experiment, outcome evidence |
| Atmosphere/pressure | Not reproduced | Non-transferable ledger | Controlled chamber/mission model |
| Regolith mechanics | Not inferred from DEM | Unassessed | Material characterization, wheel-soil tests |
| Dust/electrostatics | Not reproduced | Non-transferable/unknown | Dedicated measurements and chamber work |
| Radiation | Not reproduced | Non-transferable | Radiation test program |
| Thermal cycle | Not inferred from terrain | Unknown | Thermal/environmental data and hardware tests |
| Illumination | Context only unless source supports it | Conditional metadata | Sensor/illumination experiment |
| Communications | Not inferred | Non-transferable/unknown | Link/relay/orbit model |
| Topographic morphology | Comparable at declared support | Scored if eligible | Higher-resolution/ground truth |
| Site access | Not inferable from imagery | Hard status field | Authority/community confirmation |
| Ecological impact | Not inferable from terrain | Hard status field | Impact assessment |
| Reproducibility | Protocol-dependent | Protocol requirement | Repeated authorized study |

## Transferability classes

Each requirement receives one class:

```text
T0  Comparable observable at declared support
T1  Potentially informative but context-dependent
T2  Non-replicable physical condition
T3  Unknown because data/support/evidence is insufficient
T4  Requires authorized field or laboratory experiment
```

No T2/T3/T4 item is silently converted into T0.

## Uncertainty dimensions

Uncertainty is multidimensional:

1. **Measurement uncertainty** — source error or documented accuracy.
2. **Support uncertainty** — effective spatial/temporal support not fully known.
3. **Processing uncertainty** — transform, resampling, mask, and parameter sensitivity.
4. **Sampling uncertainty** — finite AOI/sample distribution.
5. **Semantic uncertainty** — whether a metric means what the mission user thinks it means.
6. **Transfer uncertainty** — whether a terrestrial observation informs an off-world behavior.
7. **Governance uncertainty** — rights/access/ecology/community status.

The UI must not collapse these into one percentage unless a defensible model exists.

## Sensitivity reporting

For scenario set \(\Omega\), show:

- feature range;
- pairwise rank-flip frequency;
- Pareto-set membership frequency;
- missingness state changes;
- source/support status changes;
- confidence category.

A simple robust membership measure is:

\[
P_{nd}(i)=\frac{1}{|\Omega|}\sum_{\omega\in\Omega}
\mathbf{1}[i\text{ is non-dominated under }\omega]
\]

This is a scenario frequency, not a probability of physical truth. Label it **scenario membership frequency**.

## Robustness classes

| Class | Rule | Display |
|---|---|---|
| Stable | Result state unchanged across declared scenarios | “Stable under tested assumptions” |
| Sensitive | Rank/eligibility changes under one or more reasonable scenarios | “Sensitive; inspect assumptions” |
| Indeterminate | No defensible ordering | “Insufficient evidence to choose” |
| Blocked | Critical data/rights/quality condition missing | “Blocked; resolve evidence first” |

## Transfer-gap report template

```markdown
## What this comparison supports
- [observable] at [physical window] from [source/product]
- [morphology statement] under [configuration]

## What it does not support
- [physics/operations claim] because [reason]
- [resolution-limited claim] because [reason]

## Conditions that could change the result
- [support/resampling]
- [AOI boundary]
- [missingness]
- [source version]

## What to measure next
- [study/lab/field measurement]
- [acceptance threshold]
- [required authorization]
```

## High-value refusal behavior

If a user requests “the most Mars-like site,” the product responds:

> “No universal answer is scientifically defensible from this study. Here are the non-dominated candidates for your declared morphology profile, the assumptions that change their order, the physics not represented, and the next measurement needed.”

That refusal is the category’s trust mechanism.

## Future calibration

Only after collecting pre-test and post-test records should PAOS consider calibrated transfer recommendations. A future record needs:

```text
pre_test_requirement
pre_test_site_features
pre_test_transfer_assumptions
protocol_version
observed_outcome
outcome_quality
environmental_context
failed_or_successful_transfer_claims
review_status
```

Then evaluate calibration, not just ranking accuracy:

- reliability diagrams;
- Brier score where probabilistic labels are legitimate;
- held-out task/site evaluation;
- error by terrain class and sensor regime;
- negative-result preservation.

Until then, no ML transfer predictor.
