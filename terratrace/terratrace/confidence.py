"""Honest, NON-composite decision confidence for a TerraTrace study.

TerraTrace never emits a single composite "goodness" or "Mars-likeness"
score, and neither does this module. :func:`decision_confidence` reads an
already-produced study ``package`` (plus an optional sensitivity/ablation
report) and restates the robustness evidence scattered across the package as
THREE independent signals, each reported with its own value and plain-language
detail, plus one categorical ``verdict`` and a ``rationale`` sentence. There is
no weighted sum, no 0-100 number, no hidden scalarisation: the verdict is a
documented rule over the per-signal classes below, and every signal that could
not be computed is listed verbatim in ``caveats`` so a reader sees exactly what
was and was not checked.

Scientific boundary (claim firewall): this is map-scale terrain-MORPHOLOGY
screening and resampling STATISTICS only. Nothing here produces a rover,
traversability, geologic-equivalence, site-access, or mission-readiness claim.
"Decision confidence" means only "how robust is the morphology screen's
recommendation to resampling, to a permutation test against the runner-up, and
to changing the decision lens/support" -- it says nothing about why two terrains
differ or what that implies for any mission.

Signals (each read, never fabricated; a missing block degrades to
``evaluated: False`` and is never invented):

* ``bootstrap_non_domination`` -- the probabilistic-Pareto frequency with which
  the recommended unit stays non-dominated across the bootstrap resamples, read
  from ``package["bootstrap"]["units"][recommended_unit]["nondominated_freq"]``
  (produced by :func:`terratrace.uncertainty.bootstrap_pareto` /
  ``block_bootstrap_pareto`` when a study is run with ``n_boot > 0``). A float
  in ``[0, 1]``.
* ``significance_vs_runner_up`` -- whether a permutation test finds the
  recommended unit significantly closer to the reference than the runner-up,
  read from ``package["significance"]["recommendation_significant"]`` (an opt-in
  sibling block). The reported ``p_value_one_sided`` is the WEAKEST (maximum)
  one-sided p across the block's ``per_metric`` tests, shown for transparency
  only; ``recommendation_significant`` is the authoritative flag.
* ``lens_stability`` -- whether the recommendation survives changing the
  decision lens and common support, read from
  ``sensitivity_report["overall_stable"]`` (the shape returned by
  :func:`terratrace.sensitivity.ablation_report`), falling back to
  ``sensitivity_report["lens"]["recommendation_stable"]``.
Per-signal class (documented thresholds, applied ONLY to evaluated signals):

* ``bootstrap_non_domination``: positive if ``value >= 0.8``, negative if
  ``value < 0.5``, otherwise weak. Reported as ``positive``: ``True`` (positive
  class), ``False`` (negative class), or ``None`` (weak, OR not evaluated --
  disambiguate with the ``evaluated`` flag).
* ``significance_vs_runner_up``: positive if ``significant`` is ``True``,
  negative if ``False``.
* ``lens_stability``: positive if ``stable`` is ``True``, negative if ``False``.

Verdict rule (NON-composite, no numeric combination):

* If ``result_state != "RECOMMEND_FOLLOW_UP"`` the verdict mirrors the state:
  ``TIE`` -> ``"tie"``, ``INDETERMINATE`` -> ``"indeterminate"``, ``BLOCKED`` ->
  ``"blocked"``, ``NOT_COMPARABLE`` -> ``"not_comparable"``; any other/missing
  state -> ``"unverified"``. Signals are still reported where available but do
  not change the verdict.
* Otherwise, over the EVALUATED signals only:

  - no signal evaluated -> ``"unverified"``;
  - else any evaluated signal negative -> ``"fragile"``;
  - else all evaluated signals positive AND at least two evaluated ->
    ``"robust"``;
  - otherwise (only one evaluated, or some weak) -> ``"qualified"``.

The function is pure: it reads ``package`` and ``sensitivity_report`` with
guarded ``.get`` access, never mutates them, is deterministic, imports only the
standard library, and never raises on a missing or malformed block.
"""
from __future__ import annotations

import math

RECOMMEND_STATE = "RECOMMEND_FOLLOW_UP"

