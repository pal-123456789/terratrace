# Limitations and claim firewall

TerraTrace is a **map-scale morphology screening** prototype. These boundaries are
load-bearing: the tool's credibility depends on not exceeding them.

## It may claim

- Comparison of declared map-scale terrain observables at a stated common support.
- Transparent, provenance-traceable morphology distances with uncertainty/sensitivity.
- A draft research-study protocol describing what to measure next.
- A tie / indeterminate / not-comparable / blocked result when evidence is insufficient.

## It must not claim

- Rover traversability, safety, obstacle avoidance, traction, slip, or sinkage.
- Visual-localization or autonomy performance.
- Geological or mechanical equivalence between an Earth site and Mars.
- Field access, permits, ecological approval, or operational feasibility.
- Mission readiness, landing-site suitability, or communications/power performance.
- NASA endorsement or official status, or a prediction of mission outcome.

## Data limitations

- MOLA 463 m is the limiting support; no sub-support (rock/obstacle-scale) claims.
- Copernicus is a surface model (includes vegetation/buildings) and encodes open water
  as 0 m; always check zero-fraction and mask or choose land AOIs.
- Local azimuthal-equidistant reprojection suits bounded AOIs; very large or
  extreme-latitude AOIs need an area-appropriate projection.
- No field or simulation outcome data exists yet, so no transfer-performance claim is
  made or validated.

## Numerical policy at an undefined normalisation

The axial fractional distance measures a candidate against the reference's own magnitude,
`|value − reference| / |reference|`. A reference descriptor can legitimately be exactly 0 — class and
landform fractions do — and the ratio is then undefined. The policy is fixed in
`decision.axial_fractional_distance`, and it is deliberately **not** an epsilon: an exact both-zero
agreement is a distance of 0.0, and a zero reference against a non-zero value **refuses**, raising
`UndefinedNormalisation`, as does any non-finite input.

The refusal exists because the Pareto rule excludes any unit carrying a non-finite distance. A NaN would
therefore not fail here — it would compare fewer units and return a ranking over them, with nothing in
the output to say a candidate had been dropped. No published comparison is affected: every declared
lunar and Mars decision axis is strictly positive on real terrain, and the Mars study path normalises by
the reference's robust scale (p90−p10) rather than by its value.

## Governance

A terrestrial analog site is a governed place. Public remote-sensing data does not grant
field access or permission to publish exact coordinates. Access, ecological, community,
and safety status must be verified before any fieldwork; unverified status is treated as
not permitted.

## Event compliance

NASA Space Apps 2026 runs 14–15 November 2026. The official rule, quoted verbatim in
`EVENT-ALIGNMENT.md`, prohibits *beginning work on the challenges* before the hackathon. This repository
is published prior art, and the artefact submitted is the in-window work that **extends** it — the
pre-event state and the 30 in-window commits are both listed, with dates, in
`EVENT-WINDOW-CONTRIBUTION.md`.

That is the **submitter's reading** of the rule, taken on 2026-11-15 and recorded with an explicit
statement of what it does not assert, in `event/eligibility-evidence.md`. The organizer has **not** been
asked. Nothing here claims confirmed eligibility. See `CLEAN-ROOM-NOTE.md`.
