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
LANDFORM_FORMS = ("flat", "peak", "ridge", "shoulder", "spur", "slope",
                  "hollow", "footslope", "valley", "pit")


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
    for g in pkg.get("transfer_gap_ledger", {}).get("gaps", []):
        cls = html.escape(str(g.get("class", "")))
        out.append(
            f"<li><span class='tc tc-{cls}'>{cls}</span> "
            f"<strong>{html.escape(str(g.get('category', '')))}</strong> &mdash; "
            f"{html.escape(str(g.get('statement', '')))} "
            f"<em>{html.escape(str(g.get('prohibited', '')))}</em></li>")
    return "\n".join(out)


def _flips(pkg):
    rows = []
    for pair, frac in sorted(pkg["pairwise_flip_matrix"].items()):
        rows.append(f"<tr><th scope='row'>{html.escape(pair)}</th><td>{frac:.2f}</td></tr>")
    return "\n".join(rows) or "<tr><td colspan='2'>n/a</td></tr>"


def _matrix_section(pkg):
    """Decision matrix: rows = eligible units, columns = decision axes, cells = the
    per-axis normalized distance. No single composite score is produced on purpose."""
    metrics = list(pkg["profile"].get("metrics", []))
    vectors = pkg.get("baseline_vectors") or {}
    head = "".join(f"<th scope='col'>{html.escape(str(m))}</th>" for m in metrics)
    body = []
    for uid in sorted(vectors):
        vec = vectors[uid]
        rec = " &#9733;" if uid == pkg.get("recommended_unit") else ""
        cells = []
        for i in range(len(metrics)):
            x = vec[i] if i < len(vec) else None
            cells.append(f"<td>{x:.3f}</td>" if isinstance(x, (int, float)) else "<td>&mdash;</td>")
        body.append(f"<tr><th scope='row'>{html.escape(str(uid))}{rec}</th>{''.join(cells)}</tr>")
    body_html = "\n".join(body) or f"<tr><td colspan='{len(metrics) + 1}'>no eligible units</td></tr>"
    return (
        "<section><h2>DECISION MATRIX (per-axis distance to reference)</h2>"
        "<p class='sub'>Each cell is the normalized distance on one decision axis; "
        "<strong>lower = closer</strong> to the Mars reference. Rows are the eligible Earth "
        "units and a star marks a recommended follow-up. Axes are reported separately on "
        "purpose: <strong>no single composite &quot;Mars-likeness&quot; score is produced</strong>, "
        "and the ranking is by Pareto dominance across these axes (a tie is a valid result).</p>"
        "<table><thead><tr><th scope='col'>unit</th>" + head + "</tr></thead>"
        "<tbody>" + body_html + "</tbody></table></section>")


def _frontier_section(pkg):
    """Pareto-layer ranking panel, or '' if the study carries no frontier."""
    fr = pkg.get("frontier")
    if not fr:
        return ""
    rank = fr.get("rank", {})
    rows = []
    for uid in sorted(rank, key=lambda u: (rank[u], u)):
        rec = " &#9733;" if uid == pkg.get("recommended_unit") else ""
        rows.append(f"<tr><th scope='row'>{html.escape(str(uid))}{rec}</th>"
                    f"<td>{int(rank[uid])}</td></tr>")
    body = "\n".join(rows) or "<tr><td colspan='2'>n/a</td></tr>"
    note = html.escape(str(fr.get("note", "")))
    return (
        "<section><h2>PARETO FRONTIER (layer rank)</h2>"
        "<p class='sub'>Layer 1 is the non-dominated set (best); each higher layer is peeled "
        "after the better layers are removed. Layer membership is the ranking &mdash; "
        "within-layer order is by id and carries no score. " + note + "</p>"
        "<table><thead><tr><th scope='col'>unit</th><th scope='col'>Pareto layer</th></tr></thead>"
        "<tbody>" + body + "</tbody></table></section>")


