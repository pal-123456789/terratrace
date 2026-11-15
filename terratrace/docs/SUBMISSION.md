# TerraTrace — the submission page

Everything a reviewer, a judge or a future team member needs, in the order they would want it. If you
read one page about this project, read this one; if you read two, read
[`EVENT-ALIGNMENT.md`](EVENT-ALIGNMENT.md) next, because it is where the official requirements are
quoted and where this project measures itself against them.

## What it is

A map-scale terrain-**morphology** screening engine across **Earth, Mars, the Moon, Mercury and
Ceres**. It compares the shape of a landscape — not its colour, its chemistry or its age — at a
declared common spatial support, and it answers three questions **separately**, because collapsing
them into one number is how an analog study goes wrong:

| question | what it means |
|---|---|
| **ranking** | which candidate is closest, among the candidates tested? |
| **adequacy** | is any candidate inside the reference's own morphological variability? |
| **sufficiency** | is the evidence enough to answer either of those? |

No composite analog score exists anywhere in the engine, and `terratrace/verdicts.py` has a
structural check that walks a verdict — including nested blocks — and refuses one.

The distinguishing feature is not the similarity map. It is the **refusal machinery**: the project
publishes the claim it withdrew about itself, it lists every cell where it abstains, and its atlas
**will not write a file** if two of its six committed records disagree.

## The challenge, and one honest caveat

**Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars** — the official 2026 challenge this project is submitted to, **confirmed from the
submission portal on 2026-11-15**. The list carries **14 challenges** in total.

That title was, until today, the one claim in this submission that tooling could not verify: the
challenge index is client-rendered and its titles are fetched from `api.spaceappschallenge.org/graphql`,
which refuses a plain GET with an anti-CSRF guard. It was closed by a person reading the portal, and
the whole episode — including the failed route, so nobody repeats it — is recorded in
[`EVENT-ALIGNMENT.md`](EVENT-ALIGNMENT.md) §6.

![The pipeline in twelve numbered stages, from the declared config and the fail-fast preflight through the per-body metric grid, the descriptor bank, the comparability gate, the Pareto decision, the three separate verdicts and the hashed package to the published surfaces.](figures/pipeline.svg)

## Verify it in one command

```
bash scripts/reproduce_all.sh
```

Five steps: the offline test suite, the scientific-correctness oracles, the documentation-consistency
guard, the discovery atlas, and the independent-axis probe. The first four need only Python and NumPy
plus the committed records; the fifth needs the terrain rasters and **says so and stops** if they are
absent rather than reporting a pass it did not earn. The suite is dependency-free and needs no network
and no API key.

## The result, and the bound on it

**Mars (confirmatory, protocol v3, frozen before the run).** Smoothness tracks the class —
**supported**, 3 of 3 volcanic plains. Volcanic *specificity* does not — **not supported**, 0 of 3.
Resolution robustness holds with zero reversals. The project's earlier exploratory preference for
Craters of the Moon, Idaho is **withdrawn**.

**The Moon (real LOLA terrain, exploratory).** Six published south-polar candidate regions, run on
real data at an exact common grid, with the ranking definite at every cell — and then three facts
published at the same prominence, because they reduce what the panel supports: the absolute question
is answered at **none** of the cells; the nearest unit to a lunar reference is usually **another lunar
site**; and the sole-winner property is a property of running a Pareto rule over eight units in three
dimensions, measured against a control where an arbitrary coordinate does the same thing
([`AXIS-PROBE.md`](AXIS-PROBE.md)).

That last one is the newest and the sharpest. It does not demote the ranking, which stands as
published, relative and provisional. It measures *how* provisional.

## What it does not claim

Map-scale **morphology** only. No traversability, no geologic equivalence, no site access, no mission
readiness. Nothing here says any Earth terrain is a mission-relevant Mars or lunar analog —
[`limitations.md`](limitations.md) states the firewall in full, and the transfer gaps (gravity,
atmosphere, regolith mechanics, radiation, thermal cycling) are listed as **unassessed** rather than
folded into a score.

## Which link goes in which portal field

The submission form has two link fields and they are not interchangeable. Getting them the wrong way
round is the one mistake on this page that can cost eligibility, so the mapping is recorded here.

| Portal field | What it accepts | What goes in it |
|---|---|---|
| **Project Demonstration** | a slide presentation of **no more than 7 slides, including the title and introduction**, *or* a video of **30 seconds or less**, on a public host | `TerraTrace-submission.pdf` — the 7-slide deck, linked from this repository. **Not the live site**: a website is neither a slide presentation nor a video, and the Global Award rule is about the demo's form as well as its public accessibility |
| **Project** | a website you created to showcase the project, a hosting service, or a code repository | the live site, <https://terratrace.fit> — the repository is one click from it, and either would be accepted |

The link must be the whole URL, must resolve without a password, permission or registration, and must
be reachable by anyone. Both of the above were checked that way; the repository is public and
MIT-licensed, and the deck's slide count is asserted by a test rather than counted by eye.

## Compliance

| requirement | status |
|---|---|
| demo is a **7-slide deck** (title and intro included) or a ≤30-second video | `TerraTrace-submission.pptx` is **exactly 7 slides**, asserted out of the archive by a test |
| **SI-tool disclosure** in the submission | drafted and ready at [`event/SI-DISCLOSURE.md`](event/SI-DISCLOSURE.md) |
| English on the submission page and linked materials | met |
| team size / one challenge / Local-or-Universal threshold | **the registration threshold is unchecked**; the prior-work position is decided and recorded at [`event/eligibility-evidence.md`](event/eligibility-evidence.md) (Option 1, extend-in-window and disclosed) |
| prior art disclosed, not disguised | the repository is public, MIT-licensed, and its commit history is the dated record; the artefact submitted is the in-window work that **extends** it, with both halves listed in [`EVENT-WINDOW-CONTRIBUTION.md`](EVENT-WINDOW-CONTRIBUTION.md) |
| challenge title confirmed | **yes** — read from the submission portal on 2026-11-15; the string is identical in every artefact that carries it and is pinned by a test |

## Where things are

| I want… | go to |
|---|---|
| the official rules, quoted with sources | [`EVENT-ALIGNMENT.md`](EVENT-ALIGNMENT.md) |
| every claim → an experiment → a falsifier | [`CLAIM-LEDGER.md`](CLAIM-LEDGER.md) |
| the Mars result and its caveats | [`RESULTS-v3.md`](RESULTS-v3.md) |
| the scale-resolved evidence in one output | [`DISCOVERY-ATLAS.md`](DISCOVERY-ATLAS.md) |
| the newest negative result, in full | [`AXIS-PROBE.md`](AXIS-PROBE.md) |
| the site | `/`, `/study`, `/viewer`, `/atlas` |
| the honest boundaries | [`limitations.md`](limitations.md) |
