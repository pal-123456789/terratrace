# Event eligibility evidence — NASA Space Apps 2026

**Purpose.** The official 2026 Challenge runs **November 14–15, 2026**. Official guidance permits
preparation and data exploration beforehand but says teams may not develop the solution they intend to
submit before the event begins. This repository is therefore published as **open-source prior art and a
working research tool**, not as a pre-built submission. This page records the position and the evidence
trail, so the stance is auditable rather than assumed. The full statement is in
[`CLEAN-ROOM-NOTE.md`](../../CLEAN-ROOM-NOTE.md).

## Standing position

**This repository is published prior art** — a public, MIT-licensed project whose commit history is the
proof of what existed and when. It is not presented as having been created during the event, its history
is not disguised, and it claims no NASA endorsement or official status. This is the precondition of
option 1 below, and it is the position the READMEs and this repository already state.

## Decision record

Before any submission that reuses this work, record here **which path is taken** (options are in
`CLEAN-ROOM-NOTE.md`):

- [ ] **Option 1 — fresh build.** During Nov 14–15 a new event project is built within the window, and
      this repository is relied upon as public prior work (cited by name and commit), as one would rely
      on any public library or paper.
- [ ] **Option 2 — written clarification.** The organizer has been asked whether continuing a public
      project is eligible, and the written answer is kept here (paste it below) before submitting.

**Recorded:** *(date and decision — to be filled in at the event)*
**Evidence attached:** *(link or quote of the organizer's written answer, if option 2)*

## What this repository is, and is not

- **Is:** a public, reproducible research/production project — the Planetary Analog OS
  morphology-transfer nucleus, its frozen benchmark protocols, and their results, with every data
  source cited and every claim mapped to evidence.
- **Is not:** the submitted artefact, and not NASA-endorsed. It makes no traversability,
  geologic-equivalence, site-access, or mission-readiness claim.

## Evidence trail

| Item | Where |
|---|---|
| Public commit history — dates are the record of what existed when | `github.com/pal-123456789/terratrace` |
| Clean-room statement | [`CLEAN-ROOM-NOTE.md`](../../CLEAN-ROOM-NOTE.md) |
| Frozen protocols and their results (v1 → v3) | `docs/BENCHMARK-PROTOCOL.md`, `-v2.md`, `-v3.md`; `docs/RESULTS-v2.md`, `docs/RESULTS-v3.md` |
| Claim-to-evidence ledger (every claim → an experiment, status, falsifier) | `docs/CLAIM-LEDGER.md` |
| Licence (MIT) | `LICENSE` |
| Data terms and required citations | `REAL-DATA-RUNBOOK.md`, `sources.lock.yml` |

## Always

- Cite every data source and third-party asset.
- Keep original project content under an OSI-approved licence (MIT here).
- State the scope/claim firewall in any submission exactly as in the README.
