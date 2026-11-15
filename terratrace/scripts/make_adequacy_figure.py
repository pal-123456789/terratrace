#!/usr/bin/env python3
"""Draw the one figure that makes the project's central distinction visible, from the real artifact.

WHAT THIS IS FOR. Every judge-facing surface says, in prose, that a definite ranking is not an
adequacy result. Prose is a poor carrier for that idea: it takes a paragraph, and a reader who skims
comes away with "Nevada is the Moon analog", which is the opposite of what the panel found. This draws
it instead, in one look, from committed numbers and nothing else.

The picture is a comparison of two distances that a reader can check by eye:

  * the reference's distance FROM ITSELF -- the band its own held-out sub-windows span, which is the
    only yardstick the data can justify for "inside the reference's variability";
  * each candidate's distance TO the reference, on the same axis.

The result is that every Earth candidate sits INSIDE that band, and so do four of the five sibling
lunar sites, which are known to be different terrain. A yardstick that says "adequate" to terrain from
demonstrably different places has established nothing. That is the whole figure.

NO INVENTED DATA. Every number is read from ``artifacts/lunar_adequacy/lunar_adequacy.json``, which is
the committed record of the reanalysis, and the script prints what it drew so a reader can diff the
figure against the record rather than trust it. If the artifact is absent the script FAILS rather than
drawing an illustrative version -- a figure that can be mistaken for a result is worse than no figure.

LAYOUT NOTE. The two panels are drawn from ONE linear scale each, and the per-panel control count is
that panel's own. The two panels genuinely differ -- relief admits all five controls, slope four of
five -- and the binding "4 of 5" in the verdict card is the two-descriptor rule, which is why the card
says "on both descriptors" and the panel labels count per descriptor.

LAYOUT IS CHECKED, NOT EYEBALLED. ``est_px`` below estimates the rendered width of a string in
Helvetica/Arial, and every text run in the figure is wrapped or placed against it, so the figure
cannot silently grow a label off its own canvas. ``tests/test_adequacy_figure.py`` re-imports the same
estimator and asserts the invariant over the committed SVG, because the first version of this figure
shipped with a nearest-candidate label off the left edge, a band label under the verdict cards, and a
footer sentence wider than the canvas -- all three of which a human eye missed and a width check does
not.

MARKER HEIGHT IS NOT DATA. The reference's own band is up to six times the largest candidate distance,
so on the relief axis seven candidates land inside fourteen pixels. Markers are stacked vertically
only when two would otherwise collide, the way a dot plot is, and the figure says so in its own
subtitle. Moving a marker sideways or drawing it further from the axis would give it a dimension it
does not have.

USAGE
    python3 scripts/make_adequacy_figure.py            # writes docs/figures/adequacy-vs-ranking.svg
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # .../terratrace
ART = ROOT / "artifacts" / "lunar_adequacy" / "lunar_adequacy.json"
OUT = ROOT / "docs" / "figures" / "adequacy-vs-ranking.svg"

CELL = "Site01@500m"          # the cell the panel's own reading quotes
DESCRIPTORS = ("slope", "relief")

# palette: the repository's committed README figures are light-background, so this matches them
INK, MUTE, RULE = "#24292F", "#57606A", "#D0D7DE"
BAND, BAND_EDGE = "#FFF3D6", "#E0913F"      # the yardstick
EARTH, SIBLING = "#0B7A75", "#8250DF"       # candidates vs known-different controls
BG = "#FFFFFF"
FONT = "Helvetica,Arial,sans-serif"
MIDDOT = "·"                            # a literal, not an entity: esc() would escape an entity

# canvas geometry, shared with the test that checks the layout
W, H = 1120, 660
MARGIN = 30
PLOT_X0, PLOT_X1 = 236, 676          # the two panel plots
PANEL_TOP, PANEL_ROW_H = 160, 152
CARD_X, CARD_W = 706, 384
CARD_Y0, CARD_H, CARD_PITCH = 116, 140, 142
CARD_IND = 11.0                      # hanging indent for a wrapped card line

# Conservative per-character advance widths in em, for Helvetica/Arial and its metric clones. Not a
# font metric table: a cheap estimate that is close enough to place text and strict enough that a run
# it calls "fits" really does. The narrow/wide classes are what matter -- a sentence of lowercase
# ASCII sits near 0.54 em per character, while digits, caps and 'm' pull it up and punctuation and 'i'
# pull it down. Measured against a LibreOffice render of this figure (ink edge read off the raster,
# every text run in the file), it matches real width to within about 5 %: it over-estimates regular
# text by up to 3 % and under-estimates the one bold heading by 5 %, having no weight class. That is
# why every budget here leaves a margin rather than filling the canvas.
_W0_NARROW = set("iljtfr.,:;'\"|!()[]· ")
_W0_WIDE = set("MW@%#&m")


def est_px(text, size):
    """Estimated rendered width of ``text`` in pixels at ``size`` px Helvetica/Arial."""
    total = 0.0
    for ch in text:
        if ch in _W0_NARROW:
            total += 0.30
        elif ch in _W0_WIDE:
            total += 0.92
        elif ch.isdigit():
            total += 0.556
        elif ch.isupper():
            total += 0.70
        else:
            total += 0.54
    return total * size


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def nice(x):
    """A compact label for a distance, without inventing precision."""
    return f"{x:.3f}".rstrip("0").rstrip(".") if x < 1 else f"{x:.2f}".rstrip("0").rstrip(".")


def wrap_px(text, size, max_px):
    """Greedy word wrap to a PIXEL budget rather than a character count.

    A character budget is the wrong unit here: the same count of characters is a third wider at 13 px
    than at 10.5 px, which is how the footer of the first version came out wider than the canvas while
    looking, in the source, like the shortest line in the file.
    """
    words, line, out = text.split(), "", []
    for w in words:
        trial = (line + " " + w).strip()
        if line and est_px(trial, size) > max_px:
            out.append(line)
            line = w
        else:
            line = trial
    if line:
        out.append(line)
    return out


def beeswarm(xs, gap=6.0, step=7.0, levels=4):
    """Vertical offsets that separate markers whose x positions would otherwise collide.

    Two sibling lunar sites sit 3 px apart on the slope axis and three of the relief candidates sit
    within 2 px of each other, so the first version drew seven candidates as four dots and five
    controls as four -- pictures that contradicted their own captions. The x position IS the value, so
    it must not move; the collision is what moves. Offsets run outwards from the row's own axis, and
    the figure's subtitle says plainly that marker height carries no meaning, so the stack cannot be
    misread as a second variable.
    """
    offsets = [0.0]
    for i in range(1, levels + 1):
        offsets += [-i * step, i * step]
    taken = {o: [] for o in offsets}
    out = []
    for x in xs:
        for o in offsets:
            if all(abs(x - px) >= gap for px in taken[o]):
                taken[o].append(x)
                out.append(o)
                break
        else:                                   # more collisions than levels: keep the true x
            taken[0.0].append(x)
            out.append(0.0)
    return out


def load():
    if not ART.exists():
        sys.exit(f"error: {ART} is missing. This figure is drawn from the committed record; it is "
                 f"not an illustration, so it will not be drawn from anything else.")
    a = json.loads(ART.read_text(encoding="utf-8"))
    if CELL not in a.get("cells", {}):
        sys.exit(f"error: cell {CELL!r} is not in the record; refusing to draw a partial figure")
    c = a["cells"][CELL]
    ad = c["adequacy_detail"]
    verdict = c["verdict"]
    d = {"cell": c, "summary": a["summary"]}
    for name in DESCRIPTORS:
        if name not in ad["per_descriptor"]:
            sys.exit(f"error: descriptor {name!r} is not in the record")
        pd = ad["per_descriptor"][name]
        d[name] = {
            "band_median": float(pd["band"]["median"]),
            "band_p95": float(pd["band"]["p95"]),
            "candidates": {k: float(v["distance"]) for k, v in pd["candidates"].items()},
        }
    disc = verdict["absolute_adequacy"]["discrimination"]
    # the controls are quoted per descriptor, so each panel is drawn from its own column
    d["controls"] = {"slope": [float(x["slope"]) for x in disc["control_distances"]],
                     "relief": [float(x["relief"]) for x in disc["control_distances"]]}
    d["admitted"], d["n_controls"] = int(disc["admitted"]), int(disc["controls"])
    d["rank_state"] = verdict["relative_ranking"]["state"]
    d["rank_winner"] = verdict["relative_ranking"]["recommended_unit"]
    d["adequacy_state"] = verdict["absolute_adequacy"]["state"]
    d["sufficiency"] = verdict["evidence_sufficiency"]
    # How many cells can calibrate BOTH bands. This is not decoration: the relief band exists at only
    # some supports, and a reader shown two filled panels is owed the fact that twelve of the eighteen
    # cells have no relief band at all -- where the verdict rests on slope alone, which is a different
    # statement from "the band is wide". Drawing one of the six cells that do have both, without saying
    # so, would over-generalise the picture.
    d["n_cells"] = len(a["cells"])
    d["cells_both_bands"] = sum(
        1 for c in a["cells"].values()
        if all(bool(p["established"]) for p in c["adequacy_detail"]["per_descriptor"].values()))
    # the least permissive admission count anywhere, so the figure can state a floor rather than one
    # cell's number dressed up as the panel's
    d["least_admitted"] = min(int(c["verdict"]["absolute_adequacy"]["discrimination"]["admitted"])
                              for c in a["cells"].values())
    return d


def _text(x, y, s, size, fill, *, weight=None, anchor=None, spacing=None):
    attrs = [f'x="{x:.1f}"' if isinstance(x, float) else f'x="{x}"', f'y="{y:.1f}"',
             f'font-family="{FONT}"', f'font-size="{size:g}"', f'fill="{fill}"']
    if weight:
        attrs.append(f'font-weight="{weight}"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if spacing:
        attrs.append(f'letter-spacing="{spacing}"')
    return f'<text {" ".join(attrs)}>{esc(s)}</text>'


def _card_lines(paras):
    """Wrap a card's explanation into ``(indent_px, text)`` lines.

    A reason that carries two clauses ("... is made; fewer than 30") is broken at the semicolon.
    Reporting the record's reason strings verbatim is deliberate -- the figure must not paraphrase
    what it is reporting -- but wrapping one mid-clause put "fewer" at the end of a line and its
    threshold alone on the next, which reads as a broken sentence rather than as the terse record
    entry it is.
    """
    lines = []
    for para in paras:
        for frag in (re.split(r";\s+", para) if len(paras) > 1 else [para]):
            for j, ln in enumerate(wrap_px(frag, 10.5, CARD_W - 30 - CARD_IND)):
                lines.append((0.0, f"{MIDDOT} {ln}") if j == 0 else (CARD_IND, ln))
    return lines


def build(d):
    o = []

    def add(s):
        o.append(s)

    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="A definite ranking is not an adequacy result: every Earth candidate '
        f'is closer to the lunar reference than the reference is to itself, and so are four of five '
        f'sibling lunar sites that are known to be different terrain. Drawn at one of the '
        f'{d["cells_both_bands"]} of {d["n_cells"]} cells where both descriptor bands can be '
        f'calibrated.">')
    add(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    # ---------------------------------------------------------------- title block
    add(_text(MARGIN, 38, "A definite ranking is not an adequacy result", 20, INK, weight=700))
    head_lines = [
        (f'Moon {d["cell"]["site_name"]} {MIDDOT} real NASA Goddard LOLA 5 m/px {MIDDOT} '
         f'9 km footprint {MIDDOT} {int(d["cell"]["support_m"])} m support {MIDDOT} against the same '
         f'7 Earth candidates and 5 sibling lunar sites', 12.5),
        # the census: without these two lines the figure generalises from one cell to the panel
        (f'one of the {d["n_cells"]} site x support cells the panel answers at, and one of the only '
         f'{d["cells_both_bands"]} where both descriptor bands can be calibrated', 11),
        (f'at the other {d["n_cells"] - d["cells_both_bands"]} the relief band cannot be built at all '
         f'{MIDDOT} the verdict there rests on the slope band alone', 11),
        ('all distances in units of the reference’s own spread on that descriptor', 12.5),
        ('marker height carries no meaning — markers are stacked only where two sites would land on '
         'top of each other', 11),
    ]
    y = 62
    for text, size in head_lines:
        for ln in wrap_px(text, size, W - 2 * MARGIN)[:2]:
            add(_text(MARGIN, y, ln, size, MUTE))
            y += 16

    # ---------------------------------------------------------------- the two panels
    for row, name in enumerate(DESCRIPTORS):
        v = d[name]
        band, cand = v["band_p95"], v["candidates"]
        ctrls = d["controls"][name]
        vmax = max([band] + list(cand.values()) + ctrls) * 1.12
        top = PANEL_TOP + row * PANEL_ROW_H
        axis_y = top + 48

        def X(val):
            return PLOT_X0 + (val / vmax) * (PLOT_X1 - PLOT_X0)

        add(_text(MARGIN, top + 8, name, 13, INK, weight=700))
        add(_text(MARGIN, top + 26, "distance from the reference", 11, MUTE))
        # the yardstick
        add(f'<rect x="{X(0):.1f}" y="{axis_y - 26:.1f}" width="{X(band) - X(0):.1f}" height="52" '
            f'fill="{BAND}"/>')
        add(f'<line x1="{X(band):.1f}" y1="{axis_y - 32:.1f}" x2="{X(band):.1f}" '
            f'y2="{axis_y + 32:.1f}" stroke="{BAND_EDGE}" stroke-width="1.6"/>')
        # the band edge label sits INSIDE the plot, right-aligned to the edge, so it cannot reach the
        # verdict column; the first version let it run into the cards
        add(_text(X(band) - 7, axis_y - 30, f'band edge {MIDDOT} p95 = {nice(band)}', 11, BAND_EDGE,
                  anchor="end"))
        add(f'<line x1="{X(0):.1f}" y1="{axis_y:.1f}" x2="{X(vmax):.1f}" y2="{axis_y:.1f}" '
            f'stroke="{RULE}" stroke-width="1"/>')

        # sibling lunar sites: above the axis -- the controls that decide the verdict
        add(_text(PLOT_X0, axis_y - 62, f'sibling lunar sites {MIDDOT} known-different terrain', 11,
                  SIBLING))
        add(_text(PLOT_X1, axis_y - 62,
                  f'{sum(1 for x in ctrls if x <= band)} of {d["n_controls"]} inside', 11, SIBLING,
                  anchor="end"))
        for val, dy in zip(sorted(ctrls), beeswarm(sorted(X(x) for x in ctrls))):
            add(f'<circle cx="{X(val):.1f}" cy="{axis_y - 40 + dy:.1f}" r="3.6" fill="none" '
                f'stroke="{SIBLING}" stroke-width="1.5" opacity="{1.0 if val <= band else 0.4:.2f}"/>')

        # Earth candidates: below the axis, one dot each
        ordered = sorted(cand.items(), key=lambda kv: kv[1])
        xs = [X(val) for _, val in ordered]
        win_xy = None
        for (cname, val), x, dy in zip(ordered, xs, beeswarm(xs)):
            is_winner = cname == d["rank_winner"]
            y = axis_y + 28 + dy
            if is_winner:
                win_xy = (x, y)
            add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.6 if is_winner else 3.6:.1f}" '
                f'fill="{EARTH}" opacity="{1.0 if is_winner else 0.72:.2f}"/>')
        if win_xy:
            label = (f'{d["rank_winner"].replace("earth_", "").replace("_", " ")} {MIDDOT} nearest '
                     f'Earth candidate ({nice(cand[d["rank_winner"]])})')
            # The label sits under its own marker, clamped to the CANVAS rather than to the plot: a
            # leader line drawn across the panel is not a decoration, it is a line through the other
            # candidates' markers. Clamping to the plot (the first version) forced exactly that for no
            # reason -- the winner is the leftmost candidate and its label still has room to the left.
            half = est_px(label, 11.5) / 2
            lx = min(max(win_xy[0], half + 4), W - half - 4)
            if abs(lx - win_xy[0]) > 3:
                add(f'<line x1="{lx:.1f}" y1="{axis_y + 42:.1f}" x2="{win_xy[0]:.1f}" '
                    f'y2="{win_xy[1] + 6:.1f}" stroke="{EARTH}" stroke-width=".8" opacity=".5"/>')
            add(_text(lx, axis_y + 52, label, 11.5, EARTH, weight=700, anchor="middle"))
        add(_text(PLOT_X0, axis_y + 66, f'Earth candidates {MIDDOT} all {len(cand)} inside the band',
                  11, EARTH))

    # ---------------------------------------------------------------- the three answers
    answers = [
        ("RANKING", "DEFINITE",
         f"{d['summary']['ranking_definite']} of {d['summary']['n_cells']} site x support cells",
         [f"{d['rank_winner'].replace('earth_', '').replace('_', ' ')} is the only non-dominated "
          f"Earth candidate. A ranking, within the roster tested."], EARTH),
        ("ADEQUACY", "NOT ESTABLISHED",
         f"{d['summary']['adequacy_not_established']} of {d['summary']['n_cells']} site x support cells",
         [f"The band admits {d['admitted']} of {d['n_controls']} sites known to be different terrain on "
          f"both descriptors at this cell, and at least {d['least_admitted']} of {d['n_controls']} at "
          f"every one of the {d['cells_both_bands']} cells where both bands exist, so membership in it "
          f"is not evidence of similarity."], BAND_EDGE),
        ("SUFFICIENCY", d["sufficiency"]["state"],
         f"{d['sufficiency']['n_candidates']} candidates {MIDDOT} {d['sufficiency']['n_supports']} "
         f"supports {MIDDOT} effective rank {d['sufficiency']['effective_rank']}",
         [str(r) for r in d["sufficiency"]["reasons"]], SIBLING),
    ]
    y = CARD_Y0
    for label, state, tally, paras, col in answers:
        add(f'<rect x="{CARD_X}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="6" fill="none" '
            f'stroke="{RULE}" stroke-width="1"/>')
        add(_text(CARD_X + 15, y + 23, label, 10.5, MUTE, spacing=1.4))
        add(_text(CARD_X + 15, y + 47, state, 15, col, weight=700))
        add(_text(CARD_X + 15, y + 66, tally, 11, MUTE))
        for i, (ind, ln) in enumerate(_card_lines(paras)[:5]):
            add(_text(CARD_X + 15 + ind, y + 84 + i * 12, ln, 10.5, MUTE))
        y += CARD_PITCH

    # ---------------------------------------------------------------- the one line that matters
    add(f'<line x1="{MARGIN}" y1="{H - 84}" x2="{W - MARGIN}" y2="{H - 84}" stroke="{RULE}" '
        f'stroke-width="1"/>')
    claim = (f'Every Earth candidate is closer to the Moon than the Moon is to itself {MIDDOT} and '
             f'so are {d["admitted"]} of the {d["n_controls"]} lunar sites that a lunar geologist '
             f'would call different terrain.')
    big = wrap_px(claim, 13, W - 2 * MARGIN)[:2]
    for i, ln in enumerate(big):
        add(_text(MARGIN, H - 58 + i * 18, ln, 13, INK))
    sub = ('That is why the engine answers the ranking and the adequacy questions separately, and '
           'publishes nothing that turns the first into the second. Source: '
           'artifacts/lunar_adequacy/lunar_adequacy.json (exploratory reanalysis).')
    top = H - 58 + len(big) * 18 + 6
    for i, ln in enumerate(wrap_px(sub, 11.5, W - 2 * MARGIN)[:2]):
        add(_text(MARGIN, top + i * 16, ln, 11.5, MUTE))
    add('</svg>')
    return "\n".join(o) + "\n"


def main():
    d = load()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    svg = build(d)
    OUT.write_text(svg, encoding="utf-8")
    # print what was drawn, so the figure can be diffed against the record instead of trusted
    for name in DESCRIPTORS:
        v = d[name]
        ctrls = d["controls"][name]
        print(f"[{name}] band p95 {v['band_p95']:.4f} (median {v['band_median']:.4f}); "
              f"{len(v['candidates'])} candidates, max {max(v['candidates'].values()):.4f}; "
              f"controls inside {sum(1 for x in ctrls if x <= v['band_p95'])} of {d['n_controls']}")
    print(f"[verdict] ranking {d['rank_state']} ({d['rank_winner']}); "
          f"adequacy {d['adequacy_state']}; sufficiency {d['sufficiency']['state']}")
    print(f"[census] both bands calibrated at {d['cells_both_bands']} of {d['n_cells']} cells; "
          f"relief band absent at {d['n_cells'] - d['cells_both_bands']}")
    for r in d["sufficiency"]["reasons"]:
        print(f"[reason] {r}")
    print(f"wrote {OUT.relative_to(ROOT.parent)} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
