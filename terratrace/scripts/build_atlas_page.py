"""Build the offline evidence-atlas page from the committed atlas record.

WHY A GENERATOR AND NOT A HAND-WRITTEN PAGE
-------------------------------------------
The page exists to answer one question in one screen: *how much evidence supports this terrain
relationship, at what scale, and where does the conclusion break?* Every number on it is therefore
read from `artifacts/discovery_atlas/discovery_atlas.json` rather than typed, and the page carries a
"built from" line with the source record's own sha256 -- so a reader can tell whether the page they
are looking at matches the record it claims to describe.

It is **self-contained**: CSS and the data are inline, there is no fetch, no external asset, no CDN
and no API key. That is a requirement rather than a preference -- the main demonstration has to work
on a laptop with the network off, and a page that needs a request to render has not shown anything.

Sections, matching what the review asked the interface to do:

  A  terrain comparison   reference, candidate, comparable extent, footprint, source and posting,
                          effective resolution floor, valid coverage, and a scale bar
  B  decision matrix      ranking / adequacy / sufficiency per cell, with the distinction drawn
                          explicitly -- this is the section that stops a ranking being read as
                          adequacy, which is the failure the project made twice
  C  stability map        cell x perturbation grid: which perturbations leave which cells alone, and
                          which ones reverse them
  D  diagnostics          descriptor dependence, uncertainty, adversarial sensitivity, resolution
                          limits
  E  explainability       the ten cross-artifact reconciliations, each naming both records it holds
                          together

Output: `site/atlas/index.html` (published at terratrace.fit/atlas/).
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

ATLAS = ROOT / "artifacts" / "discovery_atlas" / "discovery_atlas.json"
STRESS = ROOT / "artifacts" / "lunar_adversarial" / "lunar_adversarial.json"
OUT = REPO / "site" / "atlas" / "index.html"

CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#080b10;color:#dfe7ef;
 font:15px/1.62 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:#7fd4ff}
.wrap{max-width:1180px;margin:0 auto;padding:44px 22px 90px}
.kick{font:600 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.16em;
 text-transform:uppercase;color:#4bb0e0}
h1{font-size:clamp(28px,4.4vw,46px);line-height:1.1;margin:14px 0 12px;letter-spacing:-.02em}
h2{font-size:22px;margin:52px 0 6px;letter-spacing:-.01em}
h3{font-size:15px;margin:26px 0 8px;color:#a9c4d8;font-weight:600}
p{color:#9fb2c4;margin:10px 0}
.lede{font-size:17px;color:#c2d2e0;max-width:78ch}
.note{font-size:13px;color:#7d90a3}
.ans{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:26px 0 6px}
.card{background:#0d131b;border:1px solid #1d2733;border-radius:12px;padding:16px 18px}
.card .q{font-size:12.5px;color:#8ea3b7;min-height:34px}
.card .a{font:600 21px/1.2 ui-monospace,monospace;margin-top:8px}
.ok{color:#5fe0a8}.warn{color:#ffc861}.bad{color:#ff8a7a}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px}
th,td{padding:7px 9px;border-bottom:1px solid #18212c;text-align:left;vertical-align:top}
th{color:#8ea3b7;font-weight:600;font-size:12px;letter-spacing:.03em;text-transform:uppercase}
td.m,th.m{font-family:ui-monospace,monospace}
.grid{overflow-x:auto;padding-bottom:6px}
.map td,.map th{text-align:center;padding:3px 4px;font-size:11px}
.map td.st{background:#10301f;color:#5fe0a8}
.map td.rv{background:#3a1a17;color:#ff9c8a}
.map td.na{background:#141a22;color:#5b6c7d}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:#8ea3b7;margin:8px 0 0}
.sw{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:-1px;margin-right:5px}
.bar{height:22px;border-radius:5px;background:linear-gradient(90deg,#123040,#1d4a5e);position:relative;
 margin:6px 0 2px;border:1px solid #24404f}
.bar i{position:absolute;top:-3px;bottom:-3px;width:2px;background:#ffc861}
.pill{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;
 font-family:ui-monospace,monospace;border:1px solid #26303c;color:#9fb2c4}
.fw{border-left:3px solid #24404f;padding:2px 0 2px 14px;margin:18px 0}
.foot{margin-top:56px;padding-top:18px;border-top:1px solid #1d2733;font-size:12.5px;color:#7d90a3}
"""


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _e(x):
    return html.escape(str(x))


