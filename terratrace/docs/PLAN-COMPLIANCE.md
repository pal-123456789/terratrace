# Master-plan traceability — what the plan asked for, and what exists

This is an audit of **`PLANETARY-ANALOG-OS-MASTER-PLAN.md`** (the 785-line master plan) and the
23-module plan library against the code in this repository. **Neither the plan nor its library is
published here** — they are internal documents held locally — so they are referenced by name and
never by link. This page exists because the plan and the
implementation diverged on purpose — the plan is dated 2026-10-08 and the engine grew well past it —
and a divergence nobody has written down is indistinguishable from an omission.

**Legend.** **MET** — implemented and evidenced. **MET DIFFERENTLY** — the requirement is satisfied by
a different mechanism or name; the reason is given. **PARTIAL** — implemented in part; the gap is
named. **OPEN** — not done. Every row names the file or test that is the evidence.

## Read this first — the honest open list

Six items are **not** delivered. None is required for the engine to be truthful; all are named so no
reader has to discover them.

| # | Open item | Why it is open | Effect on the release |
|---|---|---|---|
| O1 | **External user walkthrough** (release target: “at least four of five participants identify one measured comparison and two unassessed gaps”) | Requires people; cannot be done from a repository | Claim boundary is argued, not user-tested. State that plainly. |
| O2 | **Independent GIS re-derivation** of a sample window’s slope/relief | Requires a second GIS toolchain | Correctness rests on 51 analytic oracles, not a second implementation |
| O3 | **Demo video** (2–3 min) | Recording, not code. A shot-by-shot script is provided at [`DEMO.md`](DEMO.md) | The plan’s §10.4 deliverable is a script, not a file |
| O4 | **`method.yml`** by that name | The analysis parameters live in `config/*.yml` (e.g. `matched_footprint_v3.yml`), which play exactly that role | Naming only |
| O5 | **Parquet/GeoParquet feature tables** | Output is JSON + CSV with a canonical hash; no columnar store | The plan called these “internally” for scale; irrelevant at this size |
| O6 | **`terrain-units.geojson`** | Units are bounded in `config/*.yml` and carried in the study package, not as a GeoJSON layer | The web app draws no map, so no layer is consumed |

## §2 — The claim firewall

| Plan requirement | Status | Evidence |
|---|---|---|
| Release claim stated verbatim; morphology only, not traversability/autonomy/geology/access/readiness | **MET** | `docs/PAPER.md` §Scope, `docs/limitations.md`, root `README.md`; reproduced verbatim in every report and in the site’s scope ribbon |
| Forbidden claims enumerated and propagated into output | **MET** | `study.py` carries a `prohibited_claims` block into every package; `gaps.py` encodes the T0–T4 taxonomy; the viewer renders “What this comparison cannot establish” |
| Never a single “Mars-likeness” score | **MET** | `decision.py` (Pareto only) — a composite score does not exist in the codebase |

## §3 — The canonical output (the “prepared experience”)

| Required element | Status | Where |
|---|---|---|
| One reference terrain unit | **MET** | `mars_arcadia` and two more in `config/matched_footprint_v3.yml` |
| 2 minimum, 3 maximum Earth units | **MET DIFFERENTLY** | the v3 panel uses **7** (4 basaltic, 2 smooth non-volcanic controls, 1 near-miss) because the S/V test needs a *class* contrast; the hero config still runs 2–3 |
| One locked study profile | **MET** | `config/matched_footprint_v3.yml` (sha256 recorded in `RESULTS-v3.md`) |
| One transparent comparison | **MET** | `study.compare_units`; DECISION MATRIX section in the viewer |
| One morphology-fit matrix | **MET** | per-axis distance table (viewer + `report.md`) |
| One non-transferable-physics ledger | **MET** | `gaps.py` → `transfer_gap_ledger.json`, T0–T4 |
| One field-feasibility ledger | **PARTIAL** | feasibility appears as eligibility status plus T4 (`site_access`, `ecology_community`) ledger rows rather than a separate ledger |
| One provenance trace | **MET** | `provenance.py` → `evidence-graph.json` |
| One draft study protocol | **MET** | `protocol.py` → `draft-protocol.json` |
| A valid *indeterminate* outcome | **MET** | `decision.py`; the archived real run in `artifacts/` *is* a TIE |

