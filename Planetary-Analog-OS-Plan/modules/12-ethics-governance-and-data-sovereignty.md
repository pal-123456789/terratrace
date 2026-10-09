# 12 — Ethics, Governance, and Data Sovereignty

## Principle

An Earth analog is a lived, governed place, not a blank pixel field. Public remote sensing does not grant permission to visit, publish exact coordinates, or conduct experiments.

## Governance dimensions

Each terrain unit has separate states for:

- public-data availability;
- data redistribution rights;
- coordinate sensitivity;
- land ownership/authority;
- field access permission;
- Indigenous or local governance relevance;
- community consultation status;
- protected-area status;
- environmental impact review;
- physical safety review;
- research ethics requirements;
- publication restrictions;
- benefit-sharing or local-partner agreement.

Possible values:

```text
VERIFIED_ALLOWED
VERIFIED_RESTRICTED
REQUIRES_AUTHORIZATION
UNKNOWN
NOT_APPLICABLE_WITH_EVIDENCE
```

`UNKNOWN` is never displayed as allowed.

## Field planning checklist

Before a proposed physical campaign:

1. Identify land/territorial authority.
2. Obtain written access approval.
3. Determine Indigenous/community governance and consultation requirements.
4. Complete environmental impact and seasonal checks.
5. Define route footprint and disturbance controls.
6. Specify waste, restoration, and contamination management.
7. Verify emergency response and field safety.
8. Confirm data ownership, consent, publication, and retention.
9. Determine whether exact coordinates should be generalized.
10. Share outcomes and benefits with local partners.

The v0.1 protocol is a draft and must say authorization remains outstanding unless recorded evidence proves otherwise.

## Sensitive information policy

- Never publish sensitive coordinates by default.
- Support generalized geometry or delayed release.
- Separate public map layers from restricted site geometry.
- Store consent/status metadata without exposing confidential details.
- Record source terms for all derived data.
- Make takedown/update paths clear.

## Data sovereignty

Future institutional deployments must allow:

- regionally hosted data;
- local custodian control;
- policy-based export;
- attribution and lineage preservation;
- access logs;
- controlled cross-border sharing;
- private study packages;
- open derived artifacts only where authorized.

## Ethical review model

Review lanes:

| Review lane | Reviewer | Veto scope |
|---|---|---|
| Scientific | Planetary/geospatial/domain expert | Metric validity, claim interpretation |
| Site governance | Land authority/community/site steward | Location disclosure and field-use representation |
| Environmental | Qualified environmental reviewer/authority | Disturbance, seasonal, protected-area issues |
| Safety | Field operations lead | Physical activity/vehicle/risk protocol |
| Data rights | Data steward/legal reviewer | Licensing, redistribution, personal/sensitive data |
| Product claims | Product/science lead | Public messaging and release maturity |

No one review substitutes for another.

## International design

- Do not use US-specific permission assumptions globally.
- Preserve local names and source-language context.
- Offer metric units and ISO dates by default.
- Build translation-ready labels.
- Use local institutions as co-designers and beneficiaries.
- Avoid ranking regions by “Mars likeness” in a way that stigmatizes or commodifies communities.
- Do not turn the future network into an ungoverned marketplace.

## Responsible site-network growth

A future site network requires:

- opt-in site participation;
- benefit-sharing model;
- controlled coordinate disclosure;
- data owner/custodian roles;
- governance charter;
- dispute/takedown process;
- publication and attribution rules;
- environmental and community review;
- transparent site suitability maturity levels.

## Maturity labels

```text
REMOTE-SENSING CANDIDATE
RESEARCH-DOCUMENTED TERRAIN UNIT
SITE-ACCESS STATUS VERIFIED
AUTHORIZED STUDY SITE
FIELD-TESTED UNDER PROTOCOL X
TRANSFER OUTCOME REVIEWED
```

Never skip a label based on inference.
