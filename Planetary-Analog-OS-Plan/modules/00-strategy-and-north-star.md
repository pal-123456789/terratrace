# 00 — Strategy and North Star

## Thesis

Planetary Analog OS (PAOS) is a proposed evidence infrastructure for deciding which terrestrial or simulated experiment can support a specific lunar/Martian mission claim, what assumptions are needed for transfer, and what observed result would update confidence in that transfer.

### Category statement

> **A mission-to-field evidence operating layer for planetary exploration.**

It is not a “Mars finder.” It is not an authoritative mission decision-maker. It makes analog claims inspectable, comparable, and experimentally updateable.

## Why this problem matters

Space missions rely on tests and analogs because mission hardware and operations cannot be fully exercised in their target environment before launch. Yet “analog” is overloaded: visual resemblance, geologic similarity, environmental similarity, operational similarity, human-factor similarity, and demonstrated transfer are not the same thing.

A failure to distinguish these can create:

- wasted field campaigns;
- overconfident transfer claims;
- repeated experiments with incompatible metadata;
- inability to compare results across institutions;
- knowledge trapped in reports and unstructured logs;
- weak provenance from mission assumption to test result.

PAOS attacks the **evidence discontinuity**, not the impossibility of making Earth identical to another world.

## Strategic product layers

```text
L0  Source integrity       Exact source, version, rights, coverage, quality
L1  Mission ontology       Task → requirement → observable → threshold
L2  Analog comparison      Comparable attributes at declared support
L3  Transfer gap           Non-replicable physics and operational differences
L4  Experiment design      Protocol, measurements, criteria, constraints
L5  Outcome capture        Field/simulation result, context, provenance
L6  Transfer evidence      Calibrated claims from repeated outcomes
L7  Standards/network      Cross-institution interoperability and governance
```

**Competition release:** prove L0–L4 for one narrow case.  
**Institutional product:** operationalize L0–L6 for repeated users.  
**Infrastructure ambition:** establish L7 through adoption, evidence quality, and legitimacy.

## Narrow release thesis

**TerraTrace v0.1:** Mars-only, map-scale terrain morphology comparison for a fixed route-study scenario. It selects bounded terrain units for follow-up research, or returns tie/not-comparable/blocked. It outputs a draft study protocol. It does not estimate rover traversability or validate autonomy.

## North-star metric (long-term)

**Verified Transfer Records (VTR):** number of completed study records that contain (a) predeclared mission requirement, (b) source-locked site and planetary evidence, (c) protocol, (d) observed outcome, (e) uncertainty and limitations, and (f) independent review or reproducibility evidence.

A VTR is not just a data row. It is a quality-gated evidence unit. Long-term metric should be reported by task family, source support, and validation tier; raw count alone invites low-quality submissions.

## Value proposition by stakeholder

| Stakeholder | Value hypothesis | Proof required |
|---|---|---|
| Mission concept team | Reduces time to assemble a defensible analog study and exposes gaps early | Workflow study, expert review, repeat usage |
| University/robotics lab | Makes field experiments reproducible and comparable | Clean-room re-run, protocol reuse, lab adoption |
| Space agency | Provides auditable evidence and controlled workspaces | Security/procurement fit, pilot, governance |
| Site steward/community | Makes constraints visible and controls publication/access | Consent model, data sovereignty, benefit-sharing |
| Educator/public | Teaches the difference between resemblance and transfer | User comprehension and accessibility |
| Robotics vendor | Helps target test conditions and preserve test evidence | ROI and integration studies |

These are hypotheses, not customer endorsements.

## Strategic principles

- Evidence before scale.
- A refusal can be a high-quality result.
- Task-specific validity beats universal similarity.
- Common support and uncertainty are product features.
- Human expertise is integrated, not replaced.
- Community, land access, and ecological constraints are hard data, not decorations.
- Open standards and controlled data can coexist.
- The company’s strongest asset is eventually **validated outcome evidence**, not an AI model.

## Billion/trillion framing

- **Millions in annual revenue:** plausible only after a repeatable institutional pain and paid pilots are demonstrated.
- **Billions in enterprise value:** speculative; would require broad mission/robotics adoption, recurring institutional contracts, strong data network effects, validated outcomes, and trusted governance.
- **Trillions:** do not forecast company value. A standards layer might influence very large future economic activity, but influence/throughput is not revenue or valuation. Do not use this in a competition pitch.

## Three horizons

| Horizon | Deliverable | Stop condition |
|---|---|---|
| Nov 14–15, 2026 | TerraTrace evidence-bounded prototype | Source/support mismatch or pre-event rule breach |
| 0–12 months after | Research kernel with observed or simulated outcomes, expert review, customer discovery | No repeat user or evidence-update loop |
| 1–5 years | Institutional evidence workspaces + governed site/test network | No institutional pull or community legitimacy |
| 5–10 years | Interoperable planetary analog standard and network | No independent adoption, validated transfer records, or governance trust |

## Strategic failure modes

1. Building a map without a decision.
2. Confusing similarity with transfer validity.
3. Treating raster posting as effective physical resolution.
4. Claiming predictive performance without outcome data.
5. Treating field access as implied by remote-sensing data.
6. Using a large TAM slide instead of proving paid workflow value.
7. Calling the prototype an “OS” as if it were already infrastructure.

The branding may use the long-term category. Release copy must call v0.1 a workbench/prototype.