def _boot_section(pkg):
    """Render the bootstrap-uncertainty panel, or '' if the study has none."""
    boot = pkg.get("bootstrap")
    if not boot:
        return ""
    method = html.escape(str(boot.get("method", "independent")))
    honest = html.escape(str(boot.get("note", "")))
    rows = []
    for uid in sorted(boot["units"]):
        u = boot["units"][uid]
        ci = u["distance_ci"].get("slope", [float("nan")] * 3)
        rows.append(
            f"<tr><th scope='row'>{html.escape(uid)}</th>"
            f"<td>{u['nondominated_freq']*100:.0f}%</td>"
            f"<td>{u['clear_winner_freq']*100:.0f}%</td>"
            f"<td>{ci[1]:.2f} <span style='color:#7f9398'>[{ci[0]:.2f}–{ci[2]:.2f}]</span></td></tr>")
    return (
        "<section><h2>UNCERTAINTY (BOOTSTRAP, n=" + str(boot["n_boot"]) + ")</h2>"
        "<p class='sub'>Method: <strong>" + method + "</strong> resampling. "
        "Feature distributions resampled with replacement. "
        "Non-domination frequency is how often each unit is Pareto non-dominated across "
        "resamples; a single clear winner appears in " + f"{boot['decisive_freq']*100:.0f}%" +
        " of resamples. Slope-distance shown as median [95% CI].</p>"
        "<table><thead><tr><th scope='col'>unit</th><th scope='col'>non-dominated</th>"
        "<th scope='col'>clear winner</th><th scope='col'>slope distance</th></tr></thead>"
        "<tbody>" + "\n".join(rows) + "</tbody></table>"
        "<p class='sub note'>" + honest + "</p></section>")


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
/* Narrow viewports — and, equivalently, 200% zoom on a desktop window — must not clip a
   value. Tables WRAP rather than scroll: a horizontally scrollable region would have to be
   focusable to stay keyboard-reachable (WCAG 2.1.1), and this document ships no script. */
