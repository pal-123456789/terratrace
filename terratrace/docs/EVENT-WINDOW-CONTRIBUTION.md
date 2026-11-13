# Event-window contribution record

**Eligibility is NOT confirmed, and this page does not claim it is.** It records the state of the
evidence so the decision is made on facts rather than on optimism.

Written 2026-11-13, the day before the official event window opens.

## 1. The rule we are working to

From `CLEAN-ROOM-NOTE.md`, which records the official 2026 guidance as understood at the time:

> The official 2026 NASA Space Apps Challenge runs **November 14–15, 2026**. Official guidance allows
> participants to prepare, learn tools, and explore data beforehand, but says teams **may not develop
> the solution they intend to submit before the event begins**; submitted project work must occur
> during the event window.

The operative clause is *the solution they intend to submit*. Timezone of the official window and
the precise treatment of open-source prior work are **not** resolved by anything in this repository;
the rule is quoted, not interpreted.

## 2. Pre-event state, as it actually stands

The event window has not begun. At the time of writing, **every commit in this repository is
pre-event**.

| fact | value |
|---|---|
| Commits at the time of writing | 75 |
| Latest pre-event commit | `b63f612`, 2026-11-13 |
| Tag | `v0.3.0`, 2026-11-13 |
| Event window | 2026-11-14 to 2026-11-15 — **not started** |
| Event-window contribution so far | **none** |

What exists pre-event, all of it public: the five-body morphology engine, the six decision lenses,
the 852-test suite and 51 scientific oracles, the protocol v2 negative result and the v3
confirmatory result, the keyless Copernicus COG Earth path, the website, the deck, the documentation
set, and this improvement pass.

## 3. What would count as an event-window contribution

Only work committed during 2026-11-14/15 is candidate event work. If a submission is made, this
page should be updated with the exact commits, their dates and their content, so the boundary is
auditable rather than asserted. Candidates that would genuinely be event-window work:

- any new experiment run inside the window (for example the lunar comparison, if a working data
  endpoint is found);
- any new descriptor, lens or validation oracle written during the window;
- any new user-facing artifact produced during the window.

Re-running the existing pipeline, re-rendering the existing figures, or re-wording the existing
documentation would **not** be a new contribution, and should not be presented as one.

## 4. The decision, and why it is not made yet

`CLEAN-ROOM-NOTE.md` sets out two acceptable paths:

1. **Fresh build.** Treat this repository as published prior work. During the window, build the
   submission as a new event project, relying on the published method the way one would rely on any
   public library or paper, subject to the official terms on original content and citation.
2. **Written clarification.** Ask the organizer whether continuing a public project is eligible, and
   hold the written answer **before** submitting.

Path 1 is the conservative choice and is the one this repository's own framing assumes: it presents
the project as **published open prior art**, not as event work. Path 2 depends on an answer we do not
have.

**The decision is not made, and it must be made by the submitter.** Nothing in this repository
should be read as confirmation that either path has been accepted by the organizer.

## 5. Draft inquiry (not sent)

If path 2 is chosen, this is the ask. **It has not been sent, and sending it needs explicit
authorization.**

> Subject: Eligibility question — pre-existing open-source project, NASA Space Apps 2026
>
> Hello,
>
> I would like to clarify the 2026 rules on pre-existing open-source work. Before the event, I
> published a public repository (github.com/pal-123456789/terratrace) containing a terrain-morphology
> screening engine and a documented benchmark over public NASA/ESA DEMs. It is clearly dated in its
> public commit history, licensed MIT, and is not presented anywhere as event work.
>
> Could you confirm which of the following is acceptable for submission: (a) submitting a project
> that extends this public work during the event window, with the pre-event state disclosed; or
> (b) requiring a fresh build during the window, with the prior work citable as a public method?
>
> I want to make sure the submission is compliant and disclosed honestly, so I would rather ask
> before submitting than after.
>
> Thank you.

## 6. What must NOT happen

- Do not present this codebase as created during the event.
- Do not remove or rewrite the public history to disguise its origin.
- Do not claim NASA endorsement or official status — `CLEAN-ROOM-NOTE.md` says this and the claim
  firewall is enforced in the shipped artifacts.
- Do not treat this page as evidence that eligibility has been confirmed. It is not.

## 7. Status

| item | status |
|---|---|
| Rule recorded | **DOCUMENTED** — quoted from the official guidance in `CLEAN-ROOM-NOTE.md` |
| Pre-event state recorded | **DOCUMENTED** — 75 commits, latest `b63f612`, tag `v0.3.0` |
| Event-window contribution | **NONE — the window has not opened** |
| Eligibility decision | **NOT MADE** |
| Organizer clarification | **DRAFTED, NOT SENT** — needs authorization |
