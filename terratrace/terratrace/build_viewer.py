"""Build a self-contained, offline HTML viewer from a study package.

The viewer is pre-rendered in Python (no runtime fetch, no external
assets) so it is reproducible and works in any offline preview.
"""
from __future__ import annotations

import html
import json
import pathlib

from .sourcelock import CITATIONS, TERMS

METRIC_LABELS = ["slope", "relief", "ruggedness", "connectivity"]
STATE_COPY = {
    "RECOMMEND_FOLLOW_UP": "Follow-up study candidate identified",
    "TIE": "Tie - evidence does not separate candidates",
    "INDETERMINATE": "Indeterminate - result depends on assumptions",
    "NOT_COMPARABLE": "Not comparable at available support",
    "BLOCKED": "Blocked - resolve data or rights first",
}


def _rows(pkg):
    out = []
    for uid, meta in pkg["unit_metadata"].items():
        if uid == "mars_reference":
            continue
        elig = pkg["eligibility"][uid]
        vec = pkg["baseline_vectors"].get(uid)
        vecs = "&mdash;" if not vec else "[" + ", ".join(f"{v:.3f}" for v in vec) + "]"
        status = "eligible" if elig["eligible"] else html.escape(elig["reason"])
        rec = " &#9733;" if uid == pkg["recommended_unit"] else ""
        zf = meta.get("zero_fraction")
        zf_s = f"{zf:.2f}" if isinstance(zf, (int, float)) else "-"
        out.append(
            f"<tr><th scope='row'>{html.escape(uid)}{rec}</th>"
            f"<td class='vec'>{vecs}</td>"
            f"<td>{meta['valid_fraction']:.2f}</td><td>{zf_s}</td><td>{status}</td></tr>")
    return "\n".join(out)


def _ext_rows(pkg):
    out = []
    for uid, m in (pkg.get("extended_metrics") or {}).items():
        ad, hi = m.get("aspect_dispersion"), m.get("hypsometric_integral")
        ad_s = f"{ad:.3f}" if isinstance(ad, (int, float)) else "&mdash;"
        hi_s = f"{hi:.3f}" if isinstance(hi, (int, float)) else "nan"
        out.append(f"<tr><th scope='row'>{html.escape(uid)}</th><td>{ad_s}</td><td>{hi_s}</td></tr>")
    return "\n".join(out)


def _citations(pkg):
    out = []
    for body in ("mars", "earth"):
        out.append(f"<li><strong>{body.title()}:</strong> {html.escape(CITATIONS[body])} "
                   f"<em>{html.escape(TERMS[body])}</em></li>")
    return "\n".join(out)


def _gaps(pkg):
    out = []
    for g in pkg["transfer_gap_ledger"]["gaps"]:
        out.append(
            f"<li><span class='tc tc-{g['class']}'>{g['class']}</span> "
            f"<strong>{html.escape(g['category'])}</strong> &mdash; "
            f"{html.escape(g['statement'])} "
            f"<em>{html.escape(g['prohibited'])}</em></li>")
    return "\n".join(out)


def _flips(pkg):
    rows = []
    for pair, frac in sorted(pkg["pairwise_flip_matrix"].items()):
        rows.append(f"<tr><th scope='row'>{html.escape(pair)}</th><td>{frac:.2f}</td></tr>")
    return "\n".join(rows) or "<tr><td colspan='2'>n/a</td></tr>"


