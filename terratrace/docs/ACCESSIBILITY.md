# Accessibility report

The master plan (§5, module 09) makes nine accessibility properties **non-negotiable**, and module 18
lists an accessibility report in the release package. This is that report, written the only way it
can honestly be written: one row per requirement, saying what is implemented, where, and — crucially —
**what was verified versus what was only inspected**. Nothing here claims a user test that did not
happen.

## Scope and method

There are three surfaces: the landing page (`site/index.html`), the results page
(`site/study/index.html`), and the engine's generated viewer (`site/viewer/index.html`, produced by
`terratrace/build_viewer.py`). All three are static documents with inline CSS; two carry a small
amount of progressive-enhancement JavaScript, and none requires it.

**Verified by inspection**: reading the source and the generated output. **Not verified**: no screen
reader was run, no automated rule engine (axe-core) was run, and no keyboard-only or assistive-
technology user has walked the flow. Those are named in the open list at the end.

## The nine non-negotiables

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Every map conclusion exists in an equivalent table | **Met** | The engine is table-first: distances, Pareto layers, bootstrap intervals, the gap ledger and the protocol are all tabular. The only image-like outputs are optional previews (hillshade, landform and openness maps) rendered *in addition to* a composition table, and they are absent unless `previews=True`. A conclusion cannot exist only as a picture |
| 2 | Keyboard operation completes the prepared flow | **Met, by construction** | Every control is a link, a native `<details>`/table, or a scroll. There is no drag interaction, no canvas control, and no custom widget to trap focus. The landing page's 3D canvas is `aria-hidden="true"` and purely decorative; the page is complete without it. *Inspected, not user-tested* |
| 3 | No colour-only status encoding | **Met on the primary surfaces; one named caveat** | Result states are chips whose text reads `RECOMMEND` / `TIE` / `NOT COMPARABLE` / `BLOCKED`; the roughness ladder's bars each carry `σ N m` as text; T-class chips read `T0`…`T4`. **Caveat:** the *optional* landform and openness preview images encode class by colour alone. The underlying class composition is always present as a table, so no conclusion is colour-only — but the preview tiles themselves are |
| 4 | Patterns, text, icons and explicit uncertainty labels accompany colour | **Met in part** | Uncertainty is printed as text intervals (`1.33 [1.25–1.40]`) and the five-number summaries are numeric, never implied by a shade. There are no icons or hatching patterns anywhere, so this requirement is satisfied vacuously rather than deliberately — stated so it is not read as effort that was made |
| 5 | Charts offer text summaries and downloadable CSV/JSON | **Met for text + JSON; CSV not offered** | Every “chart” is a table (text summary), and the viewer embeds the complete package JSON in a `<pre>`; `export_bundle.py` ships `study.json` plus `CHECKSUMS.txt`. **No CSV export exists.** Adding one would change the bundle's file manifest, which `tests/test_bundle.py` asserts exactly; it is recorded here as a deliberate deferral rather than done at the last minute |
| 6 | Reduced-motion preference is respected | **Met** | `site/index.html` and `site/study/index.html` both gate motion on `@media (prefers-reduced-motion: reduce)`; the landing page also short-circuits its GSAP reveal and Lenis smoothing in JavaScript, and the study page's scroll reveal is disabled under it. The generated viewer contains no animation at all |
| 7 | Works at 200 % zoom and narrow mobile width | **Met** | Both pages reflow: single-column grids, an h1 clamp, and — as of this pass — tables that **wrap** rather than squish or scroll. Choosing wrap over a horizontal scroll container was deliberate: a scrollable region must be focusable to remain keyboard-reachable (WCAG 2.1.1) and the generated viewer ships no script to make it so. `word-break` plus reduced padding keeps every cell's value visible at 375 px |
| 8 | No WebGL required | **Met** | The study page and the viewer use none. The landing page's WebGL scene is decoration: if `THREE` is absent or the context fails, the script returns early and the page renders complete, because all content is in the DOM rather than on the canvas |
| 9 | Prepared comparison reachable without a pointer | **Met** | Nav is anchor links; the study page's sections are in document order; nothing is hover-only |

## Additional measures worth naming

The generated viewer emits `scope="col"` / `scope="row"` on every table header (13 occurrences in the
archived study), so a screen reader can associate each cell with its row and column header. The
landing page's images and decorative layers carry `aria-hidden`, and the SVG figures in
[`figures/`](figures/) carry `role="img"` with a descriptive `aria-label` that states the finding in
words — so the figure is not a picture of data with no textual equivalent.

## Known gaps (open, not hidden)

1. **No assistive-technology walkthrough** and **no automated a11y scan** have been run. Every “Met”
   above is an inspection, not a measurement.
2. **Colour-only preview tiles** (item 3 caveat) — the composition tables carry the same information.
3. **No CSV export** (item 5).
4. **Colour contrast was chosen by hand, not measured.** The muted grey `#93A4AC` on `#060910` is
   comfortably above 4.5:1, and body text is `#C7D0D4` or lighter, but no contrast checker has been
   run over the two token sets. This is a five-minute job with a checker and should be done before
   claiming conformance.
5. **No 200 %-zoom screenshot review** — the responsive rules are inspected, not eyeballed at zoom.

Closing gaps 1, 4 and 5 needs a browser and a person; they are the accessibility half of the open
list in [`PLAN-COMPLIANCE.md`](PLAN-COMPLIANCE.md).
