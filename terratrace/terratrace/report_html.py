"""Self-contained, offline HTML reporting for TerraTrace packages.

Renders a study package (:func:`terratrace.study.compare_units` / ``run_study``)
or a cross-reference batch report (:func:`terratrace.batch.run_batch`) into a
single, polished, SELF-CONTAINED HTML document: inline CSS only, NO external or
CDN assets, no network and no fonts to fetch -- it opens and prints offline, in
light mode.

It mirrors, section for section, the Markdown renderer in
:mod:`terratrace.report`, presenting the same information. The map-scale
morphology CLAIM FIREWALL is reproduced *verbatim* from the package: the
prohibited-claims list, the transfer-gap ledger, and the draft protocol are
rendered exactly as the engine emitted them. This renderer never widens,
softens, re-weights, or invents a claim.

Every dynamic value (unit ids, eligibility reasons, prohibited claims, scenario
names, hashes) is passed through :func:`html.escape`, so untrusted strings
cannot inject markup. Output is deterministic: no timestamps, no randomness.

Pure standard library (``html``, ``math``, ``os``). :func:`write_html` is the
only function that touches disk.
"""
from __future__ import annotations

import html
import math
import os

_STATE_PLAIN = {
    "RECOMMEND_FOLLOW_UP": ("one candidate is the stable, non-dominated morphology "
                            "analog across every declared sensitivity scenario."),
    "TIE": ("two or more candidates are morphologically indistinguishable at this "
            "support; no single analog separates out."),
    "INDETERMINATE": ("the ranking depends on declared assumptions -- it flips across "
                      "sensitivity scenarios -- so no stable recommendation is made."),
    "NOT_COMPARABLE": ("a valid common support could not be established, so the units "
                       "cannot be ranked."),
    "BLOCKED": ("an eligibility blocker (missing data, invalid support, or unverified "
                "rights/access) prevents comparison."),
}
def _esc(s):
    """html.escape(str(s)); None -> empty string."""
    if s is None:
        return ""
    return html.escape(str(s))


def _num(x, sig=4):
    """Format a scalar to ~`sig` significant figures. Safe for None / NaN / inf
    and for non-numeric input (escaped). The returned text is final, safe HTML."""
    if x is None:
        return "n/a"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return _esc(x)
    if math.isnan(xf):
        return "nan"
    if math.isinf(xf):
        return "inf" if xf > 0 else "-inf"
    return f"{xf:.{sig}g}"


def _pct(x):
    """Format a [0, 1] frequency as a percentage; safe for None/NaN/non-numeric."""
    if x is None:
        return "n/a"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return _esc(x)
    if math.isnan(xf):
        return "nan"
    return f"{xf * 100:.1f}%"


def _codes(seq):
    """Render a sequence as comma-separated inline-code tokens (escaped)."""
    items = [f"<code>{_esc(x)}</code>" for x in (seq or [])]
    return ", ".join(items) if items else "(none)"


CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#eef1f5;color:#1b2430;font-family:Georgia,'Times New Roman',serif;line-height:1.62}
.wrap{max-width:980px;margin:0 auto;padding:44px 40px 72px;background:#fff;box-shadow:0 1px 4px rgba(20,35,59,.08)}
.eyebrow{letter-spacing:.2em;font-size:12px;color:#5a6b84;text-transform:uppercase;font-family:'Segoe UI',Helvetica,Arial,sans-serif;margin:0}
h1{font-size:30px;line-height:1.2;margin:.15em 0 .35em;color:#14233b;font-weight:700}
h2{font-size:19px;margin:1.9em 0 .5em;color:#14233b;border-bottom:2px solid #e2e6ec;padding-bottom:6px}
h3{font-size:15px;margin:1.3em 0 .4em;color:#2a3645}
p,li{font-size:14.5px}
.meta{color:#55606e;font-size:13.5px;margin:.2em 0 0}
.firewall{margin:24px 0;padding:16px 20px;border:1px solid #e0bb55;border-left:5px solid #c6902a;background:#fdf6e0;border-radius:6px;color:#4a3c12}
.firewall strong{color:#7a5a12;letter-spacing:.04em;font-family:'Segoe UI',Helvetica,Arial,sans-serif}
.firewall ul{margin:10px 0 0;padding-left:20px}
.result{margin:16px 0;padding:14px 18px;border-radius:6px;background:#edf4ee;border:1px solid #b9d3c0}
.result p{margin:.3em 0}
blockquote.note{margin:12px 0;padding:8px 16px;border-left:4px solid #c3ccd8;color:#45515f;background:#f6f8fa;font-style:italic}
table{width:100%;border-collapse:collapse;margin:12px 0 20px;font-size:13.5px;font-family:'Segoe UI',Helvetica,Arial,sans-serif}
caption{caption-side:top;text-align:left;color:#55606e;font-size:12.5px;margin-bottom:6px}
th,td{text-align:left;padding:8px 11px;border-bottom:1px solid #e2e6ec;vertical-align:top}
thead th{background:#eef1f5;color:#243244;font-weight:700}
tbody th{color:#1b2430;font-weight:600}
tbody tr:nth-child(even){background:#f7f9fb}
td.num{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,Consolas,monospace}
code{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;background:#f0f2f6;padding:1px 5px;border-radius:4px;color:#2a3645}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;word-break:break-all;color:#3a4656}
.note{color:#55606e;font-size:13px}
ul.proto{list-style:none;padding-left:0}
ul.proto>li{margin:6px 0}
ul.proto ul{margin:4px 0 8px}
hr{border:0;border-top:1px solid #e2e6ec;margin:28px 0}
.foot{margin-top:28px;color:#78828f;font-size:12px}
@media print{body{background:#fff}.wrap{box-shadow:none;max-width:none;padding:0}}
"""


def _metric_table_html(title, metric_map, caption=""):
    """Optional '<h3>title</h3>' + per-unit table for a {uid: {k: v}} map.

    Returns '' when the map is empty. Subkeys and units are sorted, so the
    output is deterministic for a given map.
    """
    if not metric_map:
        return ""
    subkeys = []
    for uid in metric_map:
        for k in (metric_map[uid] or {}):
            if k not in subkeys:
                subkeys.append(k)
    subkeys = sorted(subkeys)
    out = [f"<h3>{_esc(title)}</h3>"]
    if not subkeys:
        out.append("<p class='note'>(no descriptor values)</p>")
        return "\n".join(out)
    out.append(f"<table><caption>{_esc(caption)}</caption>" if caption else "<table>")
    head = "".join(f"<th scope='col'>{_esc(k)}</th>" for k in subkeys)
    out.append(f"<thead><tr><th scope='col'>unit</th>{head}</tr></thead><tbody>")
    for uid in sorted(metric_map):
        row = metric_map[uid] or {}
        cells = "".join(f"<td class='num'>{_num(row.get(k))}</td>" for k in subkeys)
        out.append(f"<tr><th scope='row'>{_esc(uid)}</th>{cells}</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _firewall_html(p):
    """The highlighted SCOPE / CLAIM-FIREWALL box, listing prohibited_claims."""
    out = ['<div class="firewall"><strong>SCOPE / CLAIM-FIREWALL</strong>',
           "<p>This report screens <strong>map-scale terrain morphology only</strong> at "
           "the declared common support. It is NOT a rover-traversability, autonomy, "
           "geologic-equivalence, site-access, or mission-readiness result. The following "
           "claims are <strong>prohibited</strong> and are reproduced verbatim from the "
           "package; they bind every statement below:</p>", "<ul>"]
    for claim in p.get("prohibited_claims", []) or []:
        out.append(f"<li>{_esc(claim)}</li>")
    out.append("</ul></div>")
    return "\n".join(out)


def _decision_html(p, profile, metrics, dm):
    """Decision section: per-candidate x metric distance table (lower = closer)."""
    out = ["<h2>Decision</h2>",
           f"<p>Per-axis morphology distance from each candidate to the reference on the "
           f"<code>{dm}</code> decision axes. <strong>Lower = closer</strong> to the "
           f"reference on that axis. Candidates are compared by Pareto dominance across all "
           f"axes jointly: there is <strong>no composite &ldquo;Mars-likeness&rdquo; "
           f"score</strong> and no axis weighting.</p>"]
    if not metrics:
        out.append('<p class="note">No decision axes declared.</p>')
        return "\n".join(out)
    vectors = p.get("baseline_vectors", {}) or {}
    out.append("<table><caption>Normalized distance to reference (lower = closer)."
               "</caption>")
    head = "".join(f'<th scope="col">{_esc(m)}</th>' for m in metrics)
    out.append(f'<thead><tr><th scope="col">candidate</th>{head}</tr></thead><tbody>')
    if vectors:
        for uid in sorted(vectors):
            vec = vectors[uid] or []
            cells = "".join(
                f'<td class="num">{_num(vec[i]) if i < len(vec) else "n/a"}</td>'
                for i in range(len(metrics)))
            out.append(f'<tr><th scope="row">{_esc(uid)}</th>{cells}</tr>')
    else:
        empty = "".join('<td class="num">&mdash;</td>' for _ in metrics)
        out.append(f'<tr><th scope="row">(no eligible candidate)</th>{empty}</tr>')
    out.append("</tbody></table>")
    return "\n".join(out)


def _eligibility_html(p):
    """Eligibility verdict table (unit, eligible yes/no, reason)."""
    out = ["<h2>Eligibility</h2>"]
    elig = p.get("eligibility", {}) or {}
    if not elig:
        out.append('<p class="note">No eligibility records in package.</p>')
        return "\n".join(out)
    out.append("<table><thead><tr><th scope='col'>unit</th><th scope='col'>eligible</th>"
               "<th scope='col'>reason</th></tr></thead><tbody>")
    for uid in sorted(elig):
        e = elig[uid] or {}
        out.append(f"<tr><th scope='row'>{_esc(uid)}</th>"
                   f"<td>{'yes' if e.get('eligible') else 'no'}</td>"
                   f"<td>{_esc(e.get('reason', ''))}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _uncertainty_html(p):
    """Uncertainty section. Returns '' when the package carries no bootstrap, so
    the section appears ONLY when a bootstrap was actually run."""
    boot = p.get("bootstrap")
    if not boot:
        return ""
    out = ["<h2>Uncertainty</h2>"]
    method = boot.get("method", "independent")
    if method == "block":
        how = (f"spatial moving-block bootstrap, block size {_num(boot.get('block'))} "
               "aggregated pixels, which preserves spatial autocorrelation (honest, "
               "typically wider CIs)")
    else:
        how = ("independent-pixel bootstrap, which resamples pixels independently "
               "(optimistic / lower-bound CIs)")
    out.append(f"<p>Resampling method: <strong>{_esc(method)}</strong> &mdash; {how}; "
               f"n = {_num(boot.get('n_boot'))} resamples, seed {_num(boot.get('seed'))}.</p>")
    if boot.get("note"):
        out.append(f"<blockquote class='note'>{_esc(boot['note'])}</blockquote>")
    out.append(f"<p>A single clear winner emerged in "
               f"<strong>{_pct(boot.get('decisive_freq'))}</strong> of resamples.</p>")
    bunits = boot.get("units", {}) or {}
    if bunits:
        out.append("<table><thead><tr><th scope='col'>unit</th>"
                   "<th scope='col'>nondominated_freq</th>"
                   "<th scope='col'>clear_winner_freq</th>"
                   "<th scope='col'>distance CI per feature [lo, med, hi]</th>"
                   "</tr></thead><tbody>")
        for uid in sorted(bunits):
            u = bunits[uid] or {}
            ci = u.get("distance_ci", {}) or {}
            parts = []
            for feat in sorted(ci):
                vals = (list(ci[feat] or []) + [None, None, None])[:3]
                parts.append(f"{_esc(feat)}: [{_num(vals[0])}, {_num(vals[1])}, "
                             f"{_num(vals[2])}]")
            out.append(f"<tr><th scope='row'>{_esc(uid)}</th>"
                       f"<td class='num'>{_pct(u.get('nondominated_freq'))}</td>"
                       f"<td class='num'>{_pct(u.get('clear_winner_freq'))}</td>"
                       f"<td>{'; '.join(parts) or 'n/a'}</td></tr>")
        out.append("</tbody></table>")
    return "\n".join(out)


def _sensitivity_html(p):
    """Sensitivity section: max pairwise flip + any pair above the 0.1 threshold."""
    out = ["<h2>Sensitivity (scenario rank-flips)</h2>"]
    scen = p.get("scenario_names", []) or []
    if scen:
        out.append(f"<p>Declared sensitivity scenarios: {_codes(scen)}.</p>")
    flips = p.get("pairwise_flip_matrix", {}) or {}
    if not flips:
        out.append("<p class='note'>No pairwise sensitivity matrix (fewer than two "
                   "comparable candidates or scenarios).</p>")
        return "\n".join(out)
    max_val = max(flips.values())
    max_pair = sorted(k for k, v in flips.items() if v == max_val)[0]
    out.append(f"<p>Maximum pairwise rank-flip: <strong>{_num(max_val)}</strong> "
               f"(pair <code>{_esc(max_pair)}</code>). A pair flips when the sign of its "
               f"per-axis distance difference changes between scenarios; a recommendation "
               f"is declared stable only when every flip stays at or below 0.1.</p>")
    unstable = sorted((k for k, v in flips.items() if v > 0.1),
                      key=lambda k: (-flips[k], k))
    if not unstable:
        out.append("<p class='note'>No pair exceeds the 0.1 stability threshold.</p>")
        return "\n".join(out)
    out.append("<p>Pairs above the 0.1 stability threshold:</p>")
    out.append("<table><thead><tr><th scope='col'>pair</th>"
               "<th scope='col'>flip fraction</th></tr></thead><tbody>")
    for k in unstable:
        out.append(f"<tr><th scope='row'>{_esc(k)}</th>"
                   f"<td class='num'>{_num(flips[k])}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _ledger_html(p):
    """Transfer-gap ledger table + draft study-protocol summary."""
    out = ["<h2>Transfer-gap ledger</h2>"]
    ledger = p.get("transfer_gap_ledger", {}) or {}
    if ledger.get("note"):
        out.append(f"<blockquote class='note'>{_esc(ledger['note'])}</blockquote>")
    gap_rows = ledger.get("gaps", []) or []
    if gap_rows:
        out.append("<table><thead><tr><th scope='col'>category</th><th scope='col'>class</th>"
                   "<th scope='col'>established at this support</th>"
                   "<th scope='col'>prohibited</th></tr></thead><tbody>")
        for g in gap_rows:
            out.append(f"<tr><th scope='row'>{_esc(g.get('category'))}</th>"
                       f"<td>{_esc(g.get('class'))}</td>"
                       f"<td>{_esc(g.get('statement'))}</td>"
                       f"<td>{_esc(g.get('prohibited'))}</td></tr>")
        out.append("</tbody></table>")
    proto = p.get("draft_protocol", {}) or {}
    if proto:
        out.append("<h3>Draft study protocol</h3><ul class='proto'>")
        out.append(f"<li><strong>Status:</strong> {_esc(proto.get('status', 'draft'))} "
                   f"({_esc(proto.get('authorization', ''))})</li>")
        if proto.get("objective"):
            out.append(f"<li><strong>Objective:</strong> {_esc(proto['objective'])}</li>")
        if proto.get("hypothesis"):
            out.append(f"<li><strong>Hypothesis:</strong> {_esc(proto['hypothesis'])}</li>")
        for label, key in (("Measurements required next", "measurements_required_next"),
                           ("Acceptance criteria", "acceptance_criteria"),
                           ("Rejection criteria", "rejection_criteria"),
                           ("Stop conditions", "stop_conditions")):
            items = proto.get(key) or []
            if items:
                out.append(f"<li><strong>{_esc(label)}:</strong><ul>")
                for it in items:
                    out.append(f"<li>{_esc(it)}</li>")
                out.append("</ul></li>")
        if proto.get("transfer_boundary"):
            out.append(f"<li><strong>Transfer boundary:</strong> "
                       f"{_esc(proto['transfer_boundary'])}</li>")
        out.append("</ul>")
    return "\n".join(out)


def _provenance_html(p, profile):
    """Provenance appendix table + optional extended / geomorphic descriptor
    tables + the closing scope-bound footer."""
    out = ["<h2>Provenance appendix</h2>", "<table><tbody>"]
    rows = (("schema_version", _esc(p.get("schema_version"))),
            ("source_label", _esc(profile.get("source_label"))),
            ("target_body", _esc(profile.get("target_body"))),
            ("target_support_m", _num(profile.get("target_support_m"))),
            ("decision_metrics", _esc(profile.get("decision_metrics"))))
    for key, val in rows:
        out.append(f"<tr><th scope='row'>{key}</th><td>{val}</td></tr>")
    out.append(f"<tr><th scope='row'>package_hash</th>"
               f"<td class='mono'>{_esc(p.get('package_hash'))}</td></tr>")
    out.append("</tbody></table>")
    ext = _metric_table_html(
        "Extended metrics", p.get("extended_metrics"),
        "Reported for transparency; included in the decision only when axes = extended.")
    if ext:
        out.append(ext)
    geo = _metric_table_html(
        "Geomorphic descriptors", p.get("geomorphic_metrics"),
        "Reported for transparency; included in the decision only when axes = geomorphic.")
    if geo:
        out.append(geo)
    out.append("<hr>")
    out.append(f"<p class='foot'>Generated by the TerraTrace HTML report module "
               f"(schema {_esc(p.get('schema_version', 'n/a'))}). Every statement above is "
               f"bounded by the scope / claim-firewall and the transfer-gap ledger "
               f"reproduced from the package; nothing here widens them. Not an official "
               f"NASA submission artifact. Not NASA-endorsed.</p>")
    return "\n".join(out)


def study_report_html(package):
    """Render a study package as a complete, self-contained HTML document (str).

    Robust to missing optional keys (bootstrap, geomorphic_metrics, frontier) via
    ``.get``. Mirrors the sections of :func:`terratrace.report.study_report_md`;
    the claim firewall, transfer-gap ledger, and draft protocol are reproduced
    from the package exactly as emitted and are never widened here.
    """
    p = package or {}
    profile = p.get("profile", {}) or {}
    metrics = list(profile.get("metrics", []) or [])
    body = str(profile.get("target_body", "target")).title()
    dm = _esc(profile.get("decision_metrics", "core"))
    out = []
    w = out.append
    w("<!DOCTYPE html>")
    w('<html lang="en"><head><meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width,initial-scale=1">')
    w(f"<title>TerraTrace Morphology-Screening Report - {_esc(body)} vs Earth</title>")
    w(f"<style>{CSS}</style></head>")
    w('<body><main class="wrap">')
    w('<p class="eyebrow">Planetary Analog OS / TerraTrace</p>')
    w(f"<h1>TerraTrace Morphology-Screening Report &mdash; {_esc(body)} vs Earth</h1>")
    w(f'<p class="meta">Task <code>{_esc(profile.get("task", "n/a"))}</code>, common '
      f"support {_num(profile.get('target_support_m'))} m, decision axes <code>{dm}</code>, "
      f"claim maturity <code>{_esc(profile.get('claim_maturity', 'n/a'))}</code>.</p>")
    w(_firewall_html(p))
    w('<h2>Result</h2><div class="result">')
    state = p.get("result_state", "n/a")
    rec = p.get("recommended_unit")
    w(f'<p><strong>Result state:</strong> <code>{_esc(state)}</code> &mdash; '
      f"{_esc(_STATE_PLAIN.get(state, 'see the sections below.'))}</p>")
    if rec:
        w(f'<p><strong>Recommended unit:</strong> <code>{_esc(rec)}</code> &mdash; the '
          "single most-promising morphology analog for a follow-up study (a screening "
          "recommendation, not an endorsement).</p>")
    else:
        w("<p><strong>Recommended unit:</strong> no single recommendation "
          "(the evidence does not isolate one candidate).</p>")
    w("</div>")
    w(_decision_html(p, profile, metrics, dm))
    w(_eligibility_html(p))
    w(_uncertainty_html(p))
    w(_sensitivity_html(p))
    w(_ledger_html(p))
    w(_provenance_html(p, profile))
    w("</main></body></html>")
    return "\n".join(out) + "\n"


def _batch_percandidate_html(r, cands):
    """Per-candidate robustness table for the batch report."""
    out = ["<h2>Per-candidate robustness</h2>"]
    per = r.get("per_candidate", {}) or {}
    if not per:
        out.append("<p class='note'>No per-candidate synthesis in report.</p>")
        return "\n".join(out)
    out.append("<table><thead><tr><th scope='col'>candidate</th>"
               "<th scope='col'>layer1_frequency</th>"
               "<th scope='col'>recommended_frequency</th>"
               "<th scope='col'>mean_layer</th>"
               "<th scope='col'>cells_ranked</th></tr></thead><tbody>")
    for c in (cands or sorted(per)):
        pc = per.get(c, {}) or {}
        out.append(f"<tr><th scope='row'>{_esc(c)}</th>"
                   f"<td class='num'>{_pct(pc.get('layer1_frequency'))}</td>"
                   f"<td class='num'>{_pct(pc.get('recommended_frequency'))}</td>"
                   f"<td class='num'>{_num(pc.get('mean_layer'))}</td>"
                   f"<td class='num'>{_esc(pc.get('cells_ranked'))}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _batch_cells_html(r):
    """The (reference x mode) cell grid table for the batch report."""
    out = ["<h2>Cell grid (reference &times; mode)</h2>"]
    cells = r.get("cells", []) or []
    if not cells:
        out.append("<p class='note'>No cells in report.</p>")
        return "\n".join(out)
    out.append("<table><thead><tr><th scope='col'>reference</th><th scope='col'>mode</th>"
               "<th scope='col'>result_state</th><th scope='col'>recommended_unit</th>"
               "</tr></thead><tbody>")
    for cell in cells:
        rec = cell.get("recommended_unit")
        out.append(f"<tr><th scope='row'>{_esc(cell.get('reference'))}</th>"
                   f"<td>{_esc(cell.get('mode'))}</td>"
                   f"<td><code>{_esc(cell.get('result_state'))}</code></td>"
                   f"<td>{_esc(rec) if rec is not None else '&mdash;'}</td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def batch_report_html(report):
    """Render a cross-reference batch report (:func:`terratrace.batch.run_batch`)
    as a complete, self-contained HTML document (str). Mirrors the sections of
    :func:`terratrace.report.batch_report_md`. Escaped and deterministic.
    """
    r = report or {}
    refs = r.get("references", []) or []
    cands = r.get("candidates", []) or []
    modes = r.get("decision_modes", []) or []
    suite = r.get("suite", "terratrace-batch")
    out = []
    w = out.append
    w("<!DOCTYPE html>")
    w('<html lang="en"><head><meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width,initial-scale=1">')
    w(f"<title>TerraTrace Cross-Reference Batch Report - {_esc(suite)}</title>")
    w(f"<style>{CSS}</style></head>")
    w('<body><main class="wrap">')
    w('<p class="eyebrow">Planetary Analog OS / TerraTrace</p>')
    w(f"<h1>TerraTrace Cross-Reference Batch Report &mdash; {_esc(suite)}</h1>")
    w(f'<p class="meta">References {_codes(refs)}, candidates {_codes(cands)}, decision '
      f"modes {_codes(modes)}, over {_esc(r.get('n_cells', 'n/a'))} cells "
      f"(references &times; modes).</p>")
    w('<div class="firewall"><strong>SCOPE / CLAIM-FIREWALL</strong>'
      "<p>This is a transparent robustness synthesis over map-scale terrain "
      "<strong>morphology only</strong>, NOT a composite &ldquo;Mars-likeness&rdquo; "
      "score. <code>layer1_frequency</code> is the fraction of (reference &times; "
      "decision-mode) cells in which a candidate is Pareto non-dominated; "
      "<code>consensus_shortlist</code> lists candidates non-dominated in EVERY cell. "
      "No traversability, geologic, access, or mission claim is implied.</p></div>")
    w(_batch_percandidate_html(r, cands))
    w("<h2>Consensus and ordering</h2><ul>")
    w(f"<li><strong>consensus_shortlist</strong> (non-dominated in EVERY reference "
      f"&times; mode cell): {_codes(r.get('consensus_shortlist', []))}</li>")
    w(f"<li><strong>robust_ordering</strong> (most-often non-dominated first): "
      f"{_codes(r.get('robust_ordering', []))}</li></ul>")
    w(_batch_cells_html(r))
    if r.get("note"):
        w(f"<h2>Note</h2><blockquote class='note'>{_esc(r['note'])}</blockquote>")
    w("<h2>Provenance</h2>")
    w(f"<p class='meta'>Package hash: <span class='mono'>{_esc(r.get('package_hash'))}"
      "</span></p><hr>")
    w("<p class='foot'>Generated by the TerraTrace HTML report module. Robustness "
      "synthesis only; the engine's map-scale-morphology claim firewall applies to every "
      "cell. Not an official NASA submission artifact. Not NASA-endorsed.</p>")
    w("</main></body></html>")
    return "\n".join(out) + "\n"


def write_html(html_str, path):
    """Write `html_str` to `path` as UTF-8, creating parent dirs. Returns `path`."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_str)
    return path