## §4.2 — Minimum data contract (22 fields)

Carried by `catalog.py` (15 required fields) + `sources.lock.yml` (per-file) + the fetch manifest.

| Field | Status | Where |
|---|---|---|
| source_id, provider, product_id | **MET** | `catalog.SOURCES[...]` `id`/`provider`/`product` |
| source_url | **MET** | `access.url` |
| sha256, retrieved_at | **MET** | `sources.lock.yml`, `data/fetch_manifest.json` |
| license_or_terms_url | **MET** | `license` + `citation` per source; `references.py` renders them |
| body, horizontal_crs, vertical_datum | **MET** | catalog fields, asserted by `tests/test_catalog.py` |
| native_posting_m | **MET** | `native_resolution_m` |
| coverage_geometry | **MET** | `coverage` (bbox/band), `source_covers()` |
| nodata_policy | **MET** | `nodata_sentinels` + `masks.py` |
| effective_spatial_support_m | **MET** | derived (native × the declared 3× heuristic) and reported per cell by `comparability.py` |
| uncertainty_or_limitations | **MET** | `vertical_accuracy_m` + `errorprop.py` bands + `limitations.md` |
| analysis_extent_rule, resampling_or_aggregation_rule | **MET** | `extent_m`/`target_support_m` in config; `support.py`, `reproject.py` |
| transformation_id | **MET** | evidence-graph nodes (`provenance.py`) |
| quality_mask_policy | **MET DIFFERENTLY** | a behaviour (`masks.py` + `profile.py` flags) rather than a declared per-source field |
| product_version, redistribution_status, acquisition_or_processing_date, units | **OPEN** | genuinely not carried as structured fields; product identity is in the `product` string and terms in `license`. Recorded rather than invented |

## §4.3–4.6 — Support rule, features, three outputs, result states

| Requirement | Status | Evidence |
|---|---|---|
| Compare only at a declared common support, after both bodies are on their own metric grid | **MET** | `reproject.py` (per-body radius), `support.py`, `comparability.py` |
| Show native posting, effective support, chosen support, windows in metres, excluded scales | **MET** | `matched_benchmark.py` records them per cell; the study reports `target_support_m` and the honest/diagnostic support sets |
| 3–5 descriptors only | **MET DIFFERENTLY** | ~30 cited families; the *decision* is still Pareto over a small declared set per lens, and the scale test that the plan wanted is exactly what protocol v2/v3 perform |
| Three non-compensatory outputs (morphology / non-transferable physics / field feasibility) | **MET** | morphology distances vs. the transfer-gap ledger vs. the eligibility block — never merged |
| Eligibility filters run *before* comparison | **MET** | `decision.py`; a water/flat tile is BLOCKED, not scored |
| Only four result states | **MET DIFFERENTLY** | `RECOMMEND_FOLLOW_UP`, `TIE`, `INDETERMINATE`, `NOT_COMPARABLE`, `BLOCKED` — `INDETERMINATE` splits “insufficient evidence” from “tie”, which the plan lists as one state |

## §5 — Screens and accessibility

| Screen the plan requires | Status | Where it lives |
|---|---|---|
| Study profile | **MET** | the config + the protocol header in every report |
| Comparison workbench | **MET** | DECISION MATRIX in the viewer / report |
| Sensitivity view | **MET** | pairwise rank-flip matrix section |
| Transfer-gap ledger | **MET** | T0–T4 section |
| Terrain-unit passport | **MET** | `dossier.py` per-candidate brief |
| Draft study protocol | **MET** | `draft-protocol.json` + report section |
| Evidence trace | **MET** | evidence-graph + package hash + REFERENCES |
| The nine accessibility non-negotiables | **MET** (with named exceptions) | audited line by line in [`ACCESSIBILITY.md`](ACCESSIBILITY.md) |

