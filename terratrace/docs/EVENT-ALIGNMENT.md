# Event alignment — NASA Space Apps Challenge 2026

**The rule this page follows.** Every statement below is either a **verbatim quotation** from an
official 2026 page, named with the page it came from, or it is explicitly marked **unverified** with
the reason it could not be checked. Where the official wording contradicts something this project
previously asserted, the official wording wins and the old sentence is corrected on the spot rather
than quietly kept. Two assertions in the project's earlier eligibility note did not survive that
test; both are corrected in §7 and one of them was corrected in the *opposite* direction from what
had been assumed.

This page exists because "we think we are eligible and we think we are aligned" is not a position
that can be audited. Every line of it can be traced to a page a judge can open.

## 1. The official facts

Parenthetical numbers are the section of the official page the quote sits in, where the page has
sections.

| Fact | Official wording (verbatim) | Source page |
|---|---|---|
| Event dates | "November 14-15: NASA Space Apps Challenge event." | `/resources/participant-faqs/` |
| Challenge announcement | challenges are "announced on October 28, which include the full details and requirements" | `/resources/participant-faqs/` |
| Challenge resources | "Resources for each challenge will be published on November 13." | `/resources/participant-faqs/` |
| Guides release | "November 13: Global Offers available. Challenge resources available. Project Submission and Judging & Awards Participant Guides available." | `/resources/participant-faqs/` |
| Number of challenges | "Choose from 14 challenges for you and your team to address at this year's hackathon! You can use the search and filter features to quickly find a challenge that best matches your interests and skills." | `/2026/challenges/` |
| Team size and shape | "Local Event teams must have at least one (1) person and Universal Event teams must have at least two (2) people to be eligible for global judging. Teams may have no more than six (6) members and must be signed up for the same Local Event or the Universal Event. You may only be on one team and teams are only permitted to work on one challenge." | `/resources/participant-faqs/` |
| Age | "The NASA Space Apps Challenge is open to all ages! If under the age of 18, participants must be registered for the event by a parent or legal guardian and must be accompanied by a parent or legal guardian at all times during the event." | `/resources/participant-faqs/` |
| **Demo format** | "Provide a short demonstration ("demo") of your project, either in the form of a slide presentation (**7-slide limit including title and intro slides**) or a video presentation (**30-second limit**)." | `/resources/judging-awards-guide/` |
| Submission completeness | "Complete all of the required fields on the Project Submission page." | `/resources/judging-awards-guide/` |
| Language | "Use English language on the project submission page and in any linked materials." | `/resources/judging-awards-guide/` |
| **SI disclosure (mandatory)** | "Participants may use SI tools to accelerate innovation, streamline development, and enhance creativity in support of their challenge solution. **Each team's project submission must include a description of how SI tools were used during the development of their project.**" | `/resources/participant-faqs/` |
| What "SI" means | "Super Intelligence (SI) refers to computer systems that perform tasks typically associated with human reasoning, decision-making, content creation, and problem-solving. Examples include large language models, conversational assistants, image and video generation …" | `/resources/participant-faqs/` |
| Site banner during the event | "The NASA Space Apps Challenge is happening now! 🎉" | site header, 2026-11-14 |

Note on the term: the 2026 event's official vocabulary for AI is **"Super Intelligence (SI)"**, and
the FAQ ties the term to a U.S. Executive Order dated 29 September 2026. The disclosure requirement
is therefore written in terms of SI, not "AI". Any submission text this project writes should use
the official term, and the requirement is not optional.

### How these were read

The 2026 site is a client-rendered Next.js application and the resource pages are served with their
content embedded in the server payload rather than as plain prose. `WebSearch` returned nothing in
this environment, so every quote above was recovered by reading the fetched page payload directly
and is quoted from there, not from memory or from a summary. Where a page could not be read this is
stated in §6.

## 2. The rule that governs preparation, and what it means for this repository

Verbatim, from `/resources/participant-faqs/`:

