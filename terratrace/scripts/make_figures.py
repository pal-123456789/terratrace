#!/usr/bin/env python3
"""Generate the README figures as deterministic SVG (no browser, no external assets).

The master plan requires the README's first screen to carry "a distinctive screenshot showing
morphology + gap ledger", and module 18 lists "screenshots" in the release package. Screenshots of
a live site age; these figures are generated from the same numbers the study reports, so they can be
regenerated and cannot drift.

Every number below is traceable:
  * candidate 60 km sigma  -- `config/matched_footprint_v3.yml` (comment block, measured from the
    public ESA Copernicus GLO-30 COG mosaic) and `docs/RESULTS-v3.md` §3-4.
  * Mars reference sigma   -- `docs/RESULTS-v3.md` §4.
  * result states          -- `terratrace/decision.py`.

Run:  python scripts/make_figures.py
"""
from __future__ import annotations

import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                       # .../terratrace
OUT = ROOT / "docs" / "figures"

# --- data (see module docstring for provenance) ------------------------------------
# id, 60 km sigma (m), class as assigned before the run
CANDIDATES = [
    ("nullarbor", 5, "smooth_control"),
    ("llano_estacado", 14, "smooth_control"),
    ("deccan_traps", 32, "basaltic"),
    ("snake_river_plain", 95, "basaltic"),
    ("harrat_khaybar", 102, "basaltic"),
    ("odadahraun", 182, "basaltic"),
    ("nevada_basin", 562, "other"),
]
# the two confirmatory references that carry S, and the two that carry the V contrast
REFERENCES = [("mars_arcadia", 7), ("mars_cerberus", 5), ("mars_terra_sabaea", 148), ("mars_terra_sirenum", 256)]

CLS_COLOUR = {"smooth_control": "#1A7F37", "basaltic": "#0E7490", "other": "#6E56CF"}
BG, INK, MUT, LINE = "#ffffff", "#24292F", "#57606A", "#D0D7DE"

_log = math.log10
LO, HI = _log(5), _log(562)


def _w(sigma: float) -> float:
    """bar width, %, on a log scale with an 8 % floor so nothing looks empty"""
    return 8 + 92 * (_log(sigma) - LO) / (HI - LO)