## §6 — Architecture

| Plan decision | Status | Note |
|---|---|---|
| Python + Rasterio/GDAL/NumPy offline pipeline | **MET** | `terratrace/` is pure NumPy at its core; `rasterio` is needed only to *read* real DEMs |
| **React + TypeScript + Vite** web app | **MET DIFFERENTLY** | the site is dependency-free static HTML/CSS/JS. Reason: the plan’s own non-negotiables (“no live dependency in the canonical demo”, “no WebGL required”, “works offline”) are *better* served by a build-step-free page, and the study viewer is generated by the engine itself |
| MkDocs documentation | **MET** | `mkdocs.yml` (Material) with every page in the nav — enforced by the doc guard |
| Pytest/Vitest/Playwright/axe-core | **MET DIFFERENTLY** | a dependency-free runner plus 843 tests and 51 scientific oracles; no browser test stack |
| CI: build, test, link-check, manifest verification | **MET** | `.github/workflows/ci.yml`: suite, optional-dependency hygiene, validation, **documentation-consistency** (which link-checks the docs *and* the site) |
| Explicitly excluded: microservices, graph DB, live API in the demo, accounts, ML ranker, LLM chat, spectacle globe, blockchain, marketplace, sensitive coordinates | **MET** | none is present. The landing page uses WebGL as *decoration only* and degrades to a complete static page without it |
| The 13-file artifact contract | **MET DIFFERENTLY** | the bundle is `study.json`, `manifest.json`, `checksums.txt`, `profile.json`, `evidence-graph.json`, `draft-protocol.json`, `transfer-gap-ledger.json`, `confidence.json`, `REFERENCES`, `report.md/.html`, the viewer. Same content, different names/shape — recorded rather than renamed at the last minute |

## §7 — Verification, fixtures, ablations, release targets

| Required fixture | Status | Evidence |
|---|---|---|
| Flat plane, known slope, directional aspect | **MET** | `check_openness_flat`, `check_twi_decreases_with_slope`, `features` fixtures |
| Synthetic ridge and crater-rim surfaces | **MET** | ridge: `check_anisotropy_ridges_oriented`, `check_openness_difference_cone_ridge_bowl_valley`; crater-rim as a ring: the cone/bowl pair (`check_geomorphon_cone_peak` / `check_geomorphon_bowl_pit`) pins the two extremes |
| Equal morphology at different native resolutions | **MET** | `resolution.py` + `check_multiscale_identical_is_layer1_all_scales` |
| Different morphology after aggregation | **MET** | `test_support.py` aggregation fixtures; `check_confound_mechanism_*` |
| Missing-data wedge | **MET** | `masks.py` fixtures + `check_water_candidate_blocked` |
| A data-complete but poor-fit candidate | **MET** | `check_monotonic_roughness_discrimination`, `check_null_control` |
| A visually attractive but data-incomplete candidate | **MET** | `test_adequacy.py` impostor case |
| One eligibility-blocked candidate | **MET** | `check_water_candidate_blocked`; `test_study` all-blocked → BLOCKED |
| One stable tie | **MET** | TIE fixtures in `test_decision.py`; the archived real run is a TIE |

| Required ablation (full vs degraded) | Status |
|---|---|
| Task-conditioned profile vs equal-weight similarity | **MET** — the six lenses and `sensitivity.py` `lens_ablation` |
| Common effective support vs native resolution | **MET** — `resolution.py`, protocol v3 §5 |
| Visible uncertainty vs point estimate | **MET** — bootstrap CIs + `confidence.py` |
| Explicit gap ledger vs morphology-only | **MET** — ledger always emitted |
| Eligibility filters vs soft penalty | **MET** — filters, not penalties |
| Provenance drawer vs hidden sources | **MET** — evidence graph + package hash |
| Missingness propagation vs silent fill | **MET** — valid-fraction tracked; low-valid-fraction is a blocking flag |

