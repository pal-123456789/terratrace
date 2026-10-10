"""Publication-grade Markdown reporting for TerraTrace packages.

This module turns a study package (:func:`terratrace.study.compare_units` /
``run_study``) or a cross-reference batch report (:func:`terratrace.batch.run_batch`)
into a single, citable, provenance-complete Markdown document.

The map-scale-morphology CLAIM FIREWALL is reproduced *verbatim* from the package
itself -- the prohibited-claims list, the transfer-gap ledger, and the draft
protocol are rendered exactly as the engine emitted them. This renderer never
widens, softens, re-weights, or invents a claim; it only presents what the
engine already decided, so the document inherits the engine's scientific
boundary (morphology screening only -- no traversability, autonomy, geologic
equivalence, site access, or mission readiness).

Pure standard library: no third-party imports, no network, no formats beyond
Markdown text. :func:`write_report` is the only function that touches disk.
"""
from __future__ import annotations

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
def _num(x, sig=4):
    """Format a scalar to ~`sig` significant figures; robust to None/NaN/inf/str."""
    if x is None:
        return "n/a"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(xf):
        return "nan"
    if math.isinf(xf):
        return "inf" if xf > 0 else "-inf"
    return f"{xf:.{sig}g}"


def _pct(x):
    """Format a [0, 1] frequency as a percentage; robust to None/NaN/str."""
    if x is None:
        return "n/a"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(xf):
        return "nan"
    return f"{xf * 100:.1f}%"


def _cell(s):
    """Make a value safe for a single Markdown table cell."""
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ")


def _codes(seq):
    """Render a sequence as a comma-separated list of inline-code tokens."""
    items = [f"`{x}`" for x in (seq or [])]
    return ", ".join(items) if items else "(none)"
def _append_metric_table(w, title, metric_map):
    """Append a '### title' + per-unit table for an optional {uid: {k: v}} map."""
    if not metric_map:
        return
    subkeys = []
    for uid in metric_map:
        for k in (metric_map[uid] or {}):
            if k not in subkeys:
                subkeys.append(k)
    subkeys = sorted(subkeys)
    w(f"### {title}")
    w("")
    if not subkeys:
        w("_(no descriptor values)_")
        w("")
        return
    w("| unit | " + " | ".join(_cell(k) for k in subkeys) + " |")
    w("| --- | " + " | ".join("---:" for _ in subkeys) + " |")
    for uid in sorted(metric_map):
        row = metric_map[uid] or {}
        w(f"| {_cell(uid)} | " + " | ".join(_num(row.get(k)) for k in subkeys) + " |")
    w("")


