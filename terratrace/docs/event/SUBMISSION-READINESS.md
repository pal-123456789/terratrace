# Submission readiness — final-day audit

**Audit date:** 2026-11-15, the second and final day of the 2026 challenge window.
**Branch audited:** `improvement/scientific-consistency`, from `d50b346` (the merge tip of PR #18) to
the commit that carries this page.
**Standard applied:** a scientifically honest, technically reproducible, clearly demonstrated,
challenge-relevant submission — not a feature-heavy project with exaggerated claims. Nothing in this
page is a promise of a score or a win.

**Verdict: READY WITH CAVEATS.** The submission artefacts exist, are in spec, and are verified by
tooling rather than by assertion. Two things are outside what this repository can settle: the
eligibility reading is **the submitter's, not the organizer's**, and the team-registration threshold
has not been checked against the event's Local/Universal rule. Both are disclosed rather than
smoothed, and both are named in §11 as blockers of the kind that must be closed by a person.

## 0. The three highest-risk issues, identified first

The audit was asked to start here rather than with the easy wins. These were the three, in order, and
all three were fixed before anything cosmetic:

1. **The event-window record was materially false.** `EVENT-WINDOW-CONTRIBUTION.md` said, in its
   central table, that the window had not produced commits. It had produced 29 by the time the page
   was written and 30 by the end of the day. A reader — including a judge checking whether the
   submission has in-window substance — would have concluded it had none. Fixed from `git log`, with
   the count now carrying its own as-of commit, classified into new experimental work, new tooling,
   and re-rendering that is **explicitly not counted as contribution**.
2. **Both decks contradicted the eligibility decision.** The submission deck's title slide and slide 7
   of the same deck described the work as prior art that stopped at the event boundary ("built and
   gated weeks before the event", "built weeks before the event"). That was true of the origin and
   false of the submission, and it contradicted the Option 1 decision recorded on 2026-11-15.
3. **The submission deck's lunar slide omitted the project's sharpest limit.** It carried the
   favourable stability number, and repeated it twice, while the adequacy verdict — that the absolute
   question is answered at **none** of the 18 cells — appeared nowhere in the deck. A judge could
   reasonably have read the slide as a positive analog finding.

Two of these three were found by reading the artefacts against the records, not by any check. The
response was to add the check that would have caught the first one, described in §7.

## 1. Eligibility and official alignment (P0)

The seven determinations the audit asked for, each with its basis:

| # | Determination | Answer | Basis |
|---|---|---|---|
| 1 | What existed before the event | The engine, six decision lenses, both benchmark protocols and their v2/v3 results, the keyless Earth path, the suite, the site and the documentation | Pre-window tip `73db823`, 2026-11-13 22:34 |
| 2 | What was developed 14–15 November | 30 commits: 28 ordinary and 2 merges | `git log`, dated |
| 3 | Which commits are genuine new work | Eight produced results; nine added tooling; the rest re-render | §3 of the record, commit by commit |
| 4 | Does the artefact satisfy the prior-work rule | **Not settled by this repository.** The rule prohibits *beginning work on the challenges*; the position taken is that a published prior toolkit extended in-window is compatible with it | The official rule is quoted verbatim; the reading is disclosed |
| 5 | Is written clarification necessary | Not obtained. The organizer has **not** been asked; the draft inquiry is unsent | `CLEAN-ROOM-NOTE.md` |
| 6 | Does the title match the official challenge | **Yes** — confirmed from the submission portal on 2026-11-15 by the submitter, matching the wording already carried | `EVENT-ALIGNMENT.md` §6 |
| 7 | Team-size and registration threshold | **Unverified.** Local teams need ≥1, Universal ≥2; a decision against the actual registration has not been recorded | §2 of the alignment page |

The eligibility status remains **disclosed and unconfirmed**, and the alignment audit scores it that
way. The audit instruction not to upgrade it silently was followed: it is the one row of the quality
audit that is deliberately not marked met.

**The uncertainty that remains.** The rule the repository quotes admits more than one reading of an
operator's existing public toolkit. That is a genuine ambiguity, not a defect this project can fix by
asserting harder, and the honest handling is the one taken: state the reading, state that it is the
submitter's, and let the organizer be the arbiter.

## 2. Every submission requirement, re-checked

| Requirement | Status | Evidence |
|---|---|---|
| 7-slide maximum, including title and intro | **Met** — exactly 7 | Counted out of the `.pptx` archive by `tests/test_event_alignment.py`, not asserted |
| Or the 30-second video alternative | **Not used.** The 21⁄2-minute script in `DEMO.md` exceeds both limits and says so at the top | `DEMO.md` |
| Mandatory SI / Super Intelligence disclosure | **Drafted and ready to paste**, using the official 2026 term, covering event-window work | `event/SI-DISCLOSURE.md` |
| English throughout | **Met** | Repository, site, decks |
| Required submission fields | **Not verifiable here** — the portal fields are filled by the submitter | This page §11 |
| Team registration and one-challenge restriction | **Unverified** | §1 above |
| Correct challenge selected | **Met** | Title confirmed from the portal |
| Required links and a working demonstration | **Met and verified live** — see §6 | `https://terratrace.fit`, HTTP 200 |

## 3. Scientific claim accuracy (P1)

The three claims a judge will check first, and where each one actually stands:

**The Mars headline.** Protocol v3 returned **S supported, V not supported**: smoothness tracks the
terrain class, volcanic origin does not. All 15 confirmatory honest cells are accounted for, including
the two classes that are zero — 11 unchanged, 0 stabilised, 1 destabilised, 0 reversed, 3 membership
changed, 0 error. Two caveats travel with it and are printed wherever the result is: v3 is
**pre-specified but not fully pre-registered**, and its confirmatory verdicts use the **core lens**,
the others not being independent replications.

**The lunar half.** Across **18 of 18** site × support cells the same single Earth candidate is
non-dominated, and that ordering survives **28 of the 30 perturbations** declared before the run, with
only **18 of 504 site × support cells moved**, a cell-level stable fraction of **0.964**, verdict
**ROBUST**. Reported alongside it, on the same page: the ranking is definite at all 18 cells, but
adequacy is **NOT_ESTABLISHED at all 18** — at the **6** cells where both descriptor bands can be
calibrated (the six at 500 m) the reference's own variability band admits **at least four of the five**
other sites, and at the other **12** there is **no relief band at all**, so the verdict there rests on
the slope band alone, which admits at least four of the five as well; and at **18 of 24 site ×
descriptor statistics** the unit nearest a lunar reference is **another lunar site**, not any Earth
candidate.

**The bound on our own headline.** The three declared lunar axes are one axis — mean slope and 3×3
relief satisfy `relief = 2 d tan(slope) · ρ` with ρ provably in `[1, √2]`, verified against the
engine's own functions to 4.4e-16 m, effective rank **1 of 3**. The probe then showed the sole-winner
is a property of the run rather than of a candidate: a uniformly random fourth coordinate moves the
frontier in **15.90 of 18** cells on average, and **none of 141** candidate axes beats that control.

Nothing found in this pass overstates any of the three. The withdrawn Craters of the Moon claim is
**not** repeated anywhere as a finding.

## 4. Deck and presentation (P1)

All seven slides of the submission deck and slide 2 of the project deck were rendered to images and
read after the rebuild. Four defects were found and fixed:

- the two eligibility-framing contradictions in §0;
- the lunar slide's missing adequacy verdict and its duplicated stability number;
- a paragraph in the **project deck** split across three lines with a single orphaned word, in a text
  box sized for two;
- the submission deck's limits slide did not disclose the eligibility position at all, so a judge
  reading only that slide would not learn that the prior-art question is open. It now names it.

Verified after the rebuild: 7 and 10 slides respectively; the regenerated packages carry the same
`Office Theme` as the ones they replace, so nothing but the intended content moved.

**Weakness that remains, stated plainly:** the deck carries no chart of the actual artifact output.
Every number on it is traceable, and the terrain panels are real Copernicus DEM products, but a judge
who wants a figure that *is* the result — the roughness ladder, the Pareto front — has to open the
paper or the site. That is a presentation weakness, not an accuracy one.

## 5. Demonstration (P1)

The deployed site was fetched and checked rather than assumed:

- `https://terratrace.fit` returns **HTTP 200**, redirecting once to `www`, and serves the current
  build — the page carries the 18 of 24 sibling result, the adequacy verdict, the 28 of 30 stress
  result and the 15.90 of 18 bound;
- all four routes (`/`, `/study/`, `/atlas/`, `/viewer/`) resolve to files the guard checks, and the
  guard verifies every site `href` and `#fragment` against the files as they exist;
- the offline evidence page loads nothing from outside itself and uses no browser storage, asserted by
  test;
- the one-command path, `scripts/reproduce_all.sh`, runs the suite, the oracles, the guard, the atlas
  and the axis probe with no network and no API key — and **says it skipped** step 5 when the DEMs are
  absent rather than reporting a pass it did not earn.

**Not verified:** browser console errors on the live site. This environment cannot open a browser, so
that specific check was not performed and is not claimed.

## 6. Technical defect audit (P2)

One real defect was found in this pass. It is fixed in the follow-up series (§9b), and this section is
the record of what it was and why its reach was smaller than it first looked.

**Division by a zero reference.** The axial fractional distance is `|value − reference| / |reference|`,
which is undefined when the reference descriptor is exactly zero. **12 of 184** bank scalars can be zero
in principle — class fractions that may legitimately take the value 0 — and a **13th** breaks for a
different cause, a non-finite input, which the first measurement could not see because a NaN candidate
made the distance a NaN rather than the `None` the audit tested for. Both causes are now recorded
separately in the probe's own artifact. Every declared lunar and Mars decision axis is strictly
positive, so no published comparison is affected.

**Correction to the first version of this section.** It said the case "is recorded in
`docs/limitations.md` rather than left for a user to discover". That was false: there was no such entry
in `limitations.md`, and a reader following the pointer would have found nothing. The claim is recorded
here rather than quietly deleted, and the entry now exists — `limitations.md` carries the policy, and
`decision.axial_fractional_distance` is where it is enforced.

The defect also turned out to be sharper than "a NaN appears". `decision.non_dominated` **excludes** any
unit carrying a non-finite distance, so a zero-reference axis did not raise — it silently compared fewer
units and returned a ranking over them. A policy that invented a finite substitute would have hidden
that; the fix refuses instead. §11 F1 has the detail and the tests.

No other defect was found in this pass. The suite, the oracles and the guard are green, and the guard
now covers 31 canonical documents, 4 HTML pages, and every generator script whose output carries a
number a reader can check.

## 7. Repository hygiene (P2)

Checked against the audit's own list:

| Item | Finding |
|---|---|
| Stale test counts | **Two live documents carried a stale in-window commit count of 29 against git's 30** — the alignment audit row and the eligibility basis paragraph. Both corrected, and the alignment page's two completed checklist items were still unticked |
| Outdated documentation | The event-window record and both decks, fixed in §0 |
| Contradictory result descriptions | The eligibility-framing contradictions in §0 |
| Unresolved TODOs | None found in the tree |
| Broken references | Guard resolves 124 relative links, every site href and every fragment — green |
| Incorrect challenge names | One string, confirmed from the portal, quoted identically in all five artefacts that carry it and pinned by test |
| Misleading badges | The CI badge points at the repository's own workflow; the last run on `main` **succeeded** (run #62, the merge of PR #18) |
| Untracked important artifacts | Working tree clean; nothing untracked |
| Missing generated files | Deck assets regenerate from a committed script; the large DEMs are git-ignored by design and fetched by a documented script |
| Incorrect download links | Guard-checked |
| Old decks presented as final | Distinguished by name and slide count everywhere: `TerraTrace-submission.*` is the 7-slide submission, `TerraTrace-deck.*` the 10-slide project deck |

**A new check was added, because a count went stale three times in one day.** The in-window commit
count is the one published number whose source is the repository's own history, and it was wrong
within hours of being written — by the commit that wrote it. `check_event_window` in the documentation
guard now reads `git` and compares five phrasings across three documents against the snapshot the
record names, rather than against `HEAD`: a check against the ever-growing present would fail on every
subsequent commit, which is how a real check gets deleted. It is the only check here that needs
history rather than files, so a shallow clone defeats it — and when CI's one-commit checkout defeats
it, it **says so** in the guard's output instead of passing quietly.

It was verified by simulation in both directions. Seeding a wrong count, a wrong file count and a
wrong insertion count produced four problems naming the right values; restoring produced a green run.
The first simulation failed usefully: the record's own table row went unchallenged because that
document was not in the guard's canonical list — the same "a guard that does not read a document
cannot find anything in it" lesson this list has now had to learn three times.

## 8. Five-judge scorecard

Five judges, ten criteria each, scored out of 5. Scores are deliberately not uniform: the evidence is
strongest on reproducibility and honesty, and weakest on demonstration and on whether the challenge's
literal question has been answered.

### Judge 1 — planetary science researcher

| Criterion | Score | Evidence |
|---|---|---|
| Problem relevance | 5 | The question — which Earth terrain legitimately transfers to a planetary reference — is the real methodological problem in analog studies |
| Scientific validity | 4 | 51 correctness oracles, five-body geometry against closed-form geodesy, a pre-registered test that withdrew a claim |
| Innovation | 4 | Rank/adequacy/sufficiency as separate verdicts that cannot be collapsed into a score |
| Technical execution | 4 | Correct per-body metric reprojection; real DEMs; a reprojection check against closed-form geometry rather than a second wrapper |
| Real-world usefulness | 4 | Screening that refuses false confidence is directly useful to an analog-site study |
| Evidence quality | 4 | Claim-to-evidence ledger with a falsifier per claim; one result is a claim disproved about itself |
| Clarity | 4 | Method document complete; the lunar half labelled exploratory where it appears |
| Demonstration | 4 | Live site with the results; no figure that *is* the headline result |
| Reproducibility | 5 | One command, no key, no network; frozen protocols; hash-anchored |
| Limitations and honesty | 5 | Publishes its own withdrawn claim, its abstentions, and the bound on its own headline |

**Strongest weakness:** the lunar panel is six nearby sites, not six tests — the effective sample is
near one, and the panel's own axes collapse to one. **What would improve it:** a second, independent
lunar region far from the south pole, which would test whether the one-axis collapse is a property of
the descriptor set or of that terrain.

### Judge 2 — NASA-style mission and science reviewer

| Criterion | Score | Evidence |
|---|---|---|
| Problem relevance | 5 | Addresses the challenge's literal question directly |
| Scientific validity | 3 | Valid but narrow: Mars confirmation rests on a pre-specified, not pre-registered, protocol, on the core lens alone |
| Innovation | 3 | Solid methodology; not a new measurement or instrument |
| Technical execution | 4 | Deterministic, reproducible, well tested |
| Real-world usefulness | 3 | Screening only — no traversability, hazard, access or readiness claim, by design |
| Evidence quality | 4 | Strong paper trail; single-lens confirmation limits the inference |
| Clarity | 4 | Scope firewalls are unambiguous and repeated |
| Demonstration | 4 | Site works; deck is readable in two minutes |
| Reproducibility | 5 | Verified |
| Limitations and honesty | 5 | Nothing overclaimed; limits named before results |

**Strongest weakness:** the deliverable answers the challenge's *methodological* question far better
than its *geographic* one — a mission reviewer wants candidate sites, and gets a refusal. **What would
improve it:** run the confirmatory protocol on a third held-out volcanic plain and a third cratered
highland, which would move the verdict from "pre-specified" toward "pre-registered and replicated".

### Judge 3 — software engineering reviewer

| Criterion | Score | Evidence |
|---|---|---|
| Problem relevance | 4 | Clear, bounded problem statement |
| Scientific validity | 5 | Determinism, oracle suite, hash-anchored artifacts |
| Innovation | 4 | Verification architecture is the genuinely novel part |
| Technical execution | 5 | Pure NumPy, no network at runtime, a dependency-free runner, a guard for prose |
| Real-world usefulness | 4 | Usable library with a CLI and HTTP API |
| Evidence quality | 5 | Every published count computed from source or artifact, never typed |
| Clarity | 4 | Layered documentation; some depth requires the engine README |
| Demonstration | 4 | Reproduce-in-one-command is real and honest about what it skips |
| Reproducibility | 5 | Clean- and dirty-tree runs agree; CI installs NumPy only |
| Limitations and honesty | 5 | A guard that reports what it could not verify |

**Strongest weakness:** the benchmark protocols, the engine and the decks are verified, but the
*submission flow* is still manual — the SI text, the fields and the deck upload are human steps with
no automated pre-flight. **What would improve it:** a single pre-submission script that re-runs the
guard, counts the deck's slides, checks every required artefact exists and prints the checklist.

### Judge 4 — innovation and creativity judge

| Criterion | Score | Evidence |
|---|---|---|
| Problem relevance | 4 | Genuine, under-served methodological gap |
| Scientific validity | 4 | The negative results are the most credible work here |
| Innovation | 5 | The refusal machinery: publishing the bound on its own headline, and refusing to write an atlas that contradicts itself |
| Technical execution | 4 | Competent and complete |
| Real-world usefulness | 4 | Prevents expensive false analogs rather than producing a map |
| Evidence quality | 4 | Strong, and unusual in publishing a self-refutation |
| Clarity | 4 | The three-act Mars narrative is easy to follow |
| Demonstration | 3 | No video; the deck is static; the strongest idea takes a paragraph to explain |
| Reproducibility | 4 | Verified by the same tooling |
| Limitations and honesty | 5 | Exemplary |

**Strongest weakness:** the most interesting idea — that a ranking is not an adequacy statement — is
hard to make vivid in seven static slides, and the deck does not try very hard. **What would improve
it:** one figure showing a candidate that ranks first and still fails the absolute test, which makes
the whole thesis visible in five seconds.

### Judge 5 — presentation and communication judge

| Criterion | Score | Evidence |
|---|---|---|
| Problem relevance | 4 | Clear opening problem statement |
| Scientific validity | 3 | Correct, but dense for a slide format; the caveats need reading twice |
| Innovation | 3 | Present but under-sold |
| Technical execution | 4 | Consistent visual system, correct slide count, legible slides |
| Real-world usefulness | 4 | Impact is explained honestly, distinguishing demonstrated from potential |
| Evidence quality | 3 | On the slides, numbers arrive without their receipts; the receipts are one link away |
| Clarity | 5 | Unusually clear prose; the README's first screen is genuinely useful in 30 seconds |
| Demonstration | 4 | Live site is a strong asset |
| Reproducibility | 4 | Visible and credible |
| Limitations and honesty | 5 | The limits slide is the deck's best slide |

**Strongest weakness:** seven slides cannot carry this much caveat, so the deck reads as cautious
where a judge may want a claim. **What would improve it:** a 30-second recording of the live site as a
companion, and a single "here is the answer we can defend" slide stated in one sentence.

### Overall

| Judge | Mean |
|---|---|
| Planetary science researcher | **4.3** |
| NASA-style reviewer | **4.0** |
| Software engineering reviewer | **4.5** |
| Innovation judge | **4.1** |
| Presentation judge | **3.9** |

**Overall: 4.2 / 5.** The spread is the informative part: reproducibility and honesty score 5 from
every judge, and demonstration scores lowest from two of the five.

**Strongest competitive advantage.** Not the similarity map — the refusal machinery, and the
willingness to disprove its own published finding under a protocol frozen in advance. Almost no
hackathon submission publishes a bound on its own headline.

**Biggest risk of losing.** The challenge asks for Earth locations that analog lunar base sites and
Mars. The strongest, most defensible results here are *negative* — the Craters claim withdrawn, the
lunar panel failing absolute adequacy, the frontier shown to be an artefact of the rule. A panel that
scores a clear positive answer over a rigorous non-answer will not reward this. The counter is that
the positive answer is also present and honest: across 18 of 18 cells the same Earth region is the
sole non-dominated candidate, and the Mars panel's front is named.

**Three things judges are most likely to question.**

1. *"Did you build this during the event?"* — The commit history answers it, and the answer has two
   parts: the toolkit predates the window, and 30 dated commits inside it produced eight new results,
   including the correction of one of the project's own published comparisons.
2. *"Your lunar result is six sites and one axis — is it a finding?"* — No, and the submission says so
   before being asked, including that absolute adequacy is established nowhere.
3. *"Which Earth location is the answer?"* — The engine will name the least-dissimilar candidate and
   refuse to call it adequate. That refusal is the project's position, not an omission, and it is
   stated on the limits slide.

**The honest 30-second explanation.**

> TerraTrace asks which Earth terrains are legitimately comparable to a planetary reference at a
> shared scale, and it answers three separate questions instead of one score: which candidate is least
> dissimilar, whether any candidate is inside the reference's own variability, and whether the evidence
> is strong enough to say either. It caught its own false analog — a famous basalt field it had
> favoured — withdrew it under a protocol frozen before the data, and then measured why: roughness
> tracks the terrain class, volcanic origin does not. It publishes its own abstentions, the bound on
> its own headline, and a real correction to its own lunar comparison. Running it needs no key, no
> network and no account, and the whole study has 1044 offline tests and 51 correctness oracles behind
> it.

**The final submission checklist.**

1. Confirm the eligibility position is the one being submitted, and that the SI field will be filled.
2. Paste `event/SI-DISCLOSURE.md` into the required SI field — an empty one is a required-field failure.
3. Upload `TerraTrace-submission.pptx` (7 slides) or `TerraTrace-submission.pdf` — **not** the 10-slide
   project deck, and **not** the 21⁄2-minute recording.
4. Confirm the team registration against the Local/Universal threshold.
5. Link the repository and the live site; both are verified working.
6. Confirm the challenge selected in the portal is the one quoted throughout.

## 9. Required final report

**How to read this section — and the rule that replaced a claim.** Everything here about a branch's
push state or a CI run is a fact about git and GitHub *at a moment*, not a property of this repository.
It went stale three times while this page was being written, every time in the direction of understating
the work, and re-typing the current value fixes it only until the next commit. So the volatile part is
stated as an **as-of** and the durable part as a **rule**:

> **CI is verified per commit, by `head_sha` — never by branch.** A branch query returns the *most
> recent* run, which is not the run for the commit under discussion, and a short SHA returns no runs at
> all. Both mistakes have produced a false green here, which is why the rule is written down instead of
> the number.

1. **Starting commit:** `d50b346` — the merge tip of PR #18, pushed to `main` as `be28069` on
   2026-11-15 01:13 IST.
2. **Final commit of the audited series:** `492e71a` added this page. Commits after it in that series
   corrected this page's own bookkeeping and nothing else.
3. **Branch:** `improvement/scientific-consistency` — pushed and merged as PR #20 into `main` (merge
   commit `44d2a5c`), so that series is public and CI-verified. The follow-up series that §9b describes
   was merged as PR #21 (`d75886a`). **As of this page's last edit**, the evidence-figure series in §9c
   is the only unpushed work. Which branches are actually pushed is a fact about git, not a claim this
   page can keep current — read it from `git log origin/main` — so it is listed here for the sequence,
   not for the state.
4. **Every changed file in the audited series**, relative to `d50b346` and as of `492e71a` — four
   commits, **17 files**, +862/−175. Documentation and records: `README.md`;
   `terratrace/docs/EVENT-ALIGNMENT.md`, `EVENT-WINDOW-CONTRIBUTION.md`, `SUBMISSION.md`,
   `CLAIM-LEDGER.md`; `terratrace/docs/event/` `SI-DISCLOSURE.md`, `eligibility-evidence.md`, and this
   page. Code and configuration: `terratrace/mkdocs.yml`; `terratrace/scripts/`
   `build_submission_deck.js`, `build_deck.js`, `doc_consistency_check.py`;
   `terratrace/tests/test_event_alignment.py`. Regenerated artefacts:
   `TerraTrace-submission.pptx`/`.pdf` and `TerraTrace-deck.pptx`/`.pdf`.
5. **Why each important change was made:** §0, §4 and §7 of this page give the reason for each.
6. **Exact test results:** **1044 passed, 0 failed, 0 skipped** across **106 modules** — the full
   suite, run in nine slices. Slicing is a constraint of the shell (one call is capped well below the
   suite's wall time), not a reduction in coverage; the slice totals sum to the documented count.
7. **Exact scientific-validation results:** **51/51 oracles passed**, aggregate hash
   `0e2c6a2e15069728…`, unchanged from the pinned value.
8. **CI status: verified per commit, by `head_sha`.** Every series audited on this page was checked
   that way, and the run for the merge commit of each succeeded, alongside a successful site deploy and
   a successful Vercel deployment. The earlier wording of this item — that the audited commits were
   local-only and therefore unverified — was true when written and was superseded by the merge; it is
   left legible rather than deleted so the sequence can be followed. **What this item will not do is
   assert a run number**: a run number that is current today is wrong tomorrow, which is the defect this
   page was corrected for three times (F3, F12). Unpushed work has no run to check, and the local
   equivalents of both CI jobs are the stated substitute for it.
9. **Presentation slide count:** the submission deck is **exactly 7**, counted out of the archive by
   test; the project deck is a separate 10.
10. **Demo verification:** site fetched and returned HTTP 200 with current content; all four routes,
    every relative link and every site fragment verified by the guard; the one-command reproduction
    path checked. Browser console errors were **not** verified (§5). The link *count* is deliberately
    no longer quoted here: it changes with every added link, and the "124" that used to sit in this line
    was wrong the moment one was added — a hand-maintained number about an artefact that is itself
    growing. The claim that matters is that the guard checks all of them, and that one is mechanical.
11. **Eligibility status and evidence:** **disclosed, not organizer-confirmed.** Option 1
    (extend-in-window, disclosed) was taken by the submitter on 2026-11-15; the basis is the git
    history, and the record states plainly what the decision does not assert.
12. **Event-window contribution:** 30 commits, 105 files, +36,042/−265 against the pre-window tip —
    eight producing results, nine adding tooling, the remainder re-rendering and not counted.
13. **SI disclosure status:** drafted, complete, using the official 2026 term, covering event-window
    work, and stating that the delivered engine contains no model, no network call and no runtime
    inference. **It has not been pasted into the portal — that is a required field and remains open.**
14. **Remaining blockers:** the SI field is unfilled in the portal; the challenge selection and the
    registration threshold need confirming by the submitter; the eligibility reading is unconfirmed by
    the organizer. All three are portal or organizer actions — not defects a repository can close, and
    not things this page can verify. Whether a given branch has been pushed is **not** a blocker but a
    git fact: read `git log origin/main`, and verify CI for that commit **by `head_sha`** per the rule
    at the head of this section.
15. **Five-judge scorecard:** §8 — overall **4.2/5**, per-judge means 4.3 / 4.0 / 4.5 / 4.1 / 3.9.
16. **Readiness: READY WITH CAVEATS.**
17. **The exact files and links to submit:** the presentation — `TerraTrace-submission.pptx`
    (7 slides), or `TerraTrace-submission.pdf`; the repository —
    <https://github.com/pal-123456789/terratrace>; the live site — <https://terratrace.fit>; the
    project deck, if a second artefact is permitted — `TerraTrace-deck.pdf` (10 slides). The SI text
    is `terratrace/docs/event/SI-DISCLOSURE.md`, pasted into the required field.

## 9b. The follow-up series

A second external mission brief landed after the merge above and asked for a further end-to-end audit.
It named three specific suspects and asked for the rest to be found. Branch `improvement/final-audit`,
based on the actual merged `main` (`44d2a5c`), carries the result.

**The one real correctness defect it named, now fixed.** The brief reported a fractional-distance
calculation dividing by a zero reference descriptor. The measurement behind that report is correct and
worse than it sounds, because there are three different normalisations in the tree and only one of
them mattered:

| path | denominator | behaviour at a zero reference, before |
|---|---|---|
| `matched_benchmark._dist1d` (the production study path) | the reference's robust scale, p90−p10 | already safe — a *spread*, not a value; returns NaN only when the reference has no spread at all |
| `lunar_adversarial.fractional_distance` (the lunar panel) | the reference's own value | **returned NaN** |
| `axis_probe.engine_fractional_distance` (the probe) | the reference's own value | returned `None` — a record, not a number |

The middle one is the defect. A NaN is not neutral there, because `decision.non_dominated` **excludes
any unit carrying a non-finite distance**: a zero-reference axis did not raise, it silently removed
candidates and returned a ranking computed over fewer units than the caller passed in. That is a false
ranking with no error in the output.

The policy now lives in one place, `decision.axial_fractional_distance`, and it refuses instead of
inventing a number: an exact both-zero agreement is a distance of `0.0`, a zero reference against a
non-zero value raises `UndefinedNormalisation` naming the axis and the unit, and so does any
non-finite input. **No epsilon was introduced** — a finite substitute for a diverging ratio would be an
invented scale, which is the thing the brief forbade and the thing the measurement cannot supply.

**Blast radius: none of the published results.** The three declared lunar axes (`mean_slope_deg`,
`mean_relief3_m`, `elev_std_m`) are strictly positive on real terrain, so the refusal never fires on the
panel, and the Mars path never used this normalisation at all — it uses the robust-scale denominator in
the table above. The stress driver's own baseline-reproduction check is the test that holds this: it
re-derives the published layer-1 set through the changed function and rejects the run if the set moves.
Seven tests were added, including one that demonstrates the silent-drop consequence directly rather
than asserting the refusal in the abstract.

**What the brief's other eight documentation suspects produced.** Seven were already clean; the claim
that "the root README says the title was confirmed while `SUBMISSION.md` still labels it open" was
**true**, and is the one documentation defect of the set. `SUBMISSION.md`'s compliance table also still
said the eligibility decision was to be taken "at the event", months of phrasing after it had been
taken. Both rows are corrected in this series. The remaining six were checked item by item and are
recorded as clean in §11 rather than left as silence.

**A number in the frozen protocol already disagreed with its own run.** The pre-run rationale in
`config/lunar_axis_probe_v1.yml` says the NaN audit "shows 13 of the 184 bank descriptors hit exactly
that"; the run recorded 12 for that case. The protocol is deliberately **not** edited — it is the record
of what was declared before the run, and rewriting it to agree with a later result would destroy the
point of freezing it. The disagreement, and the reason the total is 13 now (12 zero-reference plus 1
non-finite input, a cause the policy change made visible), are recorded in `AXIS-PROBE.md`.

**The count cascade, honestly.** Adding seven tests moved the canonical test count from 1037 to 1044,
and the guard immediately reported **23 problems across 15 documents and 5 generated exports** — both
decks, both deck PDFs, the paper PDF and the cover. All 19 prose occurrences and all five artefacts
were regenerated rather than the number being softened anywhere. That cascade is the guard working; it
is recorded because a reader comparing this page against an older deck will otherwise find a
discrepancy and no explanation.

## 9c. The evidence figure, and the disclosure defect that drawing it surfaced

**Why a figure at all.** The distinction this project is built on — that a definite ranking is not an
adequacy result — was carried in prose everywhere and in a picture nowhere. Prose is a poor carrier for
it: it takes a paragraph, and a reader who skims comes away with "Nevada is the Moon analog", which is
the opposite of the finding. There is now one figure, drawn from the committed record and nothing else:
`docs/figures/adequacy-vs-ranking.svg`, generated by `scripts/make_adequacy_figure.py` from
`artifacts/lunar_adequacy/lunar_adequacy.json`, published at the top of the repository README and on the
live site.

**It cannot lie in the ways a figure usually lies.** The generator **refuses to run** when the artifact
is absent, rather than drawing an illustrative version. The guard re-generates it on every run and fails
if the committed SVG and the record have drifted; if the band edge printed on a panel is not the
record's band p95; if any text run leaves the canvas; if two markers overlap; or if the website's copy
of the file diverges from the repository's. The last four are there because the *first* version of the
figure had three layout defects a human eye missed — a label off the left edge, a band label under the
verdict cards, a footer sentence wider than the canvas — and drew five controls as four dots while the
label beside it said "4 of 5 inside", a picture contradicting its own caption. Layout is measured with
the generator's own width estimator now, not inspected.

**Drawing it surfaced a real defect in the written result, and this is the part that matters.** The
published sentence was: adequacy is NOT_ESTABLISHED at all 18 cells *because the reference's own
variability band is so wide that it admits four of the five other lunar sites*. That sentence is true
**at six cells and false as a generalisation of eighteen**, and nothing in the tree could see it. The
band is calibrated per descriptor from held-out sub-windows; at **6 of the 18 cells — exactly the six at
the 500 m support — both descriptor bands exist**, and each admits at least four of the five sibling
sites. At the **other 12, every 750 m and 1000 m cell, there is no relief band at all**: the held-out
sub-windows do not supply one at those supports, so the verdict there rests on the **slope band alone**
— which also admits at least four of the five. The verdict is unchanged, and it in fact rests on a
*weaker* test at those twelve. What was wrong was the *picture of why*: those twelve cells fail for
want of a yardstick, not because the yardstick is permissive, and a reader is owed the difference. The
`established` flag that distinguishes the two cases was in the artifact all along and no page read it.

That sentence has been corrected everywhere it appeared — the repository README, the live site, the
lunar write-up and its summary table, `CLAIM-LEDGER.md` entry 28 (with an inline correction marker
rather than a silent rewrite), the generated atlas page, this page, and the figure itself, which now
states the census in its own header. **Two mechanical checks were added** to
`check_lunar_adequacy` so the census cannot be generalised away again: the split must be stated in the
lunar write-up at all, and the numbers in it must be the record's, including the floor ("at least four
of five") pinned as an equality, because understating that floor would make the band look more
informative than the measurement supports. Both were verified to fire on a doctored copy and to be
quiet on the real tree.

**Why the deck did not get the figure, stated plainly.** The submission deck is capped by the official
rules at **7 slides including the title**, and every one of its 7 is full. Its slide 5 already carries
the adequacy number as a card (`0 / 18`), and its phrasing — "the reference's own band admitting four
of the other five sites" — is true at every cell because a calibrated band exists at every cell. A
figure squeezed into that slide would be about 3.7 inches wide, which renders this figure's 10.5 px
labels at roughly 2.4 pt: unreadable, and an unreadable figure is worse than no figure. So the figure
went where it can be read at full width — the README and the site — and the deck keeps its verified
seven-slide structure.

**The suite's size did not change, and that is a deliberate choice rather than an omission.** The
figure's invariants live in the guard (`check_published_figure`) and are exercised in both directions
by the existing export test, so they run as their own CI step as well as inside the suite. The test
count is quoted in 19 prose sites and 5 generated exports, so each *added test function* costs a full
regeneration cascade of both decks, both deck PDFs, the paper PDF and the cover; a mechanical invariant
belongs in the guard, which is where it also runs on a push. The count cascade described in §9b is the
reason that trade-off is visible instead of invisible.

## 10. Why not READY

The audit's rule was explicit: do not say READY if a mandatory requirement is unresolved. Two are, and
neither is a documentation problem that this repository can close:

- **The SI field is a mandatory submission field and it is not filled** — the text is written and
  ready, but pasting it is a portal action.
- **Eligibility is a reading, not a ruling.** The organizer has not been asked, and the registration
  threshold has not been checked. If a judge were to reject the prior-art reading outright, the
  submission's basis would change.

Everything else in the audit's list is either met and verified by tooling, or met and demonstrably
disclosed. That is the difference between this verdict and READY: not the quality of the artefacts,
but two facts that live outside them.

## 11. Findings register

Severity is assigned by consequence if the finding had shipped unfixed, not by how hard it was to
find. `Status` is `fixed` only where a test or a regenerated artefact proves it.

| ID | Sev | File / function | Problem | Evidence | Impact if shipped | Fix | Verification | Status |
|---|---|---|---|---|---|---|---|---|
| F1 | **P0** | `lunar_adversarial.fractional_distance` | Axial normalisation returned NaN when the reference descriptor was 0, and `decision.non_dominated` silently excludes non-finite units | `non_dominated` excludes NaN vectors; the probe's own audit now records 13 of 184 bank scalars hitting an undefined normalisation — 12 from a zero reference and 1 from a non-finite input, a cause the first version of that audit could not see | A ranking computed over fewer units than were passed in, with nothing in the output to say a unit was dropped | One policy in `decision.axial_fractional_distance`: both-zero is `0.0`, zero-against-non-zero raises `UndefinedNormalisation`, so does any non-finite input | 7 new tests, including one that demonstrates the silent-drop consequence directly; `test_decision`, `test_axis_probe`, `test_lunar_adversarial`, `test_adversarial`, `test_adequacy` = 68/68 | **fixed** |
| F2 | **P0** | `docs/SUBMISSION.md` compliance table | Said the challenge title was **OPEN** and that eligibility was to be "decide[d] at the event", contradicting the root README and the decision record | README and `SUBMISSION.md` line 30 both say confirmed 2026-11-15; the decision record is `[x] Option 1` | The submission page a judge reads first would understate its own compliance and imply an unmade decision | Both rows corrected; the prior-art row now says the artefact **extends** the prior art rather than "must be built inside the window" | `test_event_alignment` 12/12; guard green | **fixed** |
| F3 | **P1** | `docs/event/SUBMISSION-READINESS.md` §9 | Described the audited series as local-only and unpushed, and quoted CI run #62 on an older commit | The series is merged as PR #20 at `44d2a5c`; CI run #65 on that commit succeeded | A reader would take a verified submission for an unverified one, and check the wrong CI run | Items 2, 3, 4 and 8 rewritten against the actual merged state, with the superseded wording left legible rather than deleted | CI queried per-commit (`head_sha=44d2a5c…`), not by branch | **fixed** |
| F4 | **P1** | 19 prose sites + 5 generated artefacts | Published test count 1037 while the suite reached 1044 | The guard listed all 23 as problems on the first run after the tests were added | Every reader, deck and PDF quotes a count the code no longer produces — the exact defect the guard exists for | All 19 replaced; cover, both decks, both deck PDFs and the paper PDF regenerated | Guard green over 31 canonical documents; slide counts 7 and 10 | **fixed** |
| F5 | **P1** | the submission portal | The SI disclosure is written but **not pasted into a required field** | `SI-DISCLOSURE.md` exists and is complete; portal state is not programmatically readable | A required field left empty is a submission failure, not a style issue | None available in-repo — this is a portal action by the submitter | §13 and §14 name it as the first checklist item | **open — submitter** |
| F6 | **P1** | event eligibility | Eligibility is the submitter's reading of the official rule, not the organizer's ruling, and the team-registration threshold is unchecked | Organizer has not been asked; draft inquiry unsent | The submission's basis could change if the reading is rejected | None available in-repo; the reading and its limits are recorded | `eligibility-evidence.md` decision record; alignment §9 keeps this row deliberately not-met | **open — submitter** |
| F7 | P2 | five commits dated 2026-11-14 | Authored as `<pal@example.com>`, which GitHub cannot link to the account, so they display as an unattributed contributor | `git log` over the branch; the five are on `main` | A cosmetic attribution defect on public, already-merged history | **Deliberately not fixed**: re-attributing them rewrites merged public history, and three are cited by hash in the event-window record | The cost/benefit is recorded in the commit message that fixed the five *unmerged* commits instead | **open — won't fix** |
| F8 | P2 | `scripts/doc_consistency_check.py` | Its docstring said the guard is "a few hundred milliseconds, no test execution"; it takes ~57 s on this tree | Measured twice: 57.7 s and 56.7 s, of which ~10 s is the git-backed event-window check | A reader budgets the wrong amount of time, and CI pays it on every push | The docstring now states what the guard actually costs and why it is not milliseconds (it reads git history, unlike every other check in the file), on the ground that a checker whose own docstring misstates its cost is the defect it exists to catch | Re-measured after the figure check was added; the claim is qualitative with the reason attached, not a single number that ages | **fixed** |
| F9 | P3 | the publication surfaces | No figure that **is** the headline result — a reader met the project's central distinction only as a paragraph | §4 of this page | Presentation weaker than the evidence; the strongest idea takes a paragraph to land | **Delivered, not deferred** — `docs/figures/adequacy-vs-ranking.svg`, generated from the adequacy artifact and refused when it is absent, at the top of the repository README and on the live site; both copies are checked for drift, canvas fit and marker overlap by the guard. **Correction to the first two versions of this row:** v1 said the panel data needed to draw it is absent (wrong — the artifact has it); v2 gave the cost of restyling a verified deck as the reason. The real reason the *deck* still has no figure is the official **7-slide cap** with every slide full, and a figure at the only width available would render its labels at ~2.4 pt | Drawing it surfaced the band-census defect in §9c, which is worth more than the figure | **fixed** |
| F10 | P3 | `docs/limitations.md` | The readiness page's own §6 asserted the zero-reference case "is recorded in `docs/limitations.md`" — **and no such entry existed** | `grep` over `limitations.md` returned nothing; the claim was the page's own invention | A reader following the pointer finds nothing, and an audit page that misdescribes its own evidence is worse than one that omits it | The entry now exists, stating the policy and the refusal rather than the hazard; §6 records the correction instead of deleting it | Guard green; the section is now greppable by the phrase the page quotes | **fixed** |
| F11 | **P1** | README, live site, `LUNAR-DEMONSTRATION.md`, `CLAIM-LEDGER.md`, the generated atlas page, this page | The adequacy verdict's *reason* was generalised from 6 cells to 18: "the band is so wide that it admits four of the five other sites" | Both descriptor bands can be calibrated at **6 of the 18** cells (the six at 500 m); the other **12** have no relief band at all, so the verdict there rests on slope alone. The `established` flag was in the artifact and no page read it | A reader is told the yardstick is permissive when at two thirds of the cells there is no second yardstick — a different claim, and a limitation of our own measurement rather than of the Moon | Corrected in all seven places, with the split stated where the reasoning is given; two mechanical checks added to `check_lunar_adequacy`, both verified to fire on a doctored copy | Found by drawing the result rather than by reading it; the figure states the census in its own header | **fixed** |
| F12 | P2 | `docs/event/SUBMISSION-READINESS.md` §9 | The same volatile-claim defect as F3, for the third time: a branch's push state and a CI run number, both of which age the moment anyone commits | `main` moved from `44d2a5c` to `d75886a` during this pass, and the page's quoted run number aged with it | Re-typing the current value fixes it only until the next commit, and each wrong one understates verified work | **Fixed durably rather than again**: the volatile parts are now stated as an as-of, and the durable part is the rule — *CI is verified per commit by `head_sha`, never by branch*. The link count was removed from the demo-verification item for the same reason | The rule is what a reader can act on; F3's and F12's rows both point at it | **fixed — by removing the claim, not by updating it** |

**Checked and found clean** (recorded so that silence is not mistaken for coverage): v3 is never
described as fully pre-registered anywhere; the lunar half is labelled exploratory on every page that
carries its result; the adequacy failure is at least as prominent as the ranking, including on the
submission deck's lunar slide; the axis-probe finding is stated with both numbers (15.90 of 18 and 0 of
141) wherever the lunar headline appears; and the withdrawn Craters of the Moon claim appears only as
a withdrawal, in every document that mentions it.

## 12. Implementation report

- **Starting commit:** `44d2a5c` — the actual merged `main`, verified before any change.
- **Branch:** `improvement/final-audit`, created from that commit.
- **Files changed and why** — 23 files, +456/−60 against `44d2a5c`:

| File(s) | Change | Why |
|---|---|---|
| `terratrace/decision.py` | +48 lines: `UndefinedNormalisation` and `axial_fractional_distance` | One place for the zero-reference policy instead of each call site inventing one; placed next to `non_dominated`, the rule whose silent exclusion makes a NaN dangerous |
| `terratrace/lunar_adversarial.py` | the NaN branch replaced by the shared policy | The defect itself (F1) |
| `terratrace/axis_probe.py` | delegates to the shared policy, keeps its `None` contract | One source of truth; the probe's job is to *record* unnormalisable descriptors, not to run a decision on them |
| `terratrace/tests/test_decision.py` | +7 new tests | F1's verification, including the load-bearing demonstration |
| `terratrace/docs/limitations.md` | new numerical-policy section; event-compliance section rewritten | The entry §6 claimed existed (F10), and a compliance paragraph that still said the submission "must be built during the event" |
| `terratrace/docs/SUBMISSION.md` | the compliance table's title and eligibility rows | F2 |
| `terratrace/docs/event/SUBMISSION-READINESS.md` | this page: §6 corrected, §9b added, §9 reconciled, §11–§15 added | F3, F10, and the brief's deliverable list |
| `README.md`, `terratrace/README.md`, `TerraTrace-PROJECT-BRIEF.md`, `terratrace/docs/PAPER.md`, `terratrace/docs/VALIDATION.md`, `terratrace/docs/DEMO.md`, `site/index.html` | test count 1037 → 1044 | F4 |
| `terratrace/scripts/build_deck.js`, `build_submission_deck.js`, `make_cover.py` | the same count, in the text they print | F4 — a generator is prose too |
| `TerraTrace-deck.pptx`/`.pdf`, `TerraTrace-submission.pptx`/`.pdf`, `assets/cover.png`, `terratrace/docs/TerraTrace-paper.pdf` | regenerated | F4's five generated artefacts; the guard refuses to let an export lag the count |
- **Tests added:** 7, all in `tests/test_decision.py`, covering the defined zero case, every undefined
  case, the axis-naming of the refusal, the load-bearing demonstration, the panel-level refusal, the
  finite-invariant on a well-formed panel, and the exact-agreement case.
- **Tests run:** the full suite, and the science oracles, and the guard.
- **Exact results:** **1044 passed, 0 failed, 0 skipped** across **106 modules**; **51/51** oracles at
  hash `0e2c6a2e15069728…`; guard green over 31 canonical documents, 4 HTML pages and every
  generator script whose output carries a checkable number, the evidence figure included.
- **Unresolved:** F5 and F6 are submitter actions; F7 is a deliberate no-fix; everything else F1–F12,
  including the two P1 defects found in the *last* pass (F11 the band census, F12 the volatile claim),
  is fixed and verified above.

**12b. The evidence-figure pass (§9c).** Against `d75886a`, the merged `main`: **13 files** — the full
change list is the table below. *The inserted/deleted line totals are deliberately not quoted here.* A
report row that quotes the diff it is itself part of is off by one by construction — editing the row to
make the number right changes the number — which is the same self-reference that made the event-window
commit count unmaintainable (§9, F12). `git diff d75886a HEAD --shortstat` reproduces them for anyone
who wants the figure. No test count changed, so no deck, PDF or cover needed regenerating — and the
guard enforces that claim rather than trusting it.

| File(s) | Change | Why |
|---|---|---|
| `terratrace/scripts/make_adequacy_figure.py` | new: the figure generator | F9, and the width estimator that makes its layout checkable instead of eyeballed |
| `terratrace/docs/figures/adequacy-vs-ranking.svg` | new: the figure, generated from the adequacy artifact | F9 |
| `site/figures/adequacy-vs-ranking.svg` | new: the website's copy | A page served from `site/` cannot reach a file outside it; both copies are checked against the generated bytes so a mirror cannot drift |
| `README.md` | the figure at the top of the lunar result, plus the census correction | F9 and F11 |
| `site/index.html` | the figure in the evidence section, plus the census correction and one `<p>` split | F9 and F11 |
| `terratrace/scripts/doc_consistency_check.py` | `check_published_figure`; the HTML-page count added to `COUNT_RES`; the band-census and floor checks in `check_lunar_adequacy`; the corrected runtime docstring; the generator registered in `CANONICAL` (30 → 31) | F8, F11, F12 and F9's mechanical backing |
| `terratrace/tests/test_doc_consistency.py` | the export test extended to exercise the figure check in both directions (and renamed to say so) | A check that is never run in its failing direction gets switched off |
| `terratrace/docs/LUNAR-DEMONSTRATION.md` | the adequacy reason split into the two cases, in the prose, the bullet list and the summary table | F11 |
| `terratrace/docs/CLAIM-LEDGER.md` | entry 28 corrected with an inline *(Corrected …)* marker rather than a silent rewrite | F11; the ledger's own convention |
| `terratrace/scripts/build_atlas_page.py`, `site/atlas/index.html` | the atlas's adequacy note now states the census, read from the record | F11; the page is generated prose and was over-general too |
| `terratrace/docs/EVENT-ALIGNMENT.md`, `docs/event/SUBMISSION-READINESS.md` | the canonical-document and page counts, and the withdrawal of an unguarded generator count | The guard reads its own list, so registering a document moves a number in prose; the generator-script count was quoted in three documents and checked nowhere, so it was removed rather than maintained |

## 13. Scientific result report

The brief asked that six kinds of result be kept apart. They are:

| Category | What qualifies here | What does **not** qualify |
|---|---|---|
| **Software correctness** | The reference-relative normalisation fix: defined cases, refusing undefined ones, seven new tests, no published result moved | — |
| **Method validation** | Five-body projection geometry checked against independently written closed-form geodesy; descriptors checked against their analytic answers by 51 oracles; the reprojection re-derived through a second GIS toolchain | The internal toolchain re-derivation is **not** external validation — it was prepared inside this project |
| **Real-data observations** | The lunar panel: same single Earth candidate non-dominated across 18 of 18 site × support cells, robustness 28 of 30 perturbations | An adequacy claim — adequacy is established at 0 of 18 cells |
| **Confirmatory findings** | Protocol v3's frozen rules returning S supported / V not supported / R supported, on 15 of 15 accounted cells | Not universal: it holds for this panel, these supports and the **core lens**; the other lenses are not replications. v3 is pre-specified, **not** fully pre-registered |
| **Independently reproduced** | **Nothing.** The engine's own checks re-run; nobody outside this project has reproduced a result | The 6-of-100 realisation ensemble, which is the archive's own error model on one site |
| **Externally reviewed** | **Nothing.** No external human reviewer has examined this work | Two AI-assisted review passes are recorded in the repository and are internal to it; per the SI disclosure they were produced with SI assistance and carry no external authority |

That last row is the one most likely to be mis-stated, so it is stated plainly: the project has been
audited hard, **by its own machinery and by model-assisted passes, and by no one else.**

## 14. Judge-ready package

**One sentence.** TerraTrace compares planetary and Earth terrain at a declared common scale and
answers three separate questions — which candidate is least dissimilar, whether any lies inside the
reference's own variability, and whether the evidence is strong enough to say either — and it refuses
to answer when it is not.

**One figure, and it is the argument.** `terratrace/docs/figures/adequacy-vs-ranking.svg`, at the top of
the repository README and on the live site: on each descriptor, the pale band is the lunar reference's
distance from *itself*, and every Earth candidate sits inside it — as do at least four of the five
sibling lunar sites that a geologist would call different terrain. A yardstick that says *adequate* to
terrain from demonstrably different places has established nothing, and that is visible in one look
instead of one paragraph. The figure is generated from the committed record, refuses to be drawn when
that record is absent, and states its own census (it is one of the six of eighteen cells where both
descriptor bands can be calibrated).

**Thirty seconds** (from §8, unchanged): the engine caught its own false analog, withdrew it under a
protocol frozen before the data, measured why, and publishes both the bound on its own headline and a
real correction to its own lunar comparison.

**The seven-slide story** — the submission deck, in order: 1 what this is and where it came from;
2 the challenge and the three separate questions; 3 the method across five worlds; 4 the Mars result
with all six resolution-change classes including the two zeros; 5 the lunar half with its adequacy
failure stated as prominently as its ranking; 6 the evidence behind every number; 7 the limits, named
first, and what would help most.

**A demonstration inside the official limits.** The 7-slide deck **is** the permitted demo. The
21⁄2-minute script in `DEMO.md` is **not** admissible and says so at the top. If a video is wanted, this
is the ≤30-second script, timed:

> *(0–8 s)* "Which Earth terrain is a real analog for the Moon or Mars? Asking a search engine gets you
> a postcard. TerraTrace answers with a measurement." *(8–18 s)* "It compares real NASA and ESA
> elevation data at one declared scale, across five worlds, and answers three separate questions —
> ranking, adequacy, sufficiency — with no composite score." *(18–27 s)* "It caught its own false
> analog: a famous basalt field it had favoured, which it withdrew under a protocol frozen before the
> data. Then it measured why roughness, not volcanic origin, was driving the answer." *(27–30 s)*
> "terratrace dot fit. Every number has a receipt, and the limits are named first."

**The five official judging criteria**, scored honestly with their evidence:

| Criterion | Score | Strongest evidence | Biggest weakness | The one improvement |
|---|---|---|---|---|
| **Impact** | 4 | A false analog is expensive to build on; this refuses one and shows its work | Screening only — no traversability, hazard, access or readiness claim | State the cost of a false analog in one concrete sentence on slide 1 |
| **Creativity** | 5 | The refusal machinery: publishing the bound on its own headline, and an atlas that will not write a file if two of its records disagree | Under-sold on the page a judge opens first — the idea took a paragraph to land | Delivered: the figure now lands it in one look on the README and the live site (F9), and drawing it surfaced a real disclosure defect of its own (§9c) |
| **Validity** | 4 | 51 correctness oracles, five-body geometry against closed-form geodesy, a pre-registered withdrawal, deterministic hashes | Confirmation is single-lens, and v3 is pre-specified rather than pre-registered | A replicated confirmatory panel on fresh held-out terrains |
| **Relevance** | 5 | Directly answers the challenge's question, on real lunar terrain, with the Moon half not a stretch goal | The *geographic* answer is a screening candidate, not a named analog site | Label the leading candidate explicitly as a screening candidate on the slide that names it |
| **Presentation** | 4 | Unusually clear prose; a README usable in 30 seconds; limits named first; a live site; one figure that carries the central distinction | Seven slides cannot carry this much caveat without reading as cautious | The ≤30-second video above, as a companion to the deck |

**Likely difficult questions, with accurate answers.**

1. *Did you build this during the event?* The toolkit predates it and is published prior art; 30 dated
   commits inside the window produced eight new results, including the correction of one of the
   project's own published comparisons. Both halves are listed with dates and hashes.
2. *Which Earth location is the answer?* The engine names the least-dissimilar candidate and refuses to
   call it adequate. That refusal is the position, not an omission.
3. *Is the lunar result a finding?* It is a relative screening observation on six nearby sites, and the
   submission says so before being asked: adequacy is established at none of the 18 cells.
4. *Are your lenses independent evidence?* No — they are distinct, not independent, the repository says
   so in those words, and a check keeps that wording honest.
5. *Has anyone else verified this?* No. It has been audited by its own machinery and by model-assisted
   passes; no external human reviewer has examined it, and the SI disclosure says so.
6. *Why should a judge trust the numbers?* Because the guard computes every published count from the
   source or the artefact and fails the build when prose drifts — including the count on this page.

**Limitations, in one paragraph.** Map-scale terrain morphology only, between curated map products, at
a declared support. No traversability, autonomy, geologic equivalence, site access or mission-readiness
claim, and no NASA endorsement. The Mars confirmation is single-lens and pre-specified rather than
pre-registered. The lunar half is **exploratory**: six nearby sites are not six tests, the error
ensemble is six of a hundred published realisations, the three declared axes collapse to one effective
dimension, and the sole-winner is a property of the run rather than of a candidate — a uniformly random
fourth coordinate moves that frontier in 15.90 of 18 cells and nothing in the bank beats it.

**Data and software credits.** NASA PDS/MOLA (Mars), LRO/LOLA and the NASA Goddard PGDA south-polar
products (Moon), MESSENGER (Mercury), Dawn (Ceres); ESA Copernicus GLO-30 via the public AWS COG mosaic
and via OpenTopography; USGS 3DEP, SRTM, NASADEM, JAXA ALOS. Each under its own terms, cited per source
in `sources.lock.yml` and `REAL-DATA-RUNBOOK.md`. Code: MIT. Numerical stack: NumPy, plus rasterio for
the optional GIS paths. The engine contains no model, no network call and no runtime inference.

## 15. Final classification

The brief offered a scale — Worst / Poor / Normal / Good / Excellent / Extraordinary / Insane — and
then set the bar for the last rung itself: *it earns that classification only if its scientific
evidence, implementation, reproducibility, usefulness and communication justify it*, and not because
it has many files, descriptors, tests or features. Measured against that bar:

**Excellent.** The implementation and reproducibility are genuinely strong: 1044 tests with no skips,
51 oracles, deterministic hashes, a guard that audits its own prose, and a live site that serves the
current result. The communication is strong and unusually honest. What keeps it off the top two rungs
is evidence, not engineering: the flagship lunar result is a **relative screening observation** whose
absolute question is answered nowhere, its three declared axes are one axis, and its sole-winner is a
property of the rule rather than of a candidate. The Mars confirmation is real but single-lens and
pre-specified rather than pre-registered.

**Insane is not warranted, and calling it that would be exactly the inflation the brief forbade.** The
project identifier by its own audit is not "many features" — it is that it publishes the bound on its
own headline, withdraws its own attractive finding, and fails the build when its prose drifts. Those are
quality signals, and they earn Excellent.

**What the last pass changed, and why it does not change this.** The evidence figure, the census
correction it surfaced (F11) and the guard extensions improve the *presentation* and the *machinery*.
None of them adds evidence, and the census correction in particular moves a published claim in the
direction of **less** support, not more: at twelve of the eighteen cells the adequacy verdict rests on
one band instead of two. A project that treats its own disclosure as a score-improvement would be
doing the thing this whole audit exists to prevent, so the classification is unchanged at **Excellent**
— with two P1-class defects found and fixed inside this pass rather than carried into the submission,
which is what the classification was already paying for.

**What would move it up, in order of value.** One: an **external reproduction** — anyone outside this
project re-deriving one published number from the raw data, which is the single largest gap in the
table in §13. Two: a **replicated confirmatory panel** on fresh held-out terrain, which would convert
"pre-specified" into "pre-registered and replicated". Three: an **independent morphological axis** —
the probe found none in the bank, so this needs a descriptor that is not a function of the same
gradient, which is a research problem rather than a coding one. None of the three is achievable inside
the remaining hours of an event window, so all three are named as next steps rather than attempted.
