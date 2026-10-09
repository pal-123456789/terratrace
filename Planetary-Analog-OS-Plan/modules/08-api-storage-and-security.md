# 08 — API, Storage, Security, and Reliability

## v0.1 rule

There is no public server-side API in the canonical competition release. Static artifacts are an intentional security and reliability decision.

## Future API domains

| Domain | Example route | Operation |
|---|---|---|
| Studies | `/v1/studies/{study_id}` | Read approved study package metadata |
| Profiles | `/v1/profiles/{profile_id}` | Read mission task/requirement profile |
| Terrain units | `/v1/terrain-units/{unit_id}` | Read approved metadata/geometry |
| Comparisons | `/v1/comparisons/{run_id}` | Read result, scenarios, and evidence refs |
| Evidence | `/v1/claims/{claim_id}/evidence` | Resolve lineage |
| Protocols | `/v1/protocols/{protocol_id}` | Read/export draft or approved protocol |
| Outcomes | `/v1/outcomes/{outcome_id}` | Read controlled outcome record |

### API rules

- GET routes expose only approved records.
- Mutations require authentication, role authorization, schema validation, reason, and audit event.
- Sensitive location geometry is returned by policy, not by default.
- Every response includes `schema_version`, `evidence_status`, `generated_at`, and `data_freshness`.
- No endpoint claims “best site” without profile, method, evidence, and scenario identifiers.

## Storage model

### Transactional store

PostgreSQL/PostGIS in H1 for:

- users/organizations;
- studies/profiles;
- terrain-unit metadata;
- geometry and governance status;
- evidence nodes/edges;
- reviews and approvals;
- outcome records.

### Object store

Immutable versioned objects for:

- source-derived artifacts;
- rasters/tiles where rights permit;
- Parquet tables;
- study packages;
- evaluation reports;
- media and documentation builds.

### Catalog layer

STAC/OGC-compatible metadata where the provider permits it. A catalog record is not a rights grant; source terms remain attached.

## Security model

### v0.1

- No accounts.
- No secrets in client bundle.
- Static content security policy.
- Dependency pinning and lockfiles.
- Secret scanning in CI.
- Link and dependency audit.
- Sanitize URL parameters and export fields.
- No third-party analytics by default.

### H1

- SSO/OIDC for institutional users.
- Organization/tenant isolation.
- RBAC/ABAC for study, source, site, and outcome records.
- Data classification: public, internal, restricted, sensitive.
- Encryption in transit and at rest.
- Audit log for every mutation and approval.
- Retention and deletion policy that preserves scientific history without exposing sensitive records.

### Threat model

| Threat | Impact | Control |
|---|---|---|
| Malicious export injection | Misleading or unsafe report | Escape values, safe templates, content validation |
| Source tampering | Invalid scientific result | Checksums, immutable artifacts, signed release manifest |
| Unauthorized sensitive site exposure | Community/legal/ecological harm | Geometry policy, role review, redaction/generalization |
| Supply-chain dependency attack | App/pipeline compromise | Lockfiles, scanning, minimal dependencies, provenance |
| Fake evidence update | False transfer claim | Pre/post versioning, approval roles, audit trail |
| API abuse | Cost/data leak | Authentication, quotas, async jobs, rate limits |
| Prompt injection in source documents | Wrong AI extraction | Treat documents as untrusted, source-bound extraction, human approval |
| Availability failure | Demo/research interruption | Static package, cache, offline mode, immutable release |

## Reliability targets

### v0.1

- Canonical demo works with live network disabled after asset load.
- Static release has a published checksum.
- CI builds from clean checkout.
- Broken artifact fails closed with an explicit diagnostic.
- Unsupported data yields `NOT_COMPARABLE`, never a fallback number.

### H1 draft SLOs

| Service | Target |
|---|---:|
| Approved study metadata read | 99.5% monthly |
| Evidence resolution read | 99.5% monthly |
| Async job acceptance | 99.0% monthly |
| Study package integrity | 100% checksum verification |
| Critical data-loss recovery | RPO ≤24 h |
| Platform restoration | RTO ≤8 h |

These are design targets, not current operational claims.

## Job execution

Scientific computation is asynchronous:

```text
POST job specification
→ validate sources/rights/profile
→ enqueue immutable job
→ execute pinned environment
→ write artifact + logs + checksums
→ run validation
→ publish candidate result
→ review/approve
```

A job cannot overwrite an approved result. It creates a new version.

## Cost controls

- Cache identical source/product transformations.
- Deduplicate by source hash and method configuration.
- Use compact feature artifacts for UI.
- Make expensive runs explicit with estimated compute/data cost.
- Apply quotas by organization/project.
- Never make users pay for hidden repeated recomputation caused by non-versioned data.

## Disaster recovery

Maintain:

- immutable source/product manifests;
- replicated study packages;
- database backups;
- object-store versioning;
- schema migration history;
- restore drills;
- public release snapshots;
- exportable organization data.

A platform that cannot export a study package is not a trustworthy evidence system.
