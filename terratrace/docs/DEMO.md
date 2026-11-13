# Demo script — 2½ minutes, shot by shot

The master plan (§10.4) requires a 2–3 minute video showing **one compelling decision and the refusal
mechanism**. The plan's own §10 script was written against screens that no longer exist under those
names; this version is mapped to what is actually deployed, and carries the real figures so nothing
has to be invented during a take.

**Before recording.** Open a clean profile at the four URLs below and confirm each loads. Reveal your
API key state is irrelevant — the benchmark path needs no key. Do **not** read a number off the
screen and re-type it from memory: every figure in this script is a fixed value you can verify in
`terratrace/docs/RESULTS-v3.md` first.

**Honest framing, first line of the narrative.** This repository is published prior art; the video
describes the published workbench. Do not imply it was built inside the event window.

## The four surfaces

| # | URL | What it is |
|---|---|---|
| 1 | `/` | Landing: the three-act story, the method, the descriptors, the evidence row |
| 2 | `/study` | The protocol-v3 results — verdicts, the S and V tables, the roughness ladder, the caveat |
| 3 | `/viewer` | The engine's generated study output — decision matrix, gap ledger, provenance |
| 4 | the repository | `RESULTS-v3.md`, `CLAIM-LEDGER.md`, `PAPER.pdf`, `VALIDATION.md` |

## Shots

| Time | On screen | Say (adapt, don't read) |
|---|---|---|
| 0:00–0:15 | `/` hero, scope ribbon visible | "Finding a landscape that looks like Mars is easy. Designing a test whose result actually transfers to Mars is hard — and that's the failure this tool exists to catch." |
| 0:15–0:30 | scroll to **THE FINDING** (three acts) | "The first run of this engine picked Craters of the Moon, Idaho — a genuinely famous basalt analog. It would have been easy to stop there." |
| 0:30–0:45 | keep scrolling the three acts | "We froze a protocol *before* looking at more data. The claim did not survive: in the honest regime the engine abstained, and Craters was just as close to a cratered highland as to a volcanic plain." |
| 0:45–1:05 | **cut to `/study`**; stop on the three verdict chips and the caveat box | "Then we tested *why*. Protocol v3: three confirmatory volcanic plains, two highlands, seven Earth candidates, 60 km windows. Smoothness is supported — three of three. Volcanic specificity is not — zero of three." |
| 1:05–1:25 | scroll to the **roughness ladder** | "This is the whole result in one picture. The two references that carry the finding sit at the smooth end — right where the two *non-volcanic* controls sit. The basalts win only where the target is rough. Origin does no work that roughness doesn't already do." |
| 1:25–1:40 | scroll to **R** and the reproduce block | "Resolution robustness holds: zero reversals in fifteen honest cells. And it reproduces in two commands with no API key — the Earth data comes from a public cloud mosaic, verified bit-identical to the commercial path." |
| 1:40–1:55 | **cut to `/viewer`** (the site bar shows it is an archived run) | "It would be easy to make the output look decisive. Here's what the engine actually emits: a decision matrix, a bootstrap interval on every distance, and — in this archived run — a tie, with no unit recommended." |
| 1:55–2:10 | scroll to the **transfer-gap ledger** (T0–T4) | "And this is the part most analog tools omit. Gravity, atmosphere, regolith mechanics, radiation, thermal cycling — listed as *unassessed*, not folded into a score. Site access and ecology are blocking states, not green ticks." |
| 2:10–2:25 | **cut to the repository** — `CLAIM-LEDGER.md` | "Every claim in the project points at an experiment, a status, and the evidence that would falsify it — including the claim we withdrew. The suite is 843 tests, 51 of them scientific-correctness oracles, and a guard that fails the build if the documentation drifts from the code." |
| 2:25–2:35 | back to `/` footer, firewall visible | "Map-scale morphology only. It does not claim traversability, geologic equivalence, site access, or mission readiness. Its sharpest result is a claim it disproved — its own." |

## The refusal moment

The plan calls the memorable element the **refusal-to-overclaim moment**, not the globe. Shot at
1:40–2:10 is that moment: the tool is shown *declining* to name a winner, and explaining which
physical processes it cannot speak to at all. Keep it in even if you have to cut something else.

## Consistency checklist (from module 18)

- Every number spoken matches `RESULTS-v3.md`. Read them from the page, never from memory.
- Capture from the final deployed build, after the last push.
- UI labels match the docs: it is a **draft study protocol**, never an "approved test plan".
- No site is described as field-authorized; nothing is called a validated analog.
- Attribution for MOLA / Copernicus / USGS is visible somewhere in frame (the footer does it).
- The eligibility statement is accurate: prior art, not a submission artefact.

## If you have only 60 seconds

Show shots 0:00–0:15, then cut straight to the ladder at 1:05–1:25, then the ledger at 1:55–2:10, and
close on the footer. That is the finding, the mechanism, the boundary — the three things that
distinguish this from a similarity map.