def _boot_section(pkg):
    """Render the bootstrap-uncertainty panel, or '' if the study has none."""
    boot = pkg.get("bootstrap")
    if not boot:
        return ""
    rows = []
    for uid, u in boot["units"].items():
        ci = u["distance_ci"].get("slope", [float("nan")] * 3)
        rows.append(
            f"<tr><th scope='row'>{html.escape(uid)}</th>"
            f"<td>{u['nondominated_freq']*100:.0f}%</td>"
            f"<td>{u['clear_winner_freq']*100:.0f}%</td>"
            f"<td>{ci[1]:.2f} <span style='color:#7f9398'>[{ci[0]:.2f}–{ci[2]:.2f}]</span></td></tr>")
    return (
        "<section><h2>UNCERTAINTY (BOOTSTRAP, n=" + str(boot["n_boot"]) + ")</h2>"
        "<p class='sub'>Feature distributions resampled with replacement. "
        "Non-domination frequency is how often each unit is Pareto non-dominated across "
        "resamples; a single clear winner appears in " + f"{boot['decisive_freq']*100:.0f}%" +
        " of resamples. Slope-distance shown as median [95% CI].</p>"
        "<table><thead><tr><th scope='col'>unit</th><th scope='col'>non-dominated</th>"
        "<th scope='col'>clear winner</th><th scope='col'>slope distance</th></tr></thead>"
        "<tbody>" + "\n".join(rows) + "</tbody></table></section>")


CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0A1118;color:#EAF0F1;
 font-family:'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.55}
