"""Decision logic: eligibility, Pareto comparison, and tie policy.

The engine never scalarises morphology into a single "Mars-likeness"
score. It filters ineligible units, then compares eligible units by
Pareto dominance across declared metrics, and reports a stable
recommendation only when it survives every declared sensitivity scenario.
"""
from __future__ import annotations

from itertools import combinations
import math

STATES = ("RECOMMEND_FOLLOW_UP", "TIE", "INDETERMINATE", "NOT_COMPARABLE", "BLOCKED")

# Only an explicitly verified status permits a unit to be compared/recommended.
ALLOWED_RIGHTS = ("verified_allowed",)

# Above this fraction of ~0 m pixels a unit is treated as water-contaminated.
ZERO_FRACTION_MAX = 0.6


def eligibility(unit):
    """Return (eligible: bool, reason: str) for a unit metadata dict.

    Fail-closed: rights use an allowlist, so any status that is not
    explicitly verified blocks the unit.
    """
    if not unit.get("data_present", False):
        return False, "BLOCKED: required data absent"
    if not unit.get("support_valid", False):
        return False, "NOT_COMPARABLE: common support invalid"
    if unit.get("valid_fraction", 0.0) < unit.get("min_valid_fraction", 0.5):
        return False, "BLOCKED: insufficient valid data"
    zf = unit.get("zero_fraction")
    if zf is not None and zf > unit.get("zero_fraction_max", ZERO_FRACTION_MAX):
        return False, f"BLOCKED: predominantly flat/zero ({zf:.2f}); likely water - mask or choose a land AOI"
    if unit.get("rights_status") not in ALLOWED_RIGHTS:
        return False, "BLOCKED: rights/access status not verified"
    return True, "eligible"


def dominates(a, b):
    """True if vector a dominates b (lower is better on every metric)."""
    no_worse = all(ai <= bi for ai, bi in zip(a, b))
    strictly_better = any(ai < bi for ai, bi in zip(a, b))
    return no_worse and strictly_better


def non_dominated(vectors):
    """vectors: dict unit_id -> tuple of metric distances. Returns a set.

    Units with any non-finite distance are excluded (a NaN must not silently
    collapse the result to a tie by making every comparison False).
    """
    units = [u for u in vectors if all(math.isfinite(x) for x in vectors[u])]
    nd = set(units)
    for i, j in combinations(units, 2):
        if dominates(vectors[i], vectors[j]):
            nd.discard(j)
        elif dominates(vectors[j], vectors[i]):
            nd.discard(i)
    return nd


def pairwise_flip_matrix(scenarios):
    """scenarios: list of dict unit->vector; scenarios[0] is the baseline.

    Flip fraction per pair = fraction of NON-baseline scenarios in which the
    sign of (d_i - d_j) on any metric differs from the baseline. The baseline
    is the reference, so it is excluded from the denominator.
    """
    if not scenarios or len(scenarios) < 2:
        return {}
    units = list(scenarios[0])
    base = scenarios[0]
    others = scenarios[1:]
    flips = {}
    for i, j in combinations(units, 2):
        if i not in base or j not in base:
            continue
        n_metrics = len(base[i])
        changed = comparisons = 0
        for s in others:
            if i not in s or j not in s:
                continue
            for r in range(n_metrics):
                base_sign = _sign(base[i][r] - base[j][r])
                cur_sign = _sign(s[i][r] - s[j][r])
                comparisons += 1
                if base_sign != cur_sign:
                    changed += 1
        flips[f"{i}|{j}"] = changed / comparisons if comparisons else 0.0
    return flips


def _sign(v):
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def resolve_state(eligible_vectors, scenarios, flip_threshold=0.1):
    """Resolve the overall result state among eligible units.

    eligible_vectors: dict unit->vector for the baseline scenario.
    scenarios: list of dict unit->vector (including baseline first).
    """
    if not eligible_vectors:
        return "NOT_COMPARABLE", None, {}
    nd_sets = [non_dominated(s) for s in scenarios] if scenarios else [non_dominated(eligible_vectors)]
    stable_nd = set.intersection(*nd_sets) if nd_sets else non_dominated(eligible_vectors)
    flips = pairwise_flip_matrix(scenarios) if scenarios else {}
    max_flip = max(flips.values(), default=0.0)
    baseline_nd = non_dominated(eligible_vectors)
    if len(stable_nd) == 1 and max_flip <= flip_threshold:
        return "RECOMMEND_FOLLOW_UP", next(iter(stable_nd)), flips
    if len(baseline_nd) == 1 and max_flip > flip_threshold:
        return "INDETERMINATE", None, flips
    return "TIE", None, flips
