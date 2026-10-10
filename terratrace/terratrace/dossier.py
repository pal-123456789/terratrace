"""Per-candidate site dossier for a TerraTrace study package.

A study package (:func:`terratrace.study.compare_units` / ``run_study``)
summarises every unit at once. This module produces the per-CANDIDATE analogue:
a focused decision brief for ONE unit that gathers, in a single place,
everything the package already knows about it -- its per-metric morphology
distances to the reference, its Pareto-frontier layer, its eligibility verdict,
its bootstrap non-domination / clear-winner frequencies and distance CIs (when a
bootstrap was run), whether it is THE recommendation, and the transfer-gap ledger
+ prohibited claims that bind it.

CLAIM FIREWALL: this is map-scale terrain MORPHOLOGY screening only, at the
package's declared common support. A dossier is NOT a rover-traversability,
autonomy, geologic-equivalence, site-access, or mission-readiness result. The
prohibited-claims list and transfer-gap ledger are reproduced from the package
exactly as the engine emitted them; nothing here widens, softens, re-weights, or
invents a claim -- it only re-presents, per candidate, what the engine already
decided.

Pure standard library: no third-party imports, no network, no disk access.
"""
from __future__ import annotations

import math


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


def candidate_dossier(package, unit_id):
    """Structured decision brief for ONE unit, assembled from a study package.

    Returns a dict keyed by ``unit``, ``target_body``, ``decision_metrics``,
    ``is_recommended``, ``result_state``, ``eligible``, ``eligibility_reason``,
    ``distances`` ({metric: value}, from zipping ``profile["metrics"]`` with
    ``baseline_vectors[unit_id]`` when the unit is eligible and has a baseline
    vector, else ``{}``), ``frontier_layer`` (its Pareto layer from
    ``frontier["rank"]`` or ``None``), ``uncertainty`` (bootstrap non-domination /
    clear-winner frequencies, distance CIs and method, or ``None``),
    ``transfer_gaps`` (the ledger), ``prohibited_claims`` (the list) and
    ``package_hash``.

    A missing / ineligible unit yields ``eligible=False``, ``distances={}``,
    ``frontier_layer=None`` and ``uncertainty=None`` WITHOUT raising. A ``KeyError``
    is raised only when ``unit_id`` is in neither ``baseline_vectors`` nor
    ``eligibility`` (a truly unknown unit).
    """
    p = package or {}
    profile = p.get("profile", {}) or {}
    metrics = list(profile.get("metrics", []) or [])
    baseline = p.get("baseline_vectors", {}) or {}
    eligibility = p.get("eligibility", {}) or {}

    in_base = unit_id in baseline
    elig_entry = eligibility.get(unit_id)
    if elig_entry is None and not in_base:
        raise KeyError(
            f"unit {unit_id!r} is in neither baseline_vectors nor eligibility of "
            f"this package (truly unknown unit)")

    if elig_entry is not None:
        eligible = bool(elig_entry.get("eligible", False))
        eligibility_reason = str(elig_entry.get("reason", "") or "")
    else:
        # A baseline vector exists only for eligible candidates, so a unit that is
        # in baseline_vectors but carries no eligibility record is eligible.
        eligible, eligibility_reason = True, ""

    vec = baseline.get(unit_id)
    if eligible and vec is not None:
        distances = {m: float(x) for m, x in zip(metrics, vec)}
    else:
        distances = {}

    frontier_rank = (p.get("frontier") or {}).get("rank", {}) or {}
    frontier_layer = frontier_rank.get(unit_id)
    if frontier_layer is not None:
        frontier_layer = int(frontier_layer)

    boot = p.get("bootstrap") or {}
    bunit = (boot.get("units") or {}).get(unit_id)
    if bunit is not None:
        uncertainty = {
            "nondominated_freq": bunit.get("nondominated_freq"),
            "clear_winner_freq": bunit.get("clear_winner_freq"),
            "distance_ci": bunit.get("distance_ci", {}) or {},
            "method": boot.get("method", "independent"),
        }
    else:
        uncertainty = None

    return {
        "unit": unit_id,
        "target_body": profile.get("target_body"),
        "decision_metrics": profile.get("decision_metrics", "core"),
        "is_recommended": p.get("recommended_unit") == unit_id,
        "result_state": p.get("result_state"),
        "eligible": eligible,
        "eligibility_reason": eligibility_reason,
        "distances": distances,
        "frontier_layer": frontier_layer,
        "uncertainty": uncertainty,
        "transfer_gaps": p.get("transfer_gap_ledger", {}) or {},
        "prohibited_claims": list(p.get("prohibited_claims", []) or []),
        "package_hash": p.get("package_hash"),
    }


def all_dossiers(package):
    """Return ``{unit_id: candidate_dossier(package, unit_id)}`` for every unit in
    the package's eligibility map (the reference and every candidate, eligible or
    not), so a batch of per-candidate briefs can be produced in one call."""
    p = package or {}
    eligibility = p.get("eligibility", {}) or {}
    return {uid: candidate_dossier(p, uid) for uid in eligibility}


