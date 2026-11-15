# Event-window contribution record

**Eligibility is NOT confirmed by this page, and it does not claim to be.** It records the evidence so
the decision is made on facts rather than on optimism. What changed on 2026-11-15 is that the record
stopped saying *"the window has not opened"* and started carrying actual commits.

Originally written 2026-11-13, the day before the window opened. Rewritten **2026-11-15** with the git
history, because the earlier version's central table was true when written and false by the morning.

## 1. The rule we are working to

From the official 2026 Participant FAQ, quoted verbatim in
[`EVENT-ALIGNMENT.md`](EVENT-ALIGNMENT.md) §2:

> Resources for each challenge will be published on November 13. Teams **are not allowed** to begin
> working on the challenges **prior to the hackathon**.

The operative clause is *beginning work on the challenges* — not a prohibition on owning prior tools.
Two dates bound it: challenges announced **28 October 2026**, resources published **13 November**, event
**14–15 November**. Timezone of the window, and the treatment of an operator's existing open-source
toolkit, are **not resolved by anything in this repository**. The rule is quoted, not interpreted.

An earlier version of this page quoted a *looser* rule from `CLEAN-ROOM-NOTE.md` ("may not develop the
solution they intend to submit before the event begins"). That paraphrase is not what the FAQ says and
has been replaced with the quotation above.

## 2. The boundary, from git

The event window is 2026-11-14 to 2026-11-15. The last commit **before** it, by its own timestamp:

| fact | value |
|---|---|
| Pre-window tip | `73db823`, **2026-11-13 22:34** (merge of PR #13) |
| Commits inside the window | **29** — 27 ordinary commits and 2 merge commits |
| First in-window commit | `d6ef3a2`, **2026-11-14 00:45** |
| Last in-window commit at the time of writing | `d50b346`, **2026-11-15 01:05** |
| Window diffstat | **104 files changed, +35,814 / −166** |

Every one of those 29 commits is dated, public, and reachable
(`git log --since="2026-11-14 00:00"`), so the boundary is auditable rather than asserted.

## 3. What the window actually produced, classified

The distinction that matters is between work that **created a result** and work that **re-presented
one**. Both happened, and the second is explicitly not a contribution.

### 3a. New experimental and scientific work — inside the window

| commit | time | what it produced |
|---|---|---|
| `d6ef3a2` | 11-14 00:45 | real LOLA lunar terrain ingested for the first time; self-checking counts |
| `d167659` | 11-14 12:01 | the six-site lunar result, an error ensemble, an analytic reprojection check |
| `1426d32` | 11-14 15:43 | **the common-support defect was real** — corrected exact common grid, corrected rerun, and a larger finding than the one it replaced |
| `7d9a9e1` | 11-14 17:41 | the three declared lunar axes **are one axis** — derived analytically and confirmed by measurement |
| `2802e2f` | 11-14 18:59 | a **30-perturbation adversarial stress test**, 30 declared before the run; the panel survives 28 |
| `80bce3c` | 11-14 19:41 | ranking / adequacy / sufficiency **separated as verdicts**, and the lunar panel fails adequacy at every cell |
| `714fec9` | 11-14 19:57 | the projection **validated on all five bodies** against independent closed-form geodesy |
| `3a16f54` | 11-15 00:50 | **the independent-axis probe**: the lunar sole-winner is a property of the Pareto rule, not of a candidate — an arbitrary fourth coordinate moves it in 15.90 of 18 cells, and none of 141 candidate axes beats that control |

Eight substantive entries. Two of them (`1426d32`, `7d9a9e1`) **correct or supersede a pre-event
result**, and one (`3a16f54`) is a negative result about the project's own lunar headline. This is the
strongest form of in-window contribution available: the window changed what the project claims.

### 3b. New artifacts and tooling built inside the window

`957462f` the scale-resolved discovery atlas (six records, 13 reconciliations, refuses to publish on
disagreement) · `d3e55de` the offline evidence page · `e8b823e` a second Earth-DEM mirror with a
fresh-clone provenance check · `cc86fa3` one count everywhere plus a guard for the number it could not
see · `afb0f4e` a cross-platform path-reporting fix · `9cc97e2` a check keeping the lens sets honest
(stated as *distinct*, never *independent*) · `7458862` a submission page and a one-command
verification · `4995477` a CI dependency defect found by CI itself and fixed.

### 3c. Re-rendering and re-packaging — explicitly NOT claimed as contribution

`3ed166f`, `8b399e7`, `80492ff`, `5b6895d` are deck and PDF rebuilds. `d50b346` adds one paragraph and
one button to the site. **None of these is a new scientific contribution** and none is counted as one
above. Re-running a pipeline, re-rendering a figure or re-wording a page produces no new claim.

## 4. Pre-event state — still disclosed, unchanged

The engine, the six decision lenses, the two-body benchmark protocols and their v2/v3 results, the
keyless Copernicus COG Earth path, the test suite and the scientific oracles, the website and the
documentation set **all predate the window**, and committed copies are dated 2026-11-13 or earlier.
None of that is presented as event work, the history is not disguised, and the repository is MIT
licensed and public throughout.

So the honest description of the submission is: **a pre-existing, publicly published research toolkit,
carrying a substantial and dated in-window contribution that includes the correction of one of its own
published results and a new negative result about its own lunar claim.**

## 5. The decision, and why it is still not made here

Two acceptable paths remain, unchanged from the original note:

1. **Extend-in-window.** Submit the project as it stands, with the pre-event state disclosed and the
   in-window commits listed — which is what §2 and §3 now do. This is the path the record supports.
2. **Written clarification.** Ask the organizer whether an operator's existing public toolkit may be
   extended rather than rebuilt, and hold the written answer **before** submitting.

Path 1 is supported by evidence and by nothing else. Path 2 depends on an answer nobody has.

> **The decision is not made, and it must be made by the submitter.** Nothing in this repository is
> confirmation that either path has been accepted by the organizer.

The draft inquiry for path 2 is in `CLEAN-ROOM-NOTE.md`. **It has not been sent.**

## 6. What must NOT happen

- Do not present this codebase as created during the event. It was not; it was extended during it.
- Do not remove or rewrite the public history to disguise its origin.
- Do not claim NASA endorsement or official status.
- Do not count §3c as contribution. Re-rendering is not research.
- Do not treat this page as evidence that eligibility has been confirmed. It is not.

## 7. Status

| item | status |
|---|---|
| Rule recorded | **DOCUMENTED** — quoted verbatim from the official FAQ in `EVENT-ALIGNMENT.md` §2 |
| Pre-event state disclosed | **DOCUMENTED** — pre-window tip `73db823`, 2026-11-13 22:34 |
| Event-window contribution | **DOCUMENTED — 29 commits, 104 files, +35,814 lines**, classified in §3 |
| New experimental work in window | **8 commits**, two of which correct or supersede a pre-event result |
| Eligibility decision | **NOT MADE — the submitter's call** |
| Organizer clarification | **DRAFTED, NOT SENT** — needs authorization |

## 8. Reproducing this page

```
git log --pretty=format:"%h|%ad|%s" --date=format:"%Y-%m-%d %H:%M" --since="2026-11-14 00:00" | tac
git diff --stat "$(git log --pretty=format:%H --until='2026-11-13 23:59' -1)" HEAD | tail -1
```

The first command lists the in-window commits; the second prints the diffstat that §2 quotes. Both are
git, not memory, so this page can be re-derived rather than trusted.