def study_report_md(package):
    """Render a study package as a publication-grade Markdown report (str).

    Robust to missing optional keys (bootstrap, geomorphic_metrics, frontier) via
    ``.get``. The claim firewall, transfer-gap ledger, and draft protocol are
    reproduced from the package exactly as emitted; nothing is widened here.
    """
    p = package or {}
    profile = p.get("profile", {}) or {}
    metrics = list(profile.get("metrics", []) or [])
    out = []
    w = out.append

    # 1. Title + SCOPE / CLAIM-FIREWALL --------------------------------------
    body = str(profile.get("target_body", "target")).title()
    w(f"# TerraTrace Morphology-Screening Report - {body} vs Earth")
    w("")
    w(f"Task `{profile.get('task', 'n/a')}`, common support "
      f"{_num(profile.get('target_support_m'))} m, decision axes "
      f"`{profile.get('decision_metrics', 'core')}`, claim maturity "
      f"`{profile.get('claim_maturity', 'n/a')}`.")
    w("")
    w("> **SCOPE / CLAIM-FIREWALL**")
    w("> ")
    w("> This report screens **map-scale terrain morphology only** at the declared "
      "common support. It is NOT a rover-traversability, autonomy, geologic-equivalence, "
      "site-access, or mission-readiness result. The following claims are **prohibited** "
      "and are reproduced verbatim from the package; they bind every statement below:")
    w("> ")
    for claim in p.get("prohibited_claims", []) or []:
        w(f"> - {claim}")
    w("")

    # 2. Result --------------------------------------------------------------
    w("## Result")
    w("")
    state = p.get("result_state", "n/a")
    rec = p.get("recommended_unit")
    w(f"- **Result state:** `{state}` - {_STATE_PLAIN.get(state, 'see the sections below.')}")
    if rec:
        w(f"- **Recommended unit:** `{rec}` - the single most-promising morphology "
          "analog for a follow-up study (a screening recommendation, not an endorsement).")
    else:
        w("- **Recommended unit:** no single recommendation "
          "(the evidence does not isolate one candidate).")
    w("")

    # 3. Decision ------------------------------------------------------------
    w("## Decision")
    w("")
    w(f"Per-axis morphology distance from each candidate to the reference on the "
      f"`{profile.get('decision_metrics', 'core')}` decision axes. **Lower = closer** "
      f"to the reference on that axis. Candidates are compared by Pareto dominance "
      f"across all axes jointly: there is **no composite \"Mars-likeness\" score** and "
      f"no axis weighting.")
    w("")
    vectors = p.get("baseline_vectors", {}) or {}
    if metrics:
        w("| candidate | " + " | ".join(_cell(m) for m in metrics) + " |")
        w("| --- | " + " | ".join("---:" for _ in metrics) + " |")
        if vectors:
            for uid in sorted(vectors):
                vec = vectors[uid] or []
                cells = [(_num(vec[i]) if i < len(vec) else "n/a") for i in range(len(metrics))]
                w(f"| {_cell(uid)} | " + " | ".join(cells) + " |")
        else:
            w("| _(no eligible candidate)_ | " + " | ".join("-" for _ in metrics) + " |")
    else:
        w("_No decision axes declared._")
    w("")
    # 4. Eligibility ---------------------------------------------------------
    w("## Eligibility")
    w("")
    elig = p.get("eligibility", {}) or {}
    if elig:
        w("| unit | eligible | reason |")
        w("| --- | :---: | --- |")
        for uid in sorted(elig):
            e = elig[uid] or {}
            w(f"| {_cell(uid)} | {'yes' if e.get('eligible') else 'no'} | "
              f"{_cell(e.get('reason', ''))} |")
    else:
        w("_No eligibility records in package._")
    w("")

    # 5. Uncertainty (present ONLY when a bootstrap was run) -----------------
    boot = p.get("bootstrap")
    if boot:
        w("## Uncertainty")
        w("")
        method = boot.get("method", "independent")
        if method == "block":
            how = (f"spatial moving-block bootstrap, block size {_num(boot.get('block'))} "
                   f"aggregated pixels, which preserves spatial autocorrelation (honest, "
                   f"typically wider CIs)")
        else:
            how = ("independent-pixel bootstrap, which resamples pixels independently "
                   "(optimistic / lower-bound CIs)")
        w(f"Resampling method: **{method}** - {how}; n = {_num(boot.get('n_boot'))} "
          f"resamples, seed {_num(boot.get('seed'))}.")
        if boot.get("note"):
            w("")
            w(f"> {boot['note']}")
        w("")
        w(f"A single clear winner emerged in **{_pct(boot.get('decisive_freq'))}** of resamples.")
        w("")
        bunits = boot.get("units", {}) or {}
        if bunits:
            w("| unit | nondominated_freq | clear_winner_freq | "
              "distance CI per feature [lo, med, hi] |")
            w("| --- | ---: | ---: | --- |")
            for uid in sorted(bunits):
                u = bunits[uid] or {}
                ci = u.get("distance_ci", {}) or {}
                parts = []
                for feat in sorted(ci):
                    vals = (list(ci[feat] or []) + [None, None, None])[:3]
                    parts.append(f"{feat}: [{_num(vals[0])}, {_num(vals[1])}, {_num(vals[2])}]")
                w(f"| {_cell(uid)} | {_pct(u.get('nondominated_freq'))} | "
                  f"{_pct(u.get('clear_winner_freq'))} | {_cell('; '.join(parts) or 'n/a')} |")
        w("")
    # 6. Sensitivity ---------------------------------------------------------
    w("## Sensitivity (scenario rank-flips)")
    w("")
    scen = p.get("scenario_names", []) or []
    if scen:
        w(f"Declared sensitivity scenarios: {_codes(scen)}.")
        w("")
    flips = p.get("pairwise_flip_matrix", {}) or {}
    if flips:
        max_val = max(flips.values())
        max_pair = sorted(k for k, v in flips.items() if v == max_val)[0]
        w(f"Maximum pairwise rank-flip: **{_num(max_val)}** (pair `{_cell(max_pair)}`). "
          f"A pair flips when the sign of its per-axis distance difference changes "
          f"between scenarios; a recommendation is declared stable only when every flip "
          f"stays at or below 0.1.")
        w("")
        unstable = sorted((k for k, v in flips.items() if v > 0.1),
                          key=lambda k: (-flips[k], k))
        if unstable:
            w("Pairs above the 0.1 stability threshold:")
            w("")
            w("| pair | flip fraction |")
            w("| --- | ---: |")
            for k in unstable:
                w(f"| {_cell(k)} | {_num(flips[k])} |")
        else:
            w("No pair exceeds the 0.1 stability threshold.")
    else:
        w("_No pairwise sensitivity matrix (fewer than two comparable candidates "
          "or scenarios)._")
    w("")

    # 7. Transfer-gap ledger + draft protocol --------------------------------
    w("## Transfer-gap ledger")
    w("")
    ledger = p.get("transfer_gap_ledger", {}) or {}
    if ledger.get("note"):
        w(f"> {ledger['note']}")
        w("")
    gap_rows = ledger.get("gaps", []) or []
    if gap_rows:
        w("| category | class | established at this support | prohibited |")
        w("| --- | :---: | --- | --- |")
        for g in gap_rows:
            w(f"| {_cell(g.get('category'))} | {_cell(g.get('class'))} | "
              f"{_cell(g.get('statement'))} | {_cell(g.get('prohibited'))} |")
        w("")
    proto = p.get("draft_protocol", {}) or {}
    if proto:
        w("### Draft study protocol")
        w("")
        w(f"- **Status:** {_cell(proto.get('status', 'draft'))} "
          f"({_cell(proto.get('authorization', ''))})")
        if proto.get("objective"):
            w(f"- **Objective:** {_cell(proto['objective'])}")
        if proto.get("hypothesis"):
            w(f"- **Hypothesis:** {_cell(proto['hypothesis'])}")
        for label, key in (("Measurements required next", "measurements_required_next"),
                           ("Acceptance criteria", "acceptance_criteria"),
                           ("Rejection criteria", "rejection_criteria"),
                           ("Stop conditions", "stop_conditions")):
            items = proto.get(key) or []
            if items:
                w(f"- **{label}:**")
                for it in items:
                    w(f"    - {_cell(it)}")
        if proto.get("transfer_boundary"):
            w(f"- **Transfer boundary:** {_cell(proto['transfer_boundary'])}")
        w("")

    # 8. Provenance appendix -------------------------------------------------
    w("## Provenance appendix")
    w("")
    w("| field | value |")
    w("| --- | --- |")
    w(f"| schema_version | {_cell(p.get('schema_version'))} |")
    w(f"| source_label | {_cell(profile.get('source_label'))} |")
    w(f"| target_body | {_cell(profile.get('target_body'))} |")
    w(f"| target_support_m | {_num(profile.get('target_support_m'))} |")
    w(f"| decision_metrics | {_cell(profile.get('decision_metrics'))} |")
    w(f"| package_hash | `{_cell(p.get('package_hash'))}` |")
    w("")
    _append_metric_table(w, "Extended metrics", p.get("extended_metrics"))
    _append_metric_table(w, "Geomorphic descriptors", p.get("geomorphic_metrics"))
    w("---")
    w(f"_Generated by the TerraTrace report module (schema "
      f"{_cell(p.get('schema_version', 'n/a'))}). Every statement above is bounded by the "
      f"scope / claim-firewall and the transfer-gap ledger reproduced from the package; "
      f"nothing here widens them._")
    return "\n".join(out) + "\n"