> Resources for each challenge will be published on November 13. Teams **are not allowed** to begin working on the challenges prior to the hackathon.

Three things follow, and they are different from what an earlier note in this repository implied.

First, the rule is about **beginning work on the challenges**. It is not a general prohibition on
prior work, and the event does not ask anyone to discard the tools they already own. What it forbids
is starting on a 2026 challenge before the hackathon window opens.

Second, the **challenges were only announced on 28 October 2026** and their resources on
13 November. Work done before 28 October cannot have been work on a 2026 challenge, because no 2026
challenge had been published to work on.

Third, and this is the part that costs something: work done **between 28 October and 14 November** on
a 2026 challenge is squarely inside the prohibition. This repository's history runs through that
window. The honest reading is therefore that

- the **engine and its published results are prior art** — they predate the challenge announcement
  and are cited as such, and
- the **submitted artefact** must be produced inside the 14–15 November window, using the engine as
  any public library would be used.

That second bullet is not a technicality to be waved away; it is the actual constraint. It is also
the reason [`EVENT-WINDOW-CONTRIBUTION.md`](EVENT-WINDOW-CONTRIBUTION.md) exists and the reason the
event-window record has to be filled in with real timestamps during the event rather than
reconstructed afterwards.

An earlier version of `docs/event/eligibility-evidence.md` said that official guidance "permits
preparation and data exploration beforehand". **That sentence was not supported by any official page
that could be reached**, and it has been removed. The rule above is what the page actually says.

## 3. The demo constraint, and the correction it forces

The judging and awards guide states the demo requirement in one sentence, quoted in full in §1, and
it gives exactly two admissible forms:

| Admissible form | Limit | Includes |
|---|---|---|
| Slide presentation | **7 slides** | "including title and intro slides" |
| Video presentation | **30 seconds** | — |

Both numbers are far tighter than the project had been designing against, and both forced a change.

**The slide deck is compliant.** `TerraTrace-submission.pptx` was built and then counted, not
assumed: it has **exactly 7 slides**, and that count is asserted by a test rather than trusted to a
sentence in a document. The count includes the title slide, which is what the rule means by
"including title and intro slides".

**The video script is not compliant, and cannot be made compliant by trimming.** `docs/DEMO.md`
specifies a 2½-minute video with nine timed shots. Thirty seconds is not a shortened version of that
script — it is a different artefact. The working position is therefore:

- the **7-slide deck is the submission demo**, and it is the thing that must be rehearsed and
  correct;
- the existing 2½-minute script is retained as a **recording script for the published site**, which
  is a legitimate use and is not the submission, provided the two are never confused in a submission
  page that links both.

The plan that specified a "2–3 minute video" and the external review that asked for a "two-minute
demonstration" were both written before the 2026 guide was read. Neither is submittable as written.

## 4. The mandatory SI disclosure

The requirement is quoted verbatim in §1 and it is not optional: **"Each team's project submission
must include a description of how SI tools were used during the development of their project."**

For this project that description is unusually short and unusually complete, because the AI
assistance is not incidental to the work — it is written into the repository's own record. The
submission text is drafted in full at [`event/SI-DISCLOSURE.md`](event/SI-DISCLOSURE.md), and it
follows the same rule as everything else here: it describes what was done, it does not claim
capability that is not in the commit history, and it does not hide the extent of the assistance. A
disclosure that understates is a defect of the same kind as a result that overstates.

## 5. The five judging criteria against this project's actual evidence

The judging guide lists five criteria. They are quoted below with the criterion name as the page
gives it.

