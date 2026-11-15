#!/usr/bin/env python3
"""Draw the two diagrams the readable files were missing: the pipeline, and the refusal logic.

WHY HAND-BUILT SVG AND NOT A DIAGRAM TOOL. These are the only figures in the repository that are
**transcriptions of the code rather than plots of data**, and that is precisely why they must be
reviewable: every box below names a module, a CLI step or a gate that exists in this tree, so a
reader can check a box against the file it names. A drawing tool would put that mapping somewhere
nobody diffs.

WHAT THEY ARE NOT. No number here is measured, and no box claims a capability the engine does not
have. The pipeline diagram says what happens in order; the decision diagram says when the engine
answers and when it refuses, which is the project's actual contribution and reads badly as prose.

DETERMINISTIC. No dates, no environment, no fonts beyond a family list, no random ids: the same
source produces the same bytes, which is what lets ``check_published_diagrams`` in
``scripts/doc_consistency_check.py`` regenerate both files and fail the build on drift.

USAGE
    python3 scripts/make_diagrams.py            # writes docs/figures/pipeline.svg and decision-flow.svg
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_DIR = ROOT / "docs" / "figures"

FONT = "Helvetica,Arial,sans-serif"
INK, MUTE, RULE = "#24292F", "#57606A", "#D0D7DE"
BG, PANEL = "#FFFFFF", "#F6F8FA"
OK, WARN, BAD, GATE = "#0B7A75", "#B26A00", "#B4232A", "#8250DF"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(x, y, w, h, title, sub="", *, stroke=RULE, fill=PANEL, tcol=INK, sway=None):
    """A rounded box with a bold title and an optional smaller line beneath it."""
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" '
         f'stroke="{stroke}" stroke-width="1.4"/>',
         f'<text x="{x + w / 2:.1f}" y="{y + (22 if sub else h / 2 + 4):.1f}" font-family="{FONT}" '
         f'font-size="12.5" font-weight="700" fill="{tcol}" text-anchor="middle">{esc(title)}</text>']
    if sub:
        o.append(f'<text x="{x + w / 2:.1f}" y="{y + 39:.1f}" font-family="{FONT}" font-size="10.5" '
                 f'fill="{MUTE}" text-anchor="middle">{esc(sub)}</text>')
    if sway:
        o.append(sway)
    return o


def arrow(x1, y1, x2, y2, col=RULE, dash=False):
    d = ' stroke-dasharray="4 3"' if dash else ""
    head = (f'<path d="M{x2:.1f},{y2:.1f} l-5,-3.2 l0,6.4 z" fill="{col}"/>'
            if abs(y2 - y1) < 0.5 else
            f'<path d="M{x2:.1f},{y2:.1f} l-3.2,-5 l6.4,0 z" fill="{col}"/>')
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" '
            f'stroke-width="1.3"{d}/>' + head)


def label(x, y, s, size=10.5, fill=MUTE, anchor="middle", weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size:g}" fill="{fill}" '
            f'text-anchor="{anchor}"{w}>{esc(s)}</text>')


def svg_open(w, h, aria):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(aria)}">\n<rect width="{w}" height="{h}" fill="{BG}"/>')


def pipeline():
    """The ingest-to-surface path, numbered in the order the code runs it.

    Numbered rather than snaked: a diagram that alternates direction to keep arrows short makes the
    reader reconstruct the order, and the order IS the content here.
    """
    W, H = 1120, 470
    o = [svg_open(W, H,
                  "The TerraTrace pipeline in twelve numbered stages: config and fail-fast preflight, "
                  "fetching through the source catalog, a per-body metric grid, masking and quality "
                  "gates, the descriptor bank, a comparability gate, Pareto decision over the declared "
                  "axes, three separate verdicts, a hashed artifact package, and the reader-facing "
                  "surfaces.")]
    o.append(label(30, 34, "The pipeline — every box names a module or a CLI step in this repository",
                   14, INK, "start", 700))
    o.append(label(30, 52, "read 1 → 12, left to right, top to bottom", 10.5, MUTE, "start"))

    stages = [
        ("1 · Config", "declared reference, candidates, support"),
        ("2 · Preflight", "fail-fast, no network, sizes the request"),
        ("3 · Source catalog", "coverage-checked product choice"),
        ("4 · Fetch", "MOLA keyless · Copernicus COG keyless"),
        ("5 · Metric grid", "local AEQD, WGS84 / IAU spheres"),
        ("6 · Mask + QA", "water, sentinel, flat-run, valid fraction"),
        ("7 · Descriptor bank", "40 families, ~290 scalar values"),
        ("8 · Comparability gate", "same support, or it refuses"),
        ("9 · Pareto decision", "dominance only — no composite score"),
        ("10 · Three verdicts", "ranking · adequacy · sufficiency"),
        ("11 · Hashed package", "study.json · manifest · checksums"),
        ("12 · Surfaces", "viewer · site · decks · paper"),
    ]
    cols, bw, bh, gx, gy = 4, 250, 60, 20, 30
    x0, y0 = 30, 78
    for i, (title, sub) in enumerate(stages):
        c, r = i % cols, i // cols
        x, y = x0 + c * (bw + gx), y0 + r * (bh + gy)
        stroke = GATE if i == 7 else RULE          # the gate is the one stage that can refuse
        o += box(x, y, bw, bh, title, sub, stroke=stroke)
        if c < cols - 1:
            o.append(arrow(x + bw, y + bh / 2, x + bw + gx - 2, y + bh / 2))

    yside = y0 + 2 * (bh + gy) + bh + 26
    o += box(x0, yside, 545, 46, "Validation — 51 analytic oracles",
             "closed-form answers, re-run on every change", stroke=OK, fill="#F2FAF9", tcol=OK)
    o += box(x0 + 565, yside, 495, 46, "Documentation guard",
             "fails the build when prose drifts from the code", stroke=OK, fill="#F2FAF9", tcol=OK)
    o.append(label(30, H - 12,
                   "Nothing here estimates traversability, autonomy, geological equivalence, site "
                   "access or mission readiness; stage 8 is where a comparison that cannot be made "
                   "honestly is refused rather than fudged.", 10.5, MUTE, "start"))
    return "\n".join(o) + "\n</svg>\n"


def decision_flow():
    """When the engine answers, and when it refuses — the project's actual contribution."""
    W, H = 1120, 548
    o = [svg_open(W, H,
                  "The decision logic: a comparability gate that can refuse, a Pareto ranking that "
                  "cannot be collapsed into a score, an adequacy band calibrated from the reference "
                  "itself that is demoted when it admits known-different terrain, and a sufficiency "
                  "verdict reported separately. Three answers to three questions, never merged.")]
    o.append(label(30, 36, "What the engine answers — and the four places it refuses instead",
                   15, INK, "start", 700))

    qw, qh = 300, 46
    qx, rx = 30, 700
    def q(y, text, sub=""):
        return box(qx, y, qw, qh, text, sub, stroke=GATE, fill="#FBF7FF", tcol=GATE)
    def r(y, text, sub, col=WARN, fill="#FFF8EC"):
        return box(rx, y, W - rx - 30, qh, text, sub, stroke=col, fill=fill, tcol=col)

    ys = [70, 150, 230, 310, 390]
    o += q(ys[0], "1 · Are the units comparable?", "same support, valid coverage, not degenerate")
    o += r(ys[0], "BLOCKED / NOT COMPARABLE", "no verdict is issued, and the reason is named", BAD, "#FCF3F3")
    o += q(ys[1], "2 · Which candidate is least dissimilar?", "Pareto dominance over the declared axes")
    o += r(ys[1], "A RANKING — definite, or an honest TIE / indeterminate",
           "well defined however weak the field; never a score", OK, "#F2FAF9")
    o += q(ys[2], "3 · Can a band be calibrated at all?", "the reference's own held-out sub-windows, 95th pct")
    o += r(ys[2], "ADEQUACY NOT ESTABLISHED", "no yardstick exists at this support — reported, not guessed", BAD, "#FCF3F3")
    o += q(ys[3], "4 · Does the band admit different terrain?", "the five sibling lunar sites are the controls")
    o += r(ys[3], "NOT ESTABLISHED — the yardstick is too permissive",
           "membership in it is not evidence of similarity", BAD, "#FCF3F3")
    o += q(ys[4], "5 · Is the evidence enough to say either?", "candidates, supports, band, ensemble, axes")
    o += r(ys[4], "INSUFFICIENT · MARGINAL · SUFFICIENT", "always reported with its reasons", WARN)

    for i, y in enumerate(ys):
        o.append(arrow(qx + qw, y + qh / 2, rx - 2, y + qh / 2, RULE))
        o.append(label(qx + qw + 18, y + qh / 2 - 6, "answer", 9.5, MUTE, "start"))
        if i < len(ys) - 1:
            o.append(label(qx + qw / 2, y + qh + 18, "if it can", 9.5, MUTE))

    o.append(label(30, H - 62,
                   "The four refusals are the point. A ranking is not an adequacy statement, and a "
                   "definite ranking is not evidence that it means anything:", 11, INK, "start"))
    o.append(label(30, H - 46,
                   "the three answers are computed separately, reported separately, and no code path "
                   "combines them into a single number.", 11, INK, "start"))
    o.append(label(30, H - 18,
                   "Source of truth: terratrace/decision.py (Pareto) · terratrace/adequacy.py "
                   "(the band) · terratrace/verdicts.py (the three answers, and the demotion rule).",
                   10.5, MUTE, "start"))
    return "\n".join(o) + "\n</svg>\n"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in (("pipeline.svg", pipeline()), ("decision-flow.svg", decision_flow())):
        (OUT_DIR / name).write_text(text, encoding="utf-8")
        print(f"wrote docs/figures/{name} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