def batch_report_md(report):
    """Render a cross-reference batch report (batch.run_batch) as Markdown (str)."""
    r = report or {}
    out = []
    w = out.append
    refs = r.get("references", []) or []
    cands = r.get("candidates", []) or []
    modes = r.get("decision_modes", []) or []

    w(f"# TerraTrace Cross-Reference Batch Report - {_cell(r.get('suite', 'terratrace-batch'))}")
    w("")
    w(f"References {_codes(refs)}, candidates {_codes(cands)}, decision modes "
      f"{_codes(modes)}, over {r.get('n_cells', 'n/a')} cells (references x modes).")
    w("")
    w("> **SCOPE / CLAIM-FIREWALL** - This is a transparent robustness synthesis over "
      "map-scale terrain **morphology only**, NOT a composite \"Mars-likeness\" score. "
      "`layer1_frequency` is the fraction of (reference x decision-mode) cells in which a "
      "candidate is Pareto non-dominated; `consensus_shortlist` lists candidates "
      "non-dominated in EVERY cell. No traversability, geologic, access, or mission claim "
      "is implied.")
    w("")

    w("## Per-candidate robustness")
    w("")
    per = r.get("per_candidate", {}) or {}
    if per:
        w("| candidate | layer1_frequency | recommended_frequency | mean_layer | cells_ranked |")
        w("| --- | ---: | ---: | ---: | ---: |")
        for c in (cands or sorted(per)):
            pc = per.get(c, {}) or {}
            w(f"| {_cell(c)} | {_pct(pc.get('layer1_frequency'))} | "
              f"{_pct(pc.get('recommended_frequency'))} | {_num(pc.get('mean_layer'))} | "
              f"{_cell(pc.get('cells_ranked'))} |")
    else:
        w("_No per-candidate synthesis in report._")
    w("")

    w("## Consensus and ordering")
    w("")
    cons = r.get("consensus_shortlist", []) or []
    w(f"- **consensus_shortlist** (non-dominated in EVERY reference x mode cell): "
      f"{_codes(cons)}")
    w(f"- **robust_ordering** (most-often non-dominated first): "
      f"{_codes(r.get('robust_ordering', []))}")
    w("")

    w("## Cell grid (reference x mode)")
    w("")
    cells = r.get("cells", []) or []
    if cells:
        w("| reference | mode | result_state | recommended_unit |")
        w("| --- | --- | --- | --- |")
        for cell in cells:
            rec = cell.get("recommended_unit")
            w(f"| {_cell(cell.get('reference'))} | {_cell(cell.get('mode'))} | "
              f"`{_cell(cell.get('result_state'))}` | {_cell(rec if rec is not None else '-')} |")
    else:
        w("_No cells in report._")
    w("")

    if r.get("note"):
        w("## Note")
        w("")
        w(f"> {r['note']}")
        w("")

    w("## Provenance")
    w("")
    w(f"- **package_hash:** `{_cell(r.get('package_hash'))}`")
    w("")
    w("---")
    w("_Generated by the TerraTrace report module. Robustness synthesis only; the "
      "engine's map-scale-morphology claim firewall applies to every cell._")
    return "\n".join(out) + "\n"


def write_report(markdown, path):
    """Write `markdown` to `path` as UTF-8, creating parent dirs. Returns `path`."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(markdown)
    return path







