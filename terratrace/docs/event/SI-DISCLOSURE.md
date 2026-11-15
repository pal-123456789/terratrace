# SI-tool disclosure (2026 submission requirement)

The 2026 judging and awards guide requires, in the required fields of the Project Submission page:

> Each team's project submission must include a description of how SI tools were used during the
> development of their project.

The 2026 event uses the official term **Super Intelligence (SI)** for computer systems that perform
tasks typically associated with human reasoning, decision-making, content creation and
problem-solving — large language models among them. The requirement is not optional and applies
regardless of how small the contribution was.

Two things about this project make the disclosure short and easy to write honestly. The AI assistance
is not incidental to the work, and the repository already carries a dated record of it: the commit
history, the generation scripts it contains, and this documentation are the evidence trail. Understating
the extent of the assistance would be a defect of the same kind as overstating a result, and it is the
one kind of defect a disclosure exists to prevent.

## Text to paste into the submission's SI field

> **How SI tools were used.**
>
> SI tools were used throughout the development of TerraTrace, and the sections below describe what
> they were used for and what they were not trusted to do.
>
> **Design and literature orientation.** SI tools were used to survey the relevant literature —
> planetary analog studies, the published lunar south-polar candidate regions, and the standard
> terrain descriptors — and to help frame the question the engine answers. The primary sources they
> pointed at were then read directly and are cited in the repository; nothing is cited from a
> model's recollection.
>
> **Implementation.** The engine, the projection and grid arithmetic, the frozen benchmark protocols,
> the experiment drivers, the test suite and the documentation were drafted with SI assistance. Every
> line of it was reviewed, run and either accepted or rejected by a human operator, who is the sole
> author of record in the commit history.
>
> **Adversarial review.** The project's two external reviews — including the one that produced the
> lunar correction it now publishes — were produced with SI assistance. So were the internal audits:
> the dependence analysis that showed three of the lunar descriptors are one axis, the 30-perturbation
> robustness stress test, and the verification passes.
>
> **Generation of the published artefacts.** The submission deck, the paper and the site's build are
> generated from committed scripts rather than assembled by hand. SI tools wrote those scripts; they
> do not assemble the content at submission time.
>
> **What SI tools were not used for.** No SI system is part of the delivered product. TerraTrace
> contains no model, no network call, no API key and no runtime inference of any kind: it is a
> deterministic geometry and terrain-statistics engine, and the demonstration runs with the network
> switched off. No result, number, citation or dataset in this submission was produced by asking a
> model for it — every figure is computed from a real dataset by code in this repository, and every
> source is cited to the primary document.
>
> **Human accountability.** The direction of the work, the decision to withdraw a result it had
> previously published, and every claim in the claim-to-evidence ledger were human decisions. The
> project's most prominent finding is a claim it disproved about itself, and it publishes that
> alongside its results.

> **What was built inside the event window.** The toolkit pre-dates the event and is published prior
> art; the submission is the work done during 14–15 November that extends it. Twenty-nine commits are
> dated inside the window, and the substantive ones produced, rather than re-presented, results: real
> lunar radar terrain was ingested and compared for the first time; a **common-support defect in the
> project's own published lunar comparison was found, corrected and re-run**, with the corrected
> result larger than the one it replaced; the three declared lunar descriptors were shown — derived
> and then measured — to be **one axis**; a **30-perturbation adversarial stress test**, declared
> before it ran, found the panel robust at 28 of 30; ranking, adequacy and sufficiency were separated
> as three verdicts, which showed the lunar panel fails the absolute question at every cell; the
> projection was validated on **all five bodies** against independently written closed-form geodesy;
> and an **independent-axis probe** established the sharpest result of the window — that the lunar
> panel's sole-winner property is a property of running a Pareto rule over eight units in three
> dimensions, since a uniformly random fourth coordinate moves that frontier in 15.90 of 18 cells and
> none of 141 candidate axes beats it. SI tools assisted with all of it, in the same roles described
> above, and the human operator directed the work, ran every experiment and decided every claim.
>
> **Event-window length.** This disclosure was completed on the second day of the window; the commit
> dates, not this paragraph, are the record of what was built when.

## What to adjust before pasting

- The text describes the work as it stands in the repository. If more is built today, name it in the
  first paragraph above.
- The SI field is a **required** field. An empty one is a submission failure, not a stylistic omission.
- The official 2026 term is **SI / Super Intelligence**. Use it.
- Nothing in the text should be broader than the commit history supports.

## Checked before pasting

- The word used is **SI**, the official 2026 term, not "AI" alone.
- The field is filled at all — an empty SI field is a required-field failure, not a stylistic
  omission.
- Nothing in the text is broader than the commit history supports.
