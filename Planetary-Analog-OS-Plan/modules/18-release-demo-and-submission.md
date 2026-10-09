# 18 — Release, Demo, and Submission

## Release definition

Release is a mutually consistent evidence package, not merely a deployed web app.

## Required package

- public static application;
- source repository;
- immutable tag/commit;
- OSI-compatible code license;
- source and terms manifest;
- method configuration;
- feature definitions and units;
- evidence graph export;
- canonical study profile;
- terrain-unit records;
- comparison, sensitivity, and transfer-gap artifacts;
- draft study protocol;
- scientific/technical evaluation report;
- limitations and claim firewall;
- accessibility report;
- README and docs site;
- screenshots and short video;
- public continuation/eligibility statement;
- submission receipt if submitted.

## README first screen

Order:

1. Product name and one-line purpose.
2. Scope label: “map-scale morphology audit; not rover validation.”
3. Canonical demo link.
4. Distinctive screenshot showing morphology + gap ledger.
5. One measured result from actual pipeline, if validated; otherwise describe a method capability, not an achievement.
6. Documentation/source/evaluation links.
7. Build/test status.
8. Data sources and license notice.

## Submission narrative

### Problem
Analog locations are frequently discussed as if resemblance were enough, while the relevant data, scale, assumptions, and limits are difficult to compare.

### Solution
TerraTrace defines a bounded map-scale study, compares a small number of curated terrain units at common declared support, exposes non-transferable conditions, and outputs a draft study protocol.

### NASA relevance
The challenge asks for identification and characterization of terrestrial analogs using open Earth, Moon, and Mars data. TerraTrace focuses on how to make those comparisons explicit, limited, and actionable.

### Innovation
The central product object is a mission-conditioned evidence package with a built-in refusal state, not a generic visual-similarity map.

### Validity
Validity is demonstrated through source-level metadata, common-support policy, fixtures, independent re-derivation, sensitivity, and exact limitations. No rover performance validation is claimed.

### Impact
The release is an open prototype and reusable method nucleus. It does not claim adopted agency use or measured cost savings.

## Demo consistency checklist

- Every map/table number matches the pinned artifact.
- Video uses the final release build.
- UI labels match docs equations.
- No site is described as field-authorized unless evidence exists.
- No hidden live data changed the capture.
- Source/license attribution is visible.
- Eligibility statement is accurate.
- Text says “draft study protocol,” not “approved test plan.”

## Release manifest

```json
{
  "release_id": "terratrace-v0.1.0",
  "commit": "<commit>"
  ,"created_at": "<UTC timestamp>",
  "event_status": "public-continuation-or-confirmed-submission",
  "study_profile_hash": "<sha256>",
  "source_lock_hash": "<sha256>",
  "artifacts": [{"path": "...", "sha256": "..."}],
  "tests": {"scientific": "pass/fail", "e2e": "pass/fail", "a11y": "pass/fail"},
  "claims_maturity": "prototype_morphology_only",
  "limitations_url": "..."
}
```

Fix JSON syntax before generating an actual manifest: the excerpt above is an illustrative schema and should be validated in the implementation.

## Post-release correction policy

- Never rewrite the evidence history silently.
- Publish a new artifact/version when a source or method changes.
- Link superseded outputs and explain why.
- If a public claim is wrong, remove or correct it promptly and preserve a correction note.
- Preserve null/negative findings.
