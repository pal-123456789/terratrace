# External-user walkthrough

**Status: internally tested.** The author walked this path; no external person has. Where that
matters it is said so below. Nothing in this document is user feedback, because there has not
been any.

## What a reader needs

A browser, and nothing else — no account, no API key, no network once the pages are open. Every
page in the canonical flow is self-contained: the study viewer is a single generated HTML file
with its data inlined, and the reports ship beside it.

Three routes, each answering a different question:

| route | what it is |
|---|---|
| `/` | the project story — the question, the finding, and the honest caveats |
| `/study` | the protocol-v3 result on real data, with the frozen protocol and the full results document linked |
| `/viewer` | the generated study viewer for the committed synthetic study — the engine's own output, unedited |

## The eight steps

**1. Open a planetary reference terrain.** On `/viewer`, the first section lists the reference
unit with its body, source product, native posting and the common support used. You are looking at
Mars; the page states that the comparison happens at a declared support, not at native posting.

**2. Select an Earth candidate.** The comparison table lists each Earth candidate with its class
label — `smooth_control`, `basaltic`, `other` — assigned *before* the run. That labelling is part
of the frozen config, not a post-hoc story.

**3. Check the comparable physical extent.** The adequacy section reports, per candidate, the
window actually realised in metres and whether it was truncated. If a candidate could not be
matched to the same physical extent, that is stated rather than hidden.

**4. View terrain and descriptors.** The terrain previews are shaded-relief images of the real
DEMs. The descriptor table gives each measured axis with its value and unit; the DECISION MATRIX
shows the per-axis distances.

**5. Understand the Pareto result.** The DECISION MATRIX is the decision. A candidate on layer 1
is not beaten on every axis by another; nothing is summed into a single score. If you are looking
for one number that says which terrain is best, the tool does not have one — by design.

**6. Inspect uncertainty and robustness.** The DECISION CONFIDENCE panel carries bootstrap
intervals, the sensitivity view shows whether a rank flips under a re-weighting, and the adequacy
section compares each candidate against the reference's own internal variability.

**7. See why it recommends, ties, abstains or blocks.** Four states plus `BLOCKED`: a water or flat
tile is filtered out before scoring, `INDETERMINATE` means insufficient evidence, `TIE` means the
evidence does not separate candidates. The rule that produced the state is printed beside it.

**8. Reach provenance and reproduction.** The evidence graph traces each visible number to source,
transform and unit; `checksums.txt` and `manifest.json` carry the artifact identity; the protocol
and results documents are linked. `docs/RESULTS-v3.md` is where the real-data verdicts live.

## The two-minute narrative

> TerraTrace screens Earth terrain for morphological resemblance to a planetary reference, at a
> declared common spatial support, across five bodies.
>
> The question is narrow on purpose. It measures terrain **shape** — slope, relief, ruggedness,
> roughness, openness, landform class. It does not measure whether a surface is trafficable,
> whether a site is accessible, or whether two terrains are geologically equivalent. It cannot,
> and it says so in every report.
>
> The decision is Pareto dominance over measured axes. There is no composite score anywhere in the
> code, because a weighted sum hides the trade-off that a reviewer most needs to see. It is allowed
> to answer TIE, and it is allowed to answer INDETERMINATE.
>
> Our earlier work suggested a specific Earth analog for Martian volcanic plains. We pre-registered
> a matched-footprint test to falsify it, it failed, and we withdrew the claim in public. Protocol
> v3 then asked what actually explained the match. The answer, measured: **roughness does the work;
> volcanic origin does not.** Of fifteen confirmatory cells, eleven were unchanged under a change of
> support, three changed membership, one destabilised, and none reversed.
>
> v3 is pre-specified, not fully pre-registered — the rules and config predate the run, the protocol
> document does not. Its verdicts use the core decision lens, and we do not present the other lenses
> as independent replications.
>
> The lunar half of the challenge is supported by the engine and not yet demonstrated; the reason is
> a dead data endpoint, and it is written down rather than glossed.

## Questions a planetary researcher might ask

**"Which of these Earth sites is the right analog?"** None is asserted to be. The engine returns a
non-dominated set and a class-level pattern. The single top-of-shortlist pick is a near-tie that
reverses under a six-pixel crop shift, and we say so.

**"Why should I believe the roughness numbers?"** They are computed by a pure-NumPy operator, and
two independent implementations (RichDEM, WhiteboxTools) reproduce them on this study's own windows
within a documented tolerance. The reprojection they sit on is *not* independently reproduced — it
is GDAL either way.

**"Is MOLA good enough at 463 m?"** For 60 km morphological windows at 1.5 km support, it is what
this study used, and its vertical accuracy is carried per source in the catalog. It is not adequate
for anything at metre scale, and the comparability gate refuses cells below the support their
source can carry.

**"What is the false-discovery risk across so many descriptors?"** Real, and stated: the confirmatory
panel is small (three plains references, two highlands), the sites are spatially dependent within a
window, and no universal adequacy threshold exists. The verdicts are reported per cell so a reader
can see the dependence rather than a single p-value.

**"Would this survive being re-run by someone else?"** The software: yes, from a clean checkout, with
no credentials on the Earth path. The science: that is exactly the open item — an external reviewer
has not re-derived it, and the project says so in the open list rather than implying otherwise.

**"Can I use this to pick a landing site?"** No. It narrows a search over terrain morphology. It
makes no claim about trafficability, access, illumination, thermal environment or mission readiness.

## What is deliberately missing

No demo video (the script is in `docs/DEMO.md`), and no external user has walked this path. Both are
named in the open list in `docs/PLAN-COMPLIANCE.md` rather than left for a reader to find.