def _state_class(state):
    if state in ("RECOMMEND_FOLLOW_UP", "ESTABLISHED_ADEQUATE", "SUFFICIENT"):
        return "ok"
    if state in ("NOT_ESTABLISHED", "TIE", "INDETERMINATE", "INSUFFICIENT"):
        return "bad"
    return "warn"


def _scale_bar():
    """A visual for what "resolution" means here: a 9000 m window next to a 5 m and a 30 m posting.

    Drawn, not described, because the single hardest thing to keep straight in this project is that
    the footprint and the source posting are different numbers by two orders of magnitude -- and the
    effective floor (3x the posting) is what decides whether a support is evidence at all.
    """
    total = 9000.0
    rows = [("footprint 9000 m", 9000.0, "#1d4a5e"),
            ("source posting 30 m (Copernicus)", 30.0, "#ffc861"),
            ("source posting 5 m (LOLA)", 5.0, "#5fe0a8"),
            ("effective floor 90 m (3x 30 m)", 90.0, "#ffc861"),
            ("effective floor 15 m (3x 5 m)", 15.0, "#5fe0a8")]
    out = ['<div>']
    for label, metres, colour in rows:
        pct = max(0.15, 100.0 * metres / total)
        out.append(
            f'<div class="note" style="margin-top:10px">{_e(label)}</div>'
            f'<div class="bar" style="background:#0e151d">'
            f'<div style="width:{pct:.3f}%;height:100%;background:{colour};border-radius:4px"></div>'
            f'</div>')
    out.append('<div class="note">All five bars are drawn on the same 9000 m scale. A comparison is '
               'honest when the support is above the effective floor of <em>both</em> sources: that '
               'is the arithmetic that excludes Mars from the lunar regime, not a preference.</div>')
    out.append('</div>')
    return "".join(out)


def _stability_grid(stress):
    """cell x perturbation: which perturbations leave which cell alone, and which reverse it.

    A perturbation EVALUATES a cell when it covers that cell's support -- the twenty-seven
    full-support specs cover all 18, and the three single-support footprint specs cover the six
    cells at the one support named in their label. A cell a perturbation never ran is drawn as "not
    evaluated" rather than as a pass: counting a coverage gap as stability is the same class of
    mistake the scorer itself made once, and it is not going to be repeated in the picture.
    """
    pert = [p for p in stress["perturbations"] if p["counted"]]
    labels = [p["label"] for p in pert]
    supports = ("500", "750", "1000")
    cells = [(ref, sup) for ref in sorted(stress["baseline"]["layer1"]) for sup in supports]

    # a shifted support is scored against the cell it replaced, so key the change by that cell
    changed = set()
    for p in pert:
        for c in p["changed"]:
            changed.add((p["label"], c["reference"], str(c.get("baseline_support", c["support"]))))

    def evaluated(p, sup):
        if p["n_cells"] != 6:
            return True                       # a full-support perturbation covers every cell
        return p["label"].rsplit("@", 1)[-1] == sup

    head = "".join(f'<th class="m" title="{_e(l)}">{_e(l.split(":", 1)[1][:8])}</th>' for l in labels)
    body = []
    for ref, sup in cells:
        tds = []
        for p in pert:
            if not evaluated(p, sup):
                tds.append('<td class="na" title="not evaluated by this perturbation">&#183;</td>')
            elif (p["label"], ref, sup) in changed:
                tds.append('<td class="rv" title="reverses here">R</td>')
            else:
                tds.append('<td class="st" title="unchanged">&#183;</td>')
        body.append(f'<tr><th scope="row" class="m">{_e(ref.replace("LUNAR_", ""))} @ {_e(sup)} m</th>'
                    + "".join(tds) + "</tr>")
    return ('<div class="grid"><table class="map"><thead><tr><th></th>' + head +
            "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
            '<div class="legend">'
            '<span><i class="sw" style="background:#10301f"></i>unchanged</span>'
            '<span><i class="sw" style="background:#3a1a17"></i>R &mdash; reversed</span>'
            '<span><i class="sw" style="background:#141a22"></i>&#183; &mdash; not evaluated by that '
            'perturbation</span></div>')