| Criterion | Official description (verbatim, excerpted at the same sentence) | What this project actually offers | The honest gap |
|---|---|---|---|
| **Impact** | "This project makes an impact by addressing either a minor or major problem, which influences the quality and quantity of its overall effect." | A screening step that exists to *stop* a mission concept from being built on a false analog. The project's own headline result is a withdrawn claim, which is the argument for the tool in one line. | The impact is methodological, not a deployed capability. Nothing in the repository claims an operational user. |
| **Creativity** | "This project demonstrates originality and innovation. It introduces a novel concept that has not been attempted before …" | Three separable engine verdicts (ranking / adequacy / sufficiency) rather than one analog score, a scale-resolved evidence atlas, and an abstention ledger with reasons. | Morphological analog screening is not new. What is new here is the *refusal* machinery, and it is only creative insofar as the refusal is real. It is real, and it is tested. |
| **Validity** | "This project presents a proposed solution that is grounded in scientific principles and demonstrates technical, functional, or logical feasibility." | 51 scientific-correctness oracles with a stable hash; pinning against closed-form geodesy on five bodies; a frozen protocol published before the run; a cross-artifact reconciliation layer that **refuses to publish** when two records disagree. | The lunar half of the evidence is exploratory by construction — six nearby sites are not six independent tests — and the project says so on the same slide as the result. |
| **Relevance** | "This project fully and directly addresses the challenge for which it was submitted, demonstrating a strong alignment with the intended objectives." | Mars half: a real multi-window protocol-v3 study with a confirmatory verdict. Moon half: real LOLA terrain at the published south-polar candidate regions. Both halves of a Moon-and-Mars challenge are addressed. | **The challenge title itself could not be re-verified — see §6.** Until it is confirmed at the event, this row is the weakest of the five. |
| **Presentation** | "The team effectively communicated their project, clearly conveying the challenge, their proposed solution, and its significance." | A 7-slide submission deck within the stated limit; a live site; an offline evidence page that renders with the network off; every headline number on the page recomputed from the record it describes. | Judged by a human at the event, not by a test. The deck has been QA'd slide by slide, which is a floor, not a guarantee. |

### The judging flow

The guide describes a progression — Local Events, then Global Nominees, then Global Finalists, then
Global Winners — evaluated against the same five criteria. Two consequences are worth stating
plainly rather than discovering later: Local Event teams need only **one** person, while Universal
Event teams need **at least two** to be eligible for *global* judging; and a team may be on one team
and one challenge only. If the submission is intended to reach global judging, the team must satisfy
the Universal threshold.

## 6. Documented blocker: the 14 challenge titles

**What is verified:** that there are **14 challenges** for 2026, quoted in §1 from the challenges
index.

**What could not be verified:** the **titles** of those 14 challenges, and therefore the exact
wording of the challenge this project addresses.

**Why:** the challenges are fetched by the page at run time from
`https://api.spaceappschallenge.org/graphql`, which the page's own server payload names. The index
page was fetched and searched; it contains the heading, the count, the search-and-filter prose, and
no challenge entries. `sitemap.xml` lists only five top-level URLs and no challenge slugs. No
challenge slug appears anywhere in the fetched payloads. Enumerating the titles would require
issuing a query against that endpoint, which is outside what this environment will do.

**Consequence, stated rather than hidden:** the submission deck's title line names the challenge in
the form "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars", which
comes from the project's master plan and **has not been re-confirmed against the official 2026
list**. That line is an unverified assertion sitting in a shipped artefact. Two acceptable
resolutions, in order of preference:

1. **At the event, open `/2026/challenges/`, find the challenge, and copy its title verbatim** into
   the master plan, the deck generator, and this page. Then regenerate the deck.
2. If the title cannot be confirmed, **soften the deck's line** so it describes the subject matter
   rather than quoting a title, and record in the master plan that the title is unconfirmed.

Leaving the unverified title in the shipped deck while this page says it is unverified would be
worse than either fix.

The project has not attempted to work around the block by guessing, and a previous note in this
repository correctly flagged the same thing. It is repeated here because it is the single largest
open item in this document.

## 7. Eligibility position, corrected

The corrected position, in full:

- **This repository is published prior art.** A public, MIT-licensed project whose commit history is
  the dated record of what existed and when. It is not presented as having been created inside the
  event window, its history is not disguised, and it claims no NASA endorsement and no official
  status.