def dossier_md(package, unit_id):
    """Render :func:`candidate_dossier` as a focused Markdown decision brief (str).

    Title (unit id + target body), a one-line verdict (recommended / eligible but
    not the sole recommendation / blocked with reason), a per-axis distance table
    (lower = closer to the reference), the Pareto-frontier layer, an uncertainty
    block when a bootstrap was run, and the transfer-gap ledger + prohibited claims
    reproduced from the package. Numbers are formatted to ~4 significant figures;
    nothing here widens the engine's claims.
    """
    d = candidate_dossier(package, unit_id)
    p = package or {}
    profile = p.get("profile", {}) or {}
    metrics = list(profile.get("metrics", []) or [])
    body = str(d.get("target_body") or "target").title()
    out = []
    w = out.append

    # Title + scope -----------------------------------------------------------
    w(f"# Site Dossier - `{unit_id}` vs {body}")
    w("")
    w(f"Decision axes `{d.get('decision_metrics', 'core')}`, result state "
      f"`{d.get('result_state', 'n/a')}`. Map-scale terrain **morphology screening "
      f"only**: not a traversability, autonomy, geologic-equivalence, site-access, "
      f"or mission-readiness result.")
    w("")

    # Verdict (one line) ------------------------------------------------------
    if d["is_recommended"]:
        verdict = ("**recommended** - this candidate is the single most-promising "
                   "morphology analog for a follow-up study (a screening "
                   "recommendation, not an endorsement).")
    elif d["eligible"]:
        verdict = ("**eligible, but not the sole recommendation** - it is comparable "
                   "at this support, yet the evidence does not isolate it as the one "
                   "analog.")
    else:
        reason = d["eligibility_reason"] or "ineligible"
        verdict = f"**blocked** - excluded from comparison: {reason}."
    w(f"**Verdict:** {verdict}")
    w("")

    # Morphology distances ----------------------------------------------------
    w("## Morphology distances to the reference")
    w("")
    w("Per-axis normalized distance from this candidate to the reference. "
      "**Lower = closer** to the reference on that axis. There is no composite "
      "score and no axis weighting.")
    w("")
    distances = d["distances"]
    w("| axis | distance to reference |")
    w("| --- | ---: |")
    if metrics:
        for m in metrics:
            w(f"| {_cell(m)} | {_num(distances.get(m))} |")
    elif distances:
        for m in sorted(distances):
            w(f"| {_cell(m)} | {_num(distances[m])} |")
    else:
        w("| _(no comparable distances)_ | n/a |")
    w("")

    # Pareto frontier ---------------------------------------------------------
    w("## Pareto frontier")
    w("")
    layer = d["frontier_layer"]
    if layer is not None:
        w(f"- **Frontier layer:** {layer} (layer 1 = non-dominated / best; layer "
          "membership is the ranking and within-layer order carries no score).")
    else:
        w("- **Frontier layer:** not placed (ineligible, no baseline vector, or "
          "fewer than two comparable candidates).")
    w("")

    # Uncertainty (present ONLY when a bootstrap was run) ---------------------
    unc = d["uncertainty"]
    if unc:
        method = unc.get("method", "independent")
        w(f"## Uncertainty ({_cell(method)} bootstrap)")
        w("")
        w(f"- Non-dominated in **{_pct(unc.get('nondominated_freq'))}** of resamples.")
        w(f"- The single clear winner in **{_pct(unc.get('clear_winner_freq'))}** "
          "of resamples.")
        w("")
        ci = unc.get("distance_ci", {}) or {}
        if ci:
            w("Distance confidence intervals (percentiles across resamples):")
            w("")
            w("| axis | 2.5% | 50% | 97.5% |")
            w("| --- | ---: | ---: | ---: |")
            for feat in sorted(ci):
                vals = (list(ci[feat] or []) + [None, None, None])[:3]
                w(f"| {_cell(feat)} | {_num(vals[0])} | {_num(vals[1])} | "
                  f"{_num(vals[2])} |")
            w("")

    # Transfer-gap ledger -----------------------------------------------------
    w("## Transfer-gap ledger")
    w("")
    ledger = d["transfer_gaps"] or {}
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
    else:
        w("_No transfer-gap ledger in package._")
        w("")

    # Prohibited claims -------------------------------------------------------
    w("## Prohibited claims")
    w("")
    claims = d["prohibited_claims"]
    if claims:
        for c in claims:
            w(f"- {c}")
    else:
        w("_No prohibited-claims list in package._")
    w("")

    # Provenance footer -------------------------------------------------------
    w(f"_Dossier for `{unit_id}`; package_hash `{_cell(d.get('package_hash'))}`. "
      f"Bounded by the scope / claim-firewall and the transfer-gap ledger "
      f"reproduced from the package; nothing here widens them._")
    return "\n".join(out) + "\n"