def roughness_ladder() -> str:
    W, row_h, top = 860, 30, 96
    H = top + row_h * len(CANDIDATES) + 104
    L, NAME_W, BAR_W, VAL_W = 28, 168, 470, 150
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="Sixty-kilometre roughness of the seven Earth candidates, log scale, '
        f'coloured by pre-run class. The two smoothest are the non-volcanic controls, which carry the '
        f'supported hypothesis S.">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<text x="{L}" y="34" font-family="Helvetica,Arial,sans-serif" font-size="19" font-weight="700" '
        f'fill="{INK}">The nearest Earth analog tracks roughness, not volcanic origin</text>',
        f'<text x="{L}" y="58" font-family="Helvetica,Arial,sans-serif" font-size="12.5" fill="{MUT}">'
        f'60 km elevation sigma per candidate (log scale) · class is the literature label assigned '
        f'before the run</text>',
    ]
    # reference markers as vertical dotted guides (labelled once, in the legend, so they
    # cannot collide — arcadia and cerberus are only 2 m apart on a log axis)
    for _name, sig in REFERENCES:
        x = L + NAME_W + BAR_W * _w(sig) / 100.0
        p.append(f'<line x1="{x:.1f}" y1="{top - 10}" x2="{x:.1f}" y2="{top + row_h * len(CANDIDATES) - 6}" '
                 f'stroke="{MUT}" stroke-width="1" stroke-dasharray="2 4" opacity=".55"/>')
    for i, (name, sig, cls) in enumerate(CANDIDATES):
        y = top + i * row_h
        p.append(f'<text x="{L + NAME_W - 12}" y="{y + 18}" font-family="ui-monospace,Menlo,Consolas,monospace" '
                 f'font-size="13" fill="{INK}" text-anchor="end">{name}</text>')
        p.append(f'<rect x="{L + NAME_W}" y="{y + 6}" width="{BAR_W}" height="15" fill="#F6F8FA" '
                 f'stroke="{LINE}"/>')
        p.append(f'<rect x="{L + NAME_W}" y="{y + 6}" width="{BAR_W * _w(sig) / 100.0:.1f}" height="15" '
                 f'fill="{CLS_COLOUR[cls]}"/>')
        p.append(f'<text x="{L + NAME_W + BAR_W + 14}" y="{y + 18}" font-family="ui-monospace,Menlo,Consolas,'
                 f'monospace" font-size="12.5" fill="{MUT}">σ {sig} m</text>')
    ly = top + row_h * len(CANDIDATES) + 26
    for j, (lbl, cls) in enumerate([("smooth control · non-volcanic", "smooth_control"),
                                    ("basaltic (pre-run label)", "basaltic"), ("other", "other")]):
        x = L + j * 230
        p.append(f'<rect x="{x}" y="{ly - 9}" width="11" height="11" rx="2" fill="{CLS_COLOUR[cls]}"/>')
        p.append(f'<text x="{x + 18}" y="{ly}" font-family="Helvetica,Arial,sans-serif" font-size="11.5" '
                 f'fill="{MUT}">{lbl}</text>')
    p.append(f'<line x1="{L}" y1="{ly + 20}" x2="{L + 26}" y2="{ly + 20}" stroke="{MUT}" stroke-width="1" '
             f'stroke-dasharray="2 4" opacity=".55"/>')
    p.append(f'<text x="{L + 34}" y="{ly + 24}" font-family="Helvetica,Arial,sans-serif" font-size="11.5" '
             f'fill="{MUT}">dotted guides: Mars references — arcadia σ 7 m, cerberus σ 5 m, '
             f'terra_sabaea σ 148 m, terra_sirenum σ 256 m</text>')
    p.append(f'<text x="{L}" y="{ly + 52}" font-family="Helvetica,Arial,sans-serif" font-size="12" '
             f'fill="{MUT}">The two references that support S — Arcadia (σ 7 m) and Cerberus '
             f'(σ 5 m) — sit where the two non-volcanic controls sit. The basalts win only '
             f'where the target is rough.</text>')
    p.append("</svg>")
    return "\n".join(p) + "\n"


def decision_states() -> str:
    """The refusal mechanism — the plan's stated differentiator."""
    states = [
        ("RECOMMEND", "#1A7F37", "one unit is Pareto non-dominated and stable"),
        ("TIE", "#BF8700", "evidence does not separate the candidates"),
        ("NOT COMPARABLE", "#8250DF", "supports or footprints are not matched"),
        ("BLOCKED", "#CF222E", "data, rights or constraint status incomplete"),
    ]
    W, row_h, top = 860, 46, 92
    H = top + row_h * len(states) + 40
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="TerraTrace emits one of four states; a tie, a not-comparable or a '
        f'blocked result is a first-class outcome, not a failure.">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<text x="28" y="34" font-family="Helvetica,Arial,sans-serif" font-size="19" font-weight="700" '
        f'fill="{INK}">Four honest outcomes — never one opaque score</text>',
        f'<text x="28" y="58" font-family="Helvetica,Arial,sans-serif" font-size="12.5" fill="{MUT}">'
        f'The engine emits exactly one of these; abstention is a result, not an error.</text>',
    ]
    for i, (name, col, desc) in enumerate(states):
        y = top + i * row_h
        p.append(f'<rect x="28" y="{y}" width="200" height="32" rx="16" fill="{col}"/>')
        p.append(f'<text x="128" y="{y + 21}" font-family="ui-monospace,Menlo,Consolas,monospace" '
                 f'font-size="13" font-weight="700" fill="#ffffff" text-anchor="middle">{name}</text>')
        p.append(f'<text x="248" y="{y + 21}" font-family="Helvetica,Arial,sans-serif" font-size="13" '
                 f'fill="{MUT}">{desc}</text>')
    p.append("</svg>")
    return "\n".join(p) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "roughness-ladder.svg").write_text(roughness_ladder(), encoding="utf-8")
    (OUT / "decision-states.svg").write_text(decision_states(), encoding="utf-8")
    for f in sorted(OUT.glob("*.svg")):
        print(f"wrote {f.relative_to(ROOT)} ({f.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