.wrap{max-width:1040px;margin:0 auto;padding:40px 28px 72px}
.eyebrow{color:#9BE4E9;letter-spacing:.22em;font-size:13px}
h1{font-family:Georgia,'Times New Roman',serif;font-size:46px;margin:.2em 0 .1em;font-weight:600}
.sub{color:#B7C5C8;font-size:19px;max-width:62ch}
.ribbon{margin:22px 0;padding:12px 16px;border:1px solid #30454D;border-left:4px solid #A8513A;
 background:#121F26;border-radius:8px;color:#E7E1D5;font-size:15px}
.state{margin:26px 0;padding:18px 20px;border-radius:12px;background:#122a24;border:1px solid #2f6b52}
.state b{color:#8FCA9B}
section{margin:34px 0}
h2{font-size:16px;letter-spacing:.12em;color:#9BE4E9;border-bottom:1px solid #26343b;padding-bottom:6px}
table{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #1f2c33}
thead th{color:#9fb0b5;font-weight:600}
tbody th{color:#EAF0F1;font-weight:600}
td{font-variant-numeric:tabular-nums;color:#CBD6D9}
td.vec{font-family:ui-monospace,Consolas,monospace;color:#9BE4E9;font-size:13px}
ul.gaps{list-style:none;padding:0;margin:12px 0}
ul.gaps li{padding:9px 0;border-bottom:1px solid #1f2c33;font-size:14px;color:#CBD6D9}
ul.gaps em{color:#D6A33A;font-style:normal}
.tc{display:inline-block;min-width:30px;text-align:center;border-radius:5px;padding:1px 7px;margin-right:8px;
 font-size:12px;font-weight:700;color:#0A1118}
.tc-T0{background:#4C8B69}.tc-T1{background:#38B5C5}.tc-T2{background:#A8513A;color:#fff}
.tc-T3{background:#D6A33A}.tc-T4{background:#7B4056;color:#fff}
.hash{font-family:ui-monospace,Consolas,monospace;color:#7f9398;font-size:12px;word-break:break-all}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:760px){.grid{grid-template-columns:1fr}h1{font-size:34px}}
.foot{margin-top:40px;color:#789096;font-size:12px}
"""


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TerraTrace v0.1 - study viewer</title>
<style>{css}</style></head>
<body><main class="wrap">
<p class="eyebrow">PLANETARY ANALOG OS / TERRATRACE v0.1</p>
<h1>Map-scale morphology transfer audit</h1>
<p class="sub">A reproducible comparison of a Mars reference terrain unit with
candidate Earth terrain units at a declared common support of {support} m.</p>
<div class="ribbon"><strong>Scope.</strong> This screens terrain morphology only.
It does not estimate rover traversability, validate autonomy, establish geological
equivalence, certify site access, or certify mission readiness.</div>

<div class="state"><b>Result: {state}</b> &mdash; {state_copy}.
{rec_line}</div>

<section><h2>MORPHOLOGY COMPARISON (normalized distance to reference)</h2>
<p class="sub">Decision axes ({decision_metrics}): {metric_names}. Lower is closer.
A star marks a recommended follow-up unit. No single composite "Mars-likeness"
score is produced; ranking is by Pareto dominance, and a tie is a valid result.</p>
<table><thead><tr><th scope="col">Earth terrain unit</th>
<th scope="col">distance vector</th><th scope="col">valid</th>
<th scope="col">zero</th><th scope="col">eligibility</th>
</tr></thead><tbody>
{rows}
</tbody></table></section>

<section><h2>EXTENDED MORPHOLOGY DESCRIPTORS</h2>
<table><thead><tr><th scope="col">unit</th>
<th scope="col">aspect dispersion</th><th scope="col">hypsometric integral</th>
</tr></thead><tbody>
{ext_rows}
</tbody></table>
<p class="sub">Aspect dispersion: 0 = one downslope direction, 1 = isotropic.
Hypsometric integral: elevation-distribution shape (0.5 = symmetric). Reported
for transparency; included in the decision only when decision axes = extended.</p></section>

<div class="grid">
<section><h2>SENSITIVITY (pairwise rank-flip fraction)</h2>
<table><thead><tr><th scope="col">pair</th><th scope="col">flip</th></tr></thead>
<tbody>{flips}</tbody></table>
<p class="sub">0.00 means the pairwise comparison never changed sign across the
tested scenarios. High values mean the result is assumption-sensitive.</p></section>

<section><h2>DRAFT STUDY PROTOCOL</h2>
<p class="sub">{objective}</p>
<div class="ribbon">{auth}</div></section>
</div>

<section><h2>WHAT THIS COMPARISON CANNOT ESTABLISH</h2>
<ul class="gaps">
{gaps}
</ul></section>

<section><h2>DATA SOURCES &amp; CITATIONS</h2>
<ul class="gaps">
{citations}
</ul></section>

{boot_section}

<section><h2>PROVENANCE</h2>
<p class="sub">Every value derives from the <strong>{source}</strong> source through a recorded
transformation and resolves in the evidence graph. Package hash:</p>
<p class="hash">{phash}</p></section>

<details><summary>Raw study package (JSON)</summary>
<pre class="hash">{rawjson}</pre></details>

<p class="foot">TerraTrace reference engine - source: {source} - morphology screening build.
Not an official NASA submission artifact. Not NASA-endorsed.</p>
</main></body></html>"""


def build_html(pkg):
    state = pkg["result_state"]
    proto = pkg["draft_protocol"]
    source = pkg["profile"].get("source_label", "unspecified")
    if state == "RECOMMEND_FOLLOW_UP" and pkg["recommended_unit"]:
        rec_line = f"Recommended follow-up unit: <strong>{html.escape(str(pkg['recommended_unit']))}</strong>."
    else:
        rec_line = "No single unit is recommended; see the result state and sensitivity below."
    return TEMPLATE.format(
        css=CSS,
        state=state,
        state_copy=html.escape(STATE_COPY.get(state, state)),
        rec_line=rec_line,
        source=html.escape(source),
        support=pkg["profile"]["target_support_m"],
        decision_metrics=html.escape(pkg["profile"].get("decision_metrics", "core")),
        metric_names=html.escape(", ".join(pkg["profile"].get("metrics", []))),
        rows=_rows(pkg),
        ext_rows=_ext_rows(pkg),
        citations=_citations(pkg),
        gaps=_gaps(pkg),
        flips=_flips(pkg),
        boot_section=_boot_section(pkg),
        objective=html.escape(proto["objective"]),
        auth=html.escape(proto["authorization"]),
        phash=html.escape(pkg["package_hash"]),
        rawjson=html.escape(json.dumps(pkg, indent=2, sort_keys=True)),
    )


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default="artifacts/study.json")
    ap.add_argument("--out", default="viewer/index.html")
    args = ap.parse_args(argv)
    pkg = json.loads(pathlib.Path(args.study).read_text(encoding="utf-8"))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(pkg), encoding="utf-8")
    print(f"viewer -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