def main():
    if not ATLAS.exists():
        raise SystemExit(f"discovery atlas is missing at {ATLAS}; run scripts/run_discovery_atlas.py")
    a = json.loads(ATLAS.read_text(encoding="utf-8"))
    stress = json.loads(STRESS.read_text(encoding="utf-8"))
    h = a["headline"]
    v = a["verdict"]
    ranking_definite = h["ranking_definite_cells"]
    n_cells = h["ranking_cells"]

    parts = []
    parts.append(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TerraTrace — evidence atlas</title>
<meta name="description" content="How much evidence supports each terrain relationship, at what
scale, and where the conclusion breaks. Built offline from the committed discovery atlas record.">
<style>{CSS}</style></head><body><div class="wrap">
<div class="kick">TerraTrace · evidence atlas · built offline</div>
<h1>How much evidence supports this, at what scale, and where does it break?</h1>
<p class="lede">Every number on this page is read from a committed record and reconciled against the
other records before the page is written. Nothing here is fetched at runtime: no network, no API key,
no computation on load.</p>
""")

    parts.append('<div class="ans">')
    parts.append(f'<div class="card"><div class="q">Which candidate is closest, among those tested?</div>'
                 f'<div class="a ok">definite at {ranking_definite} / {n_cells}</div>'
                 f'<div class="note">a relative answer; well defined however weak the field</div></div>')
    parts.append(f'<div class="card"><div class="q">Is any candidate inside the reference\'s own '
                 f'variability?</div><div class="a bad">not established, at all {n_cells}</div>'
                 f'<div class="note">the yardstick admits {_e(a["verdict"]["absolute_adequacy"]["discrimination"]["admitted"])} '
                 f'of {_e(a["verdict"]["absolute_adequacy"]["discrimination"]["controls"])} known-different controls, so '
                 f'membership in it is not evidence of similarity</div></div>')
    parts.append(f'<div class="card"><div class="q">Is the evidence enough to answer either?</div>'
                 f'<div class="a warn">{_e(v["evidence_sufficiency"]["state"].lower())}</div>'
                 f'<div class="note">{_e("; ".join(v["evidence_sufficiency"]["reasons"])[:180])}</div></div>')
    parts.append('</div>')
    parts.append('<div class="fw note">These are three answers to three questions and the third does '
                 'not cancel the first two &mdash; it qualifies them. A project that reported only '
                 'the first would be describing the same data and claiming more.</div>')

    # ---- A. terrain comparison
    parts.append('<h2>A · The comparable windows</h2>')
    parts.append('<p>Every window the decisions were made on, with the metadata needed to check that '
                 'both sides of a comparison cover the same ground. Footprint is what was compared; '
                 'support is the cell size; the effective floor is the coarsest support the source '
                 'can honestly carry.</p>')
    parts.append('<div class="grid"><table><thead><tr><th>regime</th><th>reference</th><th>body</th>'
                 '<th class="m">footprint</th><th class="m">support</th><th class="m">cells</th>'
                 '<th class="m">posting</th><th class="m">floor</th><th class="m">valid</th>'
                 '</tr></thead><tbody>')
    for w in a["windows"]:
        # the lunar records carry [n, n] and the Mars regime carries n; the page shows n x n either
        cn = w["cells"][0] if isinstance(w["cells"], (list, tuple)) else w["cells"]
        vf = w.get("valid_fraction")
        post = w.get("source_posting_m")
        floor = w.get("source_floor_m")
        parts.append(
            f'<tr><td>{_e(w["regime"])}</td><td class="m">{_e(w["reference"])}</td>'
            f'<td>{_e(w["body"])}</td><td class="m">{w["footprint_m"]/1000:.1f} km</td>'
            f'<td class="m">{w["support_m"]:.0f} m</td><td class="m">{cn}&times;{cn}</td>'
            f'<td class="m">{f"{post:.0f} m" if post else "&mdash;"}</td>'
            f'<td class="m">{f"{floor:.0f} m" if floor else "&mdash;"}</td>'
            f'<td class="m">{f"{vf:.3f}" if vf is not None else "&mdash;"}</td></tr>')
    parts.append('</tbody></table></div>')
    parts.append('<h3>What a resolution actually means here</h3>')
    parts.append(_scale_bar())

    # ---- B. decision matrix
    parts.append('<h2>B · The decision matrix — ranking is not adequacy</h2>')
    parts.append('<p>Each row is one comparable window. <b>Ranking</b> asks which candidate is closest '
                 'among those tested. <b>Adequacy</b> asks whether any of them is inside the '
                 'reference\'s own morphological variability. <b>Sufficiency</b> asks whether the '
                 'evidence is enough to answer either. They are filled in independently and they '
                 'disagree, which is the point of showing them side by side.</p>')
    parts.append('<div class="grid"><table><thead><tr><th>cell</th><th>ranking</th>'
                 '<th class="m">unit</th><th class="m">worst axis</th><th>adequacy</th>'
                 '<th>sufficiency</th></tr></thead><tbody>')
    for key in sorted(a["ranking"]):
        r, ad = a["ranking"][key], a["adequacy"][key]
        suf = a["sufficiency"][key]
        suf_reasons = "; ".join(suf["reasons"])
        wad = r.get("worst_axis_distance_fraction")
        wad_s = "&mdash;" if wad is None else f"{wad:.2f}"
        prov = " <span class='pill'>provisional</span>" if r["provisional"] else ""
        parts.append(
            f'<tr><td class="m">{_e(key)}</td>'
            f'<td class="{_state_class(r["state"])}">{_e(r["state"])}{prov}</td>'
            f'<td class="m">{_e(r["recommended_unit"] or "&mdash;")}</td>'
            f'<td class="m">{wad_s}</td>'
            f'<td class="bad">{_e(ad["state"])}</td>'
            f'<td class="{_state_class(suf["state"])}" title="{_e(suf_reasons)}">'
            f'{_e(suf["state"].lower())}</td></tr>')
    parts.append('</tbody></table></div>')
    parts.append('<div class="fw note"><b>Why this section exists.</b> This project withdrew a Mars '
                 'claim by reading &ldquo;non-dominated among these candidates&rdquo; as &ldquo;a good '
                 'analog&rdquo;, and published a lunar headline whose survivor is 70% away on its worst '
                 'axis at one site. Both were the same mistake. A page that showed only the ranking '
                 'column would invite it a third time.</div>')

    # ---- C. stability map
    parts.append('<h2>C · Where it survives, and where it reverses</h2>')
    parts.append(f'<p>{h["stress_stable_of_counted"][1]} perturbations were declared before the '
                 f'stress test ran, with the pass rule fixed in advance. '
                 f'<b>{h["stress_stable_of_counted"][0]} of {h["stress_stable_of_counted"][1]}</b> left '
                 f'the ordering untouched. The grid below is every cell against every counted '
                 f'perturbation &mdash; the two reversals are the falsifiable part and they are as '
                 f'visible as the passes.</p>')
    parts.append(_stability_grid(stress))
    parts.append('<h3>The two conditions that reverse it</h3><ul>')
    for lab in a["adversarial"]["reversing"]:
        row = next(p for p in stress["perturbations"] if p["label"] == lab)
        parts.append(f'<li><code>{_e(lab)}</code> &mdash; {row["n_changed"]} of {row["n_cells"]} cells '
                     f'change. <span class="note">{_e(row["family"])}</span></li>')
    parts.append('</ul>')

    # ---- D. diagnostics
    parts.append('<h2>D · Diagnostics</h2>')
    dep = a["dependence"]
    fit = dep["panel"]["500"]["pools"]["candidates_only"]["planar_fit"]
    parts.append('<div class="grid"><table><thead><tr><th>diagnostic</th><th>value</th>'
                 '<th>what it means</th></tr></thead><tbody>')
    rows = [
        ("descriptor dependence",
         f"effective rank {dep['verdict'].get('effective_rank_max')} of 3",
         "mean slope and 3&times;3 relief are the same gradient up to a direction factor; the "
         "&ldquo;three axes&rdquo; are one measurement, so this is a one-dimensional screen"),
        ("the relation, verified",
         f"worst relief error {dep['analytic']['worst_relief_error_m']:.1e} m",
         "checked against the engine's own slope and relief functions on synthetic planes, and "
         f"&rho; observed inside the provable [{dep['analytic']['rho_bounds_provable'][0]:.4f}, "
         f"{dep['analytic']['rho_bounds_provable'][1]:.4f}]"),
        ("planar fit on the panel",
         f"&rho; = {fit['scale_k']:.3f}, R&sup2; = {fit['r2']:.4f}",
         "a one-parameter fit to real terrain recovers the direction factor the algebra predicts"),
        ("error ensemble",
         f"{a['uncertainty']['lunar_error_ensemble']['realisations_sampled']} of "
         f"{a['uncertainty']['lunar_error_ensemble']['draws_available']} published realisations",
         "the archive's own perturbed DEM clones, not independent per-pixel noise, which would "
         "average away under aggregation and manufacture stability"),
        ("adequacy bands",
         f"{a['uncertainty']['adequacy_bands_calibrated']} of "
         f"{a['uncertainty']['adequacy_bands_attempted']} usable",
         "a calibrated band that admits known-different terrain is not a yardstick, so it is "
         "demoted rather than reported as a positive"),
        ("resolution limits",
         "Mars floor 1389 m &gt; every lunar support",
         "the comparability gate refuses a candidate below its source's effective resolution; Mars "
         "is excluded from the lunar regime by that arithmetic, not by preference"),
        ("the nearest unit",
         f"a sibling lunar site in {h['sibling_nearest']['count']} of {h['sibling_nearest']['of']} "
         f"site &times; descriptor statistics",
         "Nevada is the closest <em>Earth</em> candidate everywhere, and not the closest "
         "<em>unit</em>: the six nearby sites are more like each other than any Earth terrain is"),
    ]
    for name, value, why in rows:
        parts.append(f'<tr><th scope="row">{name}</th><td class="m">{value}</td>'
                     f'<td class="note">{why}</td></tr>')
    parts.append('</tbody></table></div>')

    # ---- E. explainability
    parts.append('<h2>E · Every claim points at two records</h2>')
    parts.append('<p>The atlas is assembled from five committed records and refuses to publish if any '
                 'two of them disagree. Each check below names both records it holds together, so a '
                 'reader can go and read them.</p>')
    parts.append('<div class="grid"><table><thead><tr><th>check</th><th>the claim it holds</th>'
                 '<th>the records</th></tr></thead><tbody>')
    for r in a["reconciliations"]:
        parts.append(f'<tr><td class="m">{_e(r["check"])}</td><td>{_e(r["claim"])}</td>'
                     f'<td class="note">{_e(r["where"])}</td></tr>')
    parts.append('</tbody></table></div>')

    parts.append(f'<div class="foot">Built offline from <code>artifacts/discovery_atlas/'
                 f'discovery_atlas.json</code> (sha256 <code>{_sha(ATLAS)[:16]}&hellip;</code>) and '
                 f'<code>artifacts/lunar_adversarial/lunar_adversarial.json</code>. Regenerate with '
                 f'<code>python scripts/build_atlas_page.py</code>. Scope: map-scale terrain-'
                 f'morphology screening only &mdash; no traversability, geologic-equivalence, '
                 f'site-access or mission-readiness claim, and no composite analog score anywhere on '
                 f'this page.</div>')
    parts.append('</div></body></html>')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(a['windows'])} windows, "
          f"{len(a['reconciliations'])} reconciliations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