- **The submitted artefact must be produced inside the window.** Per §2, beginning work on a 2026
  challenge before the hackathon is not allowed. The contribution record for the window is
  [`EVENT-WINDOW-CONTRIBUTION.md`](EVENT-WINDOW-CONTRIBUTION.md), and it must be filled from the
  event's real timestamps.
- **The SI disclosure must be included** (§4).
- **The demo must be a 7-slide deck or a 30-second video** (§3).
- **The challenge title must be confirmed at the event** (§6) before it is quoted anywhere.

The decision record for which path is taken remains in
[`event/eligibility-evidence.md`](event/eligibility-evidence.md), and it is still unfilled on
purpose: it is a record of a decision taken at the event, and pre-filling it would make it a
fabrication.

## 8. Prior winners: what is *not* known here

The review that produced this milestone asked for an honest comparison against previous winners.
The honest answer is that **it was not possible to read the 2025 winners' projects from this
environment**: the winners are listed on the same client-rendered site, and no project content could
be recovered from the pages that were reachable. The page to check is the 2025 Global Winners
listing under `/awards/`.

Rather than invent a comparison, this page records the gap and states the one thing that can be said
without it: the five criteria above are the bar, and §5 states this project's standing against each
of them including the rows where it is weak. A comparison built on nothing would be exactly the
failure mode §5 is designed to prevent.

## 9. Quality audit

The review's quality dimension, answered with the artefact that supports each row rather than with
an adjective.

| Dimension | What was checked | Evidence | Status |
|---|---|---|---|
| **Reproducibility** | Suite runs offline with no API key; a clean-tree run and a dirty-tree run give the same result | `tests/run_tests.py`; the CI workflow installs NumPy only, so the CI run *is* the clean-environment check | Met |
| **Scientific validity** | 51 correctness oracles against closed-form or independent references; five-body geometry against Vincenty and great-circle; a negative control that must fail loudly | `tests/`, `docs/VALIDATION.md`, `docs/INDEPENDENT-GIS-REPRODUCTION.md` | Met, with the lunar half labelled exploratory |
| **Honest reporting** | Every claim maps to an experiment and a falsifier; the project's own withdrawn claim is published at the same prominence as its results | `docs/CLAIM-LEDGER.md`, `docs/DISCOVERY-ATLAS.md` | Met |
| **Refusal behaviour** | The atlas refuses to publish when two records disagree, and every reconciliation is proven able to fail | `tests/test_discovery_atlas.py` (corruption matrix) | Met |
| **Offline demonstration** | The evidence page loads nothing from outside itself and uses no browser storage | `tests/test_atlas_page.py` | Met |
| **Documentation drift** | A mechanical guard fails the build when a document quotes a number the code no longer produces; it covers 21 canonical documents, 4 HTML pages and 6 generator scripts | `scripts/doc_consistency_check.py` | Met |
| **Submission compliance** | Slide count within the stated limit; SI disclosure written; language; required fields | §1, §3, §4, and the slide count asserted in `tests/test_event_alignment.py` | Met except §6 |
| **Eligibility** | Prior-art position recorded; window-contribution record exists and is unfilled | §7 | Met pending the event record |
| **Challenge alignment** | Title re-confirmed against the official 2026 list | — | **Open — §6** |

## 10. What this page leaves for the event

- [ ] Open `/2026/challenges/`, locate the challenge, copy its title verbatim, regenerate the deck.
- [ ] Fill the decision record in `event/eligibility-evidence.md` with the date and the path taken.
- [ ] Fill `EVENT-WINDOW-CONTRIBUTION.md` from the event's real timestamps.
- [ ] Paste `event/SI-DISCLOSURE.md` into the submission's SI field, adjusted to what was actually
      done inside the window.
- [ ] Check the submission's team registration against the Local/Universal threshold in §5.
- [ ] Confirm the submitted demo is the 7-slide deck (or a ≤30-second video), not the 2½-minute
      recording script.