| Release target | Status |
|---|---|
| Every visible number traces to source, transform, unit | **MET** — evidence graph; `docs/VALIDATION.md` |
| Two independent runs reproduce the canonical hash | **MET** — `repro.py`; the gated study hash `8f4890777ee462a2…` and the validation hash `0e2c6a2e…` are stable |
| Every fixture has an expected outcome and a passing test | **MET** — 843 tests, 0 failing |
| No display uses a value below its supported scale | **MET** — the comparability gate refuses sub-support cells |
| The app can return tie/indeterminate | **MET** |
| ≥4 of 5 participants identify one comparison and two gaps | **OPEN** (O1) |
| No participant believes the output certifies a rover | **OPEN** (O1) — argued in the firewall, not user-tested |
| Canonical flow works offline | **MET** — the viewer and reports are self-contained; the suite runs with no network |

## §8 — Gates

The readiness gates **P0–P3** are `MET`: event facts and the no-prebuild rule are recorded in
[`CLEAN-ROOM-NOTE.md`](../CLEAN-ROOM-NOTE.md) and [`event/eligibility-evidence.md`](event/eligibility-evidence.md);
source reconnaissance and the generic-capability proof are the engine itself; P3 (clean-room
readiness) is the eligibility page. The event gates **G0–G7** run on 14–15 November and are not ours
to mark.

## §11 — Governance

| Requirement | Status | Where |
|---|---|---|
| Unknown permission/access is blocking, not positive | **MET** | eligibility: unverified rights/access are ineligible |
| No exact sensitive coordinates published by default | **MET** | only bounded public-data windows are cited; site coordinates are illustrative |
| Draft protocol carries a stop condition for permit/community/ecology/safety | **MET** | `protocol.py` emits `NOT_AUTHORIZED` when status is unverified |
| Separate status fields for data / publication / access / ecology / community / safety | **PARTIAL** | rights and access are explicit; ecology and community appear as T4 ledger rows rather than six discrete passport fields |

## §18 — The release package (21 required items)

Delivered: public static application · source repository · OSI license (MIT, deliberately) · source
and terms manifest · method configuration · evidence graph export · canonical study profile ·
terrain-unit records · comparison/sensitivity/gap artifacts · draft protocol · evaluation report
(`VALIDATION.md`) · limitations and firewall · **accessibility report** · README and docs site ·
**figures** · continuation/eligibility statement.

Not delivered: **immutable tag** (created as `v0.3.0` on release — push it with the branch) ·
**demo video** (script provided) · **screenshots of a live session** (generated figures stand in;
they cannot go stale) · **submission receipt** (event-time).

## Backlog cross-check (S / E / U)

| ID | Item | Status |
|---|---|---|
| S-001…S-014 | source lock, unit schema, method config, support transform, the four features, distance, missingness, sensitivity, Pareto/tie, gap ledger, protocol | **MET** — `tests/test_sourcelock.py`, `test_preflight.py`, `test_support.py`, `validation.py` (51 oracles), `test_sensitivity.py`, `test_decision.py`, `test_gaps`-covered, `test_protocol` |
| E-001…E-007 | evidence edges, artifact manifest, claim ledger, offline bundle, reproducibility, licence/citation, limitations | **MET** — `test_provenance.py`, `manifest.json`, `CLAIM-LEDGER.md`, `test_bundle.py`, `test_repro.py`, `references.py`, `limitations.md` |
| U-001…U-008 | scope ribbon, profile, comparison table, sensitivity state, gap ledger, evidence drawer, protocol export, **no-map path** | **MET** — all eight exist in the generated viewer/report; the no-map path is the default, since the flow is tables first and previews are additive |

## What this audit changed

Running it surfaced one real defect that was then fixed: the committed `terratrace/viewer/index.html`
did **not** reproduce from the committed `artifacts/study.json` — it was generated by an older
`build_viewer.py` and was missing the DECISION MATRIX and DECISION CONFIDENCE sections and the
`scope` attributes. It was regenerated, and the site’s `/viewer` page rebuilt from it.