# Documented non-domination thresholds (see module docstring / verdict rule).
POS_NONDOM = 0.8   # value >= this -> positive class
NEG_NONDOM = 0.5   # value <  this -> negative class; in-between -> weak

# Non-recommend result states map straight onto a mirrored verdict.
_STATE_VERDICT = {
    "TIE": "tie",
    "INDETERMINATE": "indeterminate",
    "BLOCKED": "blocked",
    "NOT_COMPARABLE": "not_comparable",
}

# Readable names for the plain-language rationale / caveats.
_READABLE = {
    "bootstrap_non_domination": "bootstrap non-domination",
    "significance_vs_runner_up": "significance vs runner-up",
    "lens_stability": "lens/support stability",
}

SIGNAL_NAMES = ("bootstrap_non_domination", "significance_vs_runner_up",
                "lens_stability")


def _coerce_float(x):
    """Return ``x`` as a finite float, or ``None`` if impossible/non-finite."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _join_readable(names):
    """Join signal keys into a readable, comma/'and'-separated phrase."""
    parts = [_READABLE.get(n, n) for n in names]
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return parts[0] + " and " + parts[1]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _bootstrap_signal(package, recommended_unit):
    """Read the recommended unit's bootstrap non-domination frequency.

    Returns ``(signal_dict, class_or_None)`` where class is one of
    ``"positive"`` / ``"weak"`` / ``"negative"`` for an evaluated signal, else
    ``None``.
    """
    boot = package.get("bootstrap")
    if not isinstance(boot, dict):
        return ({"evaluated": False, "value": None, "positive": None,
                 "detail": "no bootstrap block in package (run study with n_boot>0)"},
                None)
    units = boot.get("units")
    if recommended_unit is None or not isinstance(units, dict):
        return ({"evaluated": False, "value": None, "positive": None,
                 "detail": "no recommended unit or no bootstrap units table"},
                None)
    entry = units.get(recommended_unit)
    if not isinstance(entry, dict):
        return ({"evaluated": False, "value": None, "positive": None,
                 "detail": f"recommended unit {recommended_unit!r} absent from bootstrap units"},
                None)
    value = _coerce_float(entry.get("nondominated_freq"))
    if value is None:
        return ({"evaluated": False, "value": None, "positive": None,
                 "detail": "nondominated_freq missing or non-finite"},
                None)
    if value >= POS_NONDOM:
        cls, positive = "positive", True
    elif value < NEG_NONDOM:
        cls, positive = "negative", False
    else:
        cls, positive = "weak", None
    n_boot = _coerce_float(boot.get("n_boot"))
    nb = f", n_boot={int(n_boot)}" if n_boot is not None else ""
    detail = (f"recommended unit non-dominated in {value:.0%} of bootstrap "
              f"resamples{nb}; positive>={POS_NONDOM:.0%}, negative<{NEG_NONDOM:.0%}")
    return ({"evaluated": True, "value": value, "positive": positive,
             "detail": detail}, cls)


def _significance_signal(package):
    """Read the opt-in permutation-significance block for the recommendation."""
    sig = package.get("significance")
    if not isinstance(sig, dict):
        return ({"evaluated": False, "significant": None, "p_value_one_sided": None,
                 "detail": "no significance block in package (opt-in)"},
                None)
    rs = sig.get("recommendation_significant")
    if rs is None:
        return ({"evaluated": False, "significant": None, "p_value_one_sided": None,
                 "detail": "significance block present but recommendation_significant missing"},
                None)
    significant = bool(rs)
    p = None
    per_metric = sig.get("per_metric")
    if isinstance(per_metric, dict) and per_metric:
        ps = [_coerce_float(m.get("p_value_one_sided"))
              for m in per_metric.values() if isinstance(m, dict)]
        ps = [v for v in ps if v is not None]
        if ps:
            p = max(ps)   # weakest (most conservative) one-sided p, transparency only
    runner = sig.get("runner_up")
    detail = (f"permutation test vs runner-up {runner!r}: "
              f"recommendation_significant={significant}"
              + (f"; weakest one-sided p={p:.4g}" if p is not None
                 else "; no per-metric p available"))
    return ({"evaluated": True, "significant": significant,
             "p_value_one_sided": p, "detail": detail},
            "positive" if significant else "negative")


def _lens_signal(sensitivity_report):
    """Read overall lens/support stability from an ablation report."""
    if not isinstance(sensitivity_report, dict):
        return ({"evaluated": False, "stable": None,
                 "detail": "no sensitivity report provided"}, None)
    stable_val = sensitivity_report.get("overall_stable")
    source = "overall_stable"
    if stable_val is None:
        lens = sensitivity_report.get("lens")
        if isinstance(lens, dict):
            stable_val = lens.get("recommendation_stable")
            source = "lens.recommendation_stable"
    if stable_val is None:
        return ({"evaluated": False, "stable": None,
                 "detail": "sensitivity report present but no stability flag found"},
                None)
    stable = bool(stable_val)
    detail = (f"recommendation {'stable' if stable else 'NOT stable'} across "
              f"decision lenses/supports (ablation {source})")
    return ({"evaluated": True, "stable": stable, "detail": detail},
            "positive" if stable else "negative")


def _recommend_verdict(signals, classes):
    """Combine evaluated signal classes into a verdict + rationale (no score)."""
    evaluated = [n for n in SIGNAL_NAMES if signals[n]["evaluated"]]
    not_run = [n for n in SIGNAL_NAMES if not signals[n]["evaluated"]]
    pos = [n for n in evaluated if classes[n] == "positive"]
    weak = [n for n in evaluated if classes[n] == "weak"]
    neg = [n for n in evaluated if classes[n] == "negative"]

    if not evaluated:
        verdict = "unverified"
    elif neg:
        verdict = "fragile"
    elif len(pos) == len(evaluated) and len(evaluated) >= 2:
        verdict = "robust"
    else:
        verdict = "qualified"

    clauses = []
    if pos:
        clauses.append("supported by " + _join_readable(pos))
    if weak:
        clauses.append("only weakly supported by " + _join_readable(weak))
    if neg:
        clauses.append("undercut by " + _join_readable(neg))
    body = ("Recommendation " + "; ".join(clauses) + "." if clauses
            else "No robustness signal was evaluated for this recommendation.")
    if not_run:
        body += " Not evaluated: " + _join_readable(not_run) + "."
    return verdict, body


def _non_recommend_rationale(state, verdict, signals):
    """Rationale when the study did not reach a single-unit recommendation."""
    avail = [n for n in SIGNAL_NAMES if signals[n]["evaluated"]]
    s = (f"Result state {state!r} is not a single-unit recommendation, so the "
         f"verdict mirrors the state ({verdict}).")
    if avail:
        s += (" Robustness signals available but not used for this verdict: "
              + _join_readable(avail) + ".")
    else:
        s += " No robustness signals were evaluable."
    return s

def decision_confidence(package, sensitivity_report=None):
    """Restate a study's robustness evidence as independent decision signals.

    See the module docstring for the full signal sources, thresholds, and the
    non-composite verdict rule. Pure and read-only: ``package`` and
    ``sensitivity_report`` are never mutated, the result is deterministic, and a
    missing/malformed block degrades to ``evaluated: False`` rather than raising.
    """
    if not isinstance(package, dict):
        package = {}
    state = package.get("result_state")
    recommended_unit = package.get("recommended_unit")

    boot_sig, boot_cls = _bootstrap_signal(package, recommended_unit)
    sig_sig, sig_cls = _significance_signal(package)
    lens_sig, lens_cls = _lens_signal(sensitivity_report)

    signals = {
        "bootstrap_non_domination": boot_sig,
        "significance_vs_runner_up": sig_sig,
        "lens_stability": lens_sig,
    }
    classes = {
        "bootstrap_non_domination": boot_cls,
        "significance_vs_runner_up": sig_cls,
        "lens_stability": lens_cls,
    }
    caveats = [f"{n} not evaluated" for n in SIGNAL_NAMES
               if not signals[n]["evaluated"]]

    if state != RECOMMEND_STATE:
        verdict = _STATE_VERDICT.get(state, "unverified")
        rationale = _non_recommend_rationale(state, verdict, signals)
    else:
        verdict, rationale = _recommend_verdict(signals, classes)

    return {
        "state": state,
        "recommended_unit": recommended_unit,
        "signals": signals,
        "verdict": verdict,
        "rationale": rationale,
        "caveats": caveats,
    }