@media(max-width:820px){
 .grid{grid-template-columns:1fr}
 h1{font-size:34px}
 .wrap{padding:26px 16px 56px}
 table{font-size:12.5px}
 th,td{padding:6px 5px;word-break:break-word}
 td.vec,.hash{font-size:11px}
 .sub{font-size:16px}
}
.foot{margin-top:40px;color:#789096;font-size:12px}
.badge{display:inline-block;padding:3px 12px;border-radius:999px;background:#A8513A;color:#fff;
 font-size:12px;font-weight:700;letter-spacing:.16em;border:1px solid #c56a4f}
.badge-line{margin:.4em 0 .1em}
.bl{color:#789096;font-size:12px;letter-spacing:.14em;margin-left:9px}
.note{color:#9fb0b5}
"""


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TerraTrace v0.1 - study viewer</title>
<style>{css}</style></head>
<body><main class="wrap">
<p class="eyebrow">PLANETARY ANALOG OS / TERRATRACE v0.1</p>
<p class="badge-line"><span class="badge">{body_badge}</span><span class="bl">target reference body</span></p>
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

{matrix_section}

{frontier_section}

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

{uncertainty_section}

{previews_section}{landform_section}{scale_fabric_section}{confidence_section}

<section><h2>PROVENANCE</h2>
<p class="sub">Every value derives from the <strong>{source}</strong> source through a recorded
transformation and resolves in the evidence graph. Package hash:</p>
<p class="hash">{phash}</p></section>

<details><summary>Raw study package (JSON)</summary>
<pre class="hash">{rawjson}</pre></details>

<p class="foot">TerraTrace reference engine - source: {source} - morphology screening build.
Not an official NASA submission artifact. Not NASA-endorsed.</p>
</main></body></html>"""


def _uncertainty_section(pkg):
    """Propagated measurement-uncertainty table; empty unless the package carries it."""
    fu = pkg.get("feature_uncertainty")
    if not isinstance(fu, dict) or not fu:
        return ""
    rows = []
    for uid in sorted(fu):
        r = fu[uid] or {}
        rows.append(
            f"<tr><td>{html.escape(str(uid))}</td><td>{r.get('sigma_z', '')}</td>"
            f"<td>{round(float(r.get('slope_sigma_deg', 0) or 0), 3)}</td>"
            f"<td>{round(float(r.get('relief_sigma_m', 0) or 0), 3)}</td></tr>")
    return ("<section><h2>MEASUREMENT UNCERTAINTY</h2>"
            "<p class='sub'>1&sigma; propagated from each DEM's vertical accuracy "
            "(optimistic: assumes independent pixels).</p>"
            "<table><tr><th>unit</th><th>&sigma;z (m)</th><th>slope &sigma; (deg)</th>"
            "<th>relief &sigma; (m)</th></tr>" + "".join(rows) + "</table></section>")


def _previews_section(pkg):
    """Inline self-contained hillshade previews; empty unless the package carries them."""
    pv = pkg.get("previews")
    if not isinstance(pv, dict) or not pv:
        return ""
    figs = []
    for uid in sorted(pv):
        uri = pv[uid]
        if isinstance(uri, str) and uri.startswith("data:image/png;base64,"):
            figs.append(f"<figure style='display:inline-block;margin:6px;text-align:center'>"
                        f"<img alt='hillshade of {html.escape(str(uid))}' "
                        f"src='{html.escape(uri)}' style='width:160px;image-rendering:pixelated'>"
                        f"<figcaption class='sub'>{html.escape(str(uid))}</figcaption></figure>")
    if not figs:
        return ""
    return ("<section><h2>TERRAIN PREVIEWS</h2>"
            "<p class='sub'>Shaded-relief hillshades at the common support (illustrative).</p>"
            + "".join(figs) + "</section>")


def _landform_section(pkg):
    """Landform-structure panel (geomorphons + topographic openness). Returns ''
    unless the package carries a non-empty 'landform' block, so a plain study
    viewer is byte-for-byte unchanged. Lighter than the HTML report."""
    lf = pkg.get("landform")
    if not isinstance(lf, dict) or not lf:
        return ""
    forms = list(LANDFORM_FORMS)
    for uid in lf:
        for f in ((lf[uid] or {}).get("composition") or {}):
            if f not in forms:
                forms.append(f)
    forms = list(LANDFORM_FORMS) + sorted(forms[len(LANDFORM_FORMS):])
    head = "".join(f"<th scope='col'>{html.escape(str(f))}</th>" for f in forms)
    rows = []
    for uid in sorted(lf):
        rec = lf[uid] or {}
        comp = rec.get("composition") or {}
        op = rec.get("openness") or {}
        cells = []
        for f in forms:
            v = comp.get(f)
            cells.append(f"<td>{v * 100:.1f}%</td>"
                         if isinstance(v, (int, float)) else "<td>&mdash;</td>")
        pos, neg = op.get("positive_median"), op.get("negative_median")
        pos_s = f"{pos:.2f}" if isinstance(pos, (int, float)) else "&mdash;"
        neg_s = f"{neg:.2f}" if isinstance(neg, (int, float)) else "&mdash;"
        rows.append(f"<tr><th scope='row'>{html.escape(str(uid))}</th>{''.join(cells)}"
                    f"<td>{html.escape(str(rec.get('dominant_form', '')))}</td>"
                    f"<td>{pos_s}</td><td>{neg_s}</td></tr>")
    figs = []
    for key, what in (("landform_previews", "categorical landform map"),
                      ("openness_previews", "positive-openness map")):
        maps = pkg.get(key)
        if not isinstance(maps, dict):
            continue
        for uid in sorted(maps):
            uri = maps[uid]
            if isinstance(uri, str) and uri.startswith("data:image/png;base64,"):
                figs.append(
                    f"<figure style='display:inline-block;margin:6px;text-align:center'>"
                    f"<img alt='{what} of {html.escape(str(uid))}' src='{html.escape(uri)}' "
                    f"style='width:160px;image-rendering:pixelated'>"
                    f"<figcaption class='sub'>{html.escape(str(uid))} &mdash; {what}"
                    f"</figcaption></figure>")
    return (
        "\n\n<section><h2>LANDFORM STRUCTURE (GEOMORPHONS + OPENNESS)</h2>"
        "<p class='sub'>Per-unit geomorphon form composition (% of valid cells), dominant "
        "form, and median topographic openness (positive = exposed, negative = enclosed).</p>"
        "<table><thead><tr><th scope='col'>unit</th>" + head +
        "<th scope='col'>dominant</th><th scope='col'>open+ med</th>"
        "<th scope='col'>open- med</th></tr></thead><tbody>" + "\n".join(rows) +
        "</tbody></table>" + "".join(figs) +
        "<p class='sub note'>Map-scale landform morphology (geomorphons, Jasiewicz &amp; "
        "Stepinski 2013) and topographic openness (Yokoyama 2002). Morphology only &mdash; "
        "not traversability, hazard, or geologic-unit identification.</p></section>")


def _scale_fabric_section(pkg):
    """Scale & fabric panel for the viewer (GATED; a lighter mirror of
    report_html._scale_fabric_html). Returns '' unless the package carries a
    non-empty 'spectral' or 'anisotropy' block (the opt-in terrain_spectra pass),
    so a plain study viewer is byte-for-byte unchanged. The returned string carries
    its OWN leading separator, so an empty return keeps the viewer byte-for-byte
    unchanged (the template places {scale_fabric_section} between {landform_section}
    and {confidence_section}). Each sub-table is guarded independently; all escaped."""
    sp = pkg.get("spectral")
    an = pkg.get("anisotropy")
    sp = sp if isinstance(sp, dict) and sp else None
    an = an if isinstance(an, dict) and an else None
    if not sp and not an:
        return ""
    e = html.escape

    def _f(x):
        return f"{x:.4g}" if isinstance(x, (int, float)) else "&mdash;"

    out = ["\n\n<section><h2>SCALE &amp; FABRIC (SPECTRAL ROUGHNESS + ANISOTROPY)</h2>"
           "<p class='sub'>Per-unit roughness spectrum (power-spectral slope + band RMS) "
           "and directional terrain fabric of each sampled DEM.</p>"]
    if sp:
        rows = []
        for uid in sorted(sp):
            r = sp[uid] or {}
            rows.append(
                f"<tr><th scope='row'>{e(str(uid))}</th>"
                f"<td>{_f(r.get('spectral_slope'))}</td><td>{_f(r.get('peak_wavelength_m'))}</td>"
                f"<td>{_f(r.get('roughness_rms'))}</td><td>{_f(r.get('rough_long'))}</td>"
                f"<td>{_f(r.get('rough_mid'))}</td><td>{_f(r.get('rough_short'))}</td></tr>")
        out.append("<table><thead><tr><th scope='col'>unit</th>"
                   "<th scope='col'>spectral slope</th><th scope='col'>peak &lambda; (m)</th>"
                   "<th scope='col'>RMS</th><th scope='col'>long</th><th scope='col'>mid</th>"
                   "<th scope='col'>short</th></tr></thead><tbody>" + "\n".join(rows) +
                   "</tbody></table>")
    if an:
        rows = []
        for uid in sorted(an):
            r = an[uid] or {}
            rows.append(
                f"<tr><th scope='row'>{e(str(uid))}</th>"
                f"<td>{_f(r.get('strength'))}</td><td>{_f(r.get('orientation_deg'))}</td>"
                f"<td>{_f(r.get('isotropy'))}</td></tr>")
        out.append("<table><thead><tr><th scope='col'>unit</th>"
                   "<th scope='col'>anisotropy strength</th>"
                   "<th scope='col'>orientation (&deg;)</th>"
                   "<th scope='col'>isotropy</th></tr></thead><tbody>" + "\n".join(rows) +
                   "</tbody></table>")
    out.append("<p class='sub note'>Spectral slope and directional fabric are map-scale "
               "roughness/morphology descriptors of the sampled DEM. Spectral slope "
               "summarises how power is shared across wavelengths; anisotropy "
               "strength/orientation describe directional terrain fabric (ridges, dunes, "
               "grain). Morphology only &mdash; not a traversability, hazard, or geologic "
               "claim.</p></section>")
    return "".join(out)


def _significance_section_viewer(pkg):
    """Per-metric permutation-significance table for the viewer; '' when the package
    carries no 'significance' block. When present but ``evaluated`` is False, render a
    single honest line stating why. Connectivity is a scalar axis (no p-value)."""
    sig = pkg.get("significance")
    if not isinstance(sig, dict) or not sig:
        return ""
    e = html.escape
    if sig.get("evaluated") is False or "per_metric" not in sig:
        return ("<p class='sub note'>Permutation significance was not evaluated: "
                + e(str(sig.get("reason", "not evaluated"))) + ".</p>")

    def _f(x):
        return f"{x:.4g}" if isinstance(x, (int, float)) else "n/a"

    rows = []
    for m in sorted(sig.get("per_metric", {}) or {}):
        row = sig["per_metric"][m] or {}
        mark = "&#10003;" if row.get("significant") else "&mdash;"
        rows.append(
            f"<tr><th scope='row'>{e(str(m))}</th>"
            f"<td>{_f(row.get('observed_diff'))}</td>"
            f"<td>{_f(row.get('p_value_one_sided'))}</td>"
            f"<td>{_f(row.get('p_value_two_sided'))}</td>"
            f"<td>{_f(row.get('effect_size'))}</td>"
            f"<td>{mark}</td><td>{e(str(row.get('method', '')))}</td></tr>")
    rec, runner = e(str(sig.get("recommended_unit", ""))), e(str(sig.get("runner_up", "")))
    overall = "yes" if sig.get("recommendation_significant") else "no"
    return (
        "<p class='sub'>Significance vs runner-up: recommended <strong>" + rec +
        "</strong> vs <strong>" + runner + "</strong> &mdash; one-sided permutation "
        "closeness test, " + _f(sig.get("n_perm")) + " permutations. Overall "
        "<strong>recommendation significant: " + overall + "</strong>. A negative "
        "observed difference means the recommended unit is the closer one; "
        "connectivity is a single scalar, so it carries no p-value.</p>"
        "<table><thead><tr><th scope='col'>metric</th><th scope='col'>observed_diff</th>"
        "<th scope='col'>p one-sided</th><th scope='col'>p two-sided</th>"
        "<th scope='col'>effect size</th><th scope='col'>significant</th>"
        "<th scope='col'>method</th></tr></thead><tbody>" + "\n".join(rows) +
        "</tbody></table>")
def _confidence_section(pkg):
    """Decision-confidence panel for the viewer (GATED; mirrors
    report_html._confidence_html). Returns '' unless a robustness signal was actually
    computed (``bool(significance) or bool(bootstrap)``). The returned string carries
    its OWN leading separator, so an empty return keeps the viewer byte-for-byte
    unchanged (the template places {confidence_section} directly after
    {landform_section}). Restates three independent signals + one categorical verdict
    via confidence.decision_confidence; NO composite score. All text escaped."""
    if not (bool(pkg.get("significance")) or bool(pkg.get("bootstrap"))):
        return ""
    from terratrace import confidence
    conf = confidence.decision_confidence(pkg)
    e = html.escape
    verdict = str(conf.get("verdict", ""))
    signals = conf.get("signals", {}) or {}
    labels = (("bootstrap_non_domination", "bootstrap non-domination"),
              ("significance_vs_runner_up", "significance vs runner-up"),
              ("lens_stability", "lens/support stability"))
    rows = []
    for key, label in labels:
        s = signals.get(key, {}) or {}
        ev = bool(s.get("evaluated"))
        val = "&mdash;"
        if ev and key == "bootstrap_non_domination":
            v = s.get("value")
            val = f"{v * 100:.0f}%" if isinstance(v, (int, float)) else "&mdash;"
        elif ev and key == "significance_vs_runner_up":
            val = "significant" if s.get("significant") else "not significant"
            pv = s.get("p_value_one_sided")
            if isinstance(pv, (int, float)):
                val += f", weakest p={pv:.4g}"
        elif ev and key == "lens_stability":
            val = "stable" if s.get("stable") else "not stable"
        rows.append(f"<tr><th scope='row'>{e(label)}</th>"
                    f"<td>{'yes' if ev else 'no'}</td><td>{val}</td>"
                    f"<td>{e(str(s.get('detail', '')))}</td></tr>")
    caveats = conf.get("caveats", []) or []
    cav = ("".join(f"<li>{e(str(c))}</li>" for c in caveats) if caveats
           else "<li>all three robustness signals were evaluated</li>")
    return (
        "\n\n<section><h2>DECISION CONFIDENCE</h2>"
        "<div class='state'><b>Verdict: " + e(verdict.upper()) + "</b> &mdash; "
        + e(conf.get("rationale", "")) + "</div>"
        "<p class='sub'>Three independent robustness signals, reported separately "
        "with <strong>no composite score</strong>.</p>"
        "<table><thead><tr><th scope='col'>signal</th><th scope='col'>evaluated</th>"
        "<th scope='col'>value / flag</th><th scope='col'>detail</th></tr></thead>"
        "<tbody>" + "\n".join(rows) + "</tbody></table>"
        "<p class='sub'>Not evaluated:</p><ul class='gaps'>" + cav + "</ul>"
        + _significance_section_viewer(pkg) +
        "<p class='sub note'>Decision confidence restates existing robustness evidence "
        "(bootstrap non-domination, a permutation test vs the runner-up, and "
        "lens/support stability) as independent signals and one categorical verdict "
        "&mdash; there is no composite score. Morphology/statistics only; not a "
        "traversability, hazard, or mission-readiness claim.</p></section>")


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
        state=html.escape(str(state)),
        state_copy=html.escape(STATE_COPY.get(state, state)),
        rec_line=rec_line,
        source=html.escape(source),
        support=html.escape(str(pkg["profile"].get("target_support_m", ""))),
        decision_metrics=html.escape(pkg["profile"].get("decision_metrics", "core")),
        metric_names=html.escape(", ".join(pkg["profile"].get("metrics", []))),
        body_badge=html.escape(str(pkg["profile"].get("target_body", "")).upper()),
        matrix_section=_matrix_section(pkg),
        frontier_section=_frontier_section(pkg),
        rows=_rows(pkg),
        ext_rows=_ext_rows(pkg),
        citations=_citations(pkg),
        gaps=_gaps(pkg),
        flips=_flips(pkg),
        boot_section=_boot_section(pkg),
        uncertainty_section=_uncertainty_section(pkg),
        previews_section=_previews_section(pkg),
        landform_section=_landform_section(pkg),
        scale_fabric_section=_scale_fabric_section(pkg),
        confidence_section=_confidence_section(pkg),
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
