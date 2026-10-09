# 10 — AI/ML Policy

## Decision

**No machine-learning ranking model in TerraTrace v0.1.**

The product does not have a labeled corpus of terrain-transfer outcomes. An ML ranker would create an impressive interface while hiding assumptions and claiming generalization from no ground truth.

## Allowed AI uses

| Use | Allowed behavior | Required control |
|---|---|---|
| Requirement extraction | Suggest structured fields from source text | Human confirmation; source passage attached |
| Evidence retrieval | Find relevant source passages/products | Results cite exact source; no autonomous claim |
| Developer assistance | Draft tests/docs/schema | Human review and test gates |
| Ontology suggestion | Propose mappings/terms | Reviewer approves canonical vocabulary |
| Study-summary drafting | Summarize already approved evidence | Fact-bound prompt; claim audit |

## Prohibited v0.1 uses

- Opaque analog score.
- LLM-generated scientific conclusion without structured evidence.
- Invented source, dataset, partner, or result.
- Autonomous site recommendation that bypasses constraints.
- Synthetic evidence represented as field observation.
- AI-generated “confidence” with no calibration.

## Future model admission gate

A learned model can enter ranking only when:

1. A labeled outcome or expert-judgment dataset exists.
2. Labels have provenance and disagreement records.
3. Train/test split prevents geography/task/site leakage.
4. Transparent baseline exists.
5. Model beats or adds value to baseline on a predeclared metric.
6. Calibration and uncertainty are reported.
7. Errors are stratified by terrain/product/task.
8. Users can inspect evidence and model contribution.
9. Model version and training data are immutable.
10. A human review path exists for high-impact results.

## Future model architecture

Potential staged experiments:

- retrieval model for source/experiment discovery;
- interpretable task-to-feature weighting with expert priors;
- calibrated ranker trained on study outcomes;
- active-learning selector for experiments that reduce uncertainty;
- multimodal model only after cross-sensor alignment and ground truth.

## AI evaluation metrics

Do not use accuracy alone. Consider:

- calibration error;
- ranking agreement;
- pairwise preference accuracy;
- abstention quality;
- evidence citation precision;
- unsupported-claim rate;
- performance by terrain type and task;
- human correction burden;
- outcome utility.

## Prompt/source safety

Treat every external document, dataset description, and field note as untrusted content. A document can contain instructions that are irrelevant or malicious. The system extracts evidence into a typed schema; it never executes document instructions.

## Model card requirement

Any future model ships with:

```text
intended use
out-of-scope use
training data
label policy
geographic/task coverage
known failures
uncertainty/calibration
human review policy
version/checksum
evidence and citations
```

## Product principle

“AI” is not a product category. A model enters only where it reduces a measured bottleneck without lowering evidence quality.
