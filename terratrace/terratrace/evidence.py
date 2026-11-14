"""Validation of recorded evidence, so a claim's own numbers can be checked against themselves.

WHY THIS MODULE EXISTS
----------------------
`tests/test_lunar_demonstration.py` contained this assertion:

    assert abs(sum(freq.values()) - len(block["point_estimate_layer1"]) * frac - 0) >= 0

`abs(...) >= 0` is true for every real number. The line validated nothing, while sitting in a test
named for the ensemble's integrity and passing on every run. It is worse than a missing test: it is
a test that would have been quoted as evidence.

The frequencies were the problem: a fraction alone cannot be checked, because any fraction in [0, 1]
is a plausible-looking frequency. Counts can be checked, because they must be whole, must sum to the
number of realisations, and must agree with every other count derived from the same draws. So the
artifacts record counts *and* fractions, and this module checks them against each other.

`check_ensemble_counts` returns a list of problems; empty means consistent. It never raises, so it
can be used both inside the producing script and in the test suite.
"""
from __future__ import annotations

import math


def _is_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def check_ensemble_counts(ens):
    """Problems with an ensemble block's recorded counts. Empty list == internally consistent.

    The invariants, each of which a corrupted record breaks:

    1. the declared number of realisations is a positive count, and matches the draw count;
    2. the exact-set counts sum to the number of realisations (every draw produced exactly one set);
    3. each candidate's membership count is a whole number between 0 and the draw count;
    4. the membership counts sum to the total member-slots implied by the recorded sets;
    5. every recorded frequency equals its own count divided by the draw count;
    6. the exact-match count agrees with the recorded set that matched, and with its fraction.
    """
    problems = []
    n = ens.get("n_draws")
    if not _is_count(n) or n <= 0:
        return [f"n_draws must be a positive whole number, got {n!r}"]
    if ens.get("n_realisations") is not None and ens["n_realisations"] != n:
        problems.append(f"n_realisations {ens['n_realisations']} != n_draws {n}")
    for scale, block in (ens.get("scales") or {}).items():
        tag = f"ensemble[{scale}]"
        counts = block.get("candidate_layer1_count")
        freqs = block.get("candidate_layer1_frequency")
        sets = block.get("layer1_set_counts")
        if counts is None or freqs is None or sets is None:
            problems.append(f"{tag}: counts, frequencies and set counts are all required; a "
                            f"frequency alone cannot be checked")
            continue
        if set(counts) != set(freqs):
            problems.append(f"{tag}: counts and frequencies cover different candidates: "
                            f"{sorted(set(counts) ^ set(freqs))}")
        for u, c in counts.items():
            if not _is_count(c):
                problems.append(f"{tag}: count for {u} is {c!r}, not a whole number >= 0")
            elif c > n:
                problems.append(f"{tag}: {u} is in layer 1 for {c} of {n} draws, which is impossible")
        # (2) every draw produced exactly one set
        set_total = sum(sets.values())
        if set_total != n:
            problems.append(f"{tag}: recorded layer-1 set counts sum to {set_total}, not the "
                            f"{n} realisations - a draw is missing or double-counted")
        # (4) member slots implied by the sets must equal the membership counts
        implied = 0
        for name, cnt in sets.items():
            members = [m for m in name.split("+") if m] if name != "(none)" else []
            implied += len(members) * cnt
        if sum(counts.values()) != implied:
            problems.append(f"{tag}: membership counts sum to {sum(counts.values())}, but the "
                            f"recorded sets imply {implied} member slots")
        # (5) each frequency must be its own count over the draws
        for u, f in freqs.items():
            if u not in counts:
                continue
            want = counts[u] / n
            if not isinstance(f, (int, float)) or abs(f - want) > 1e-12:
                problems.append(f"{tag}: frequency for {u} is {f!r}, but its count "
                                f"{counts[u]}/{n} = {want:.6f}")
        # (6) the exact-match count must be the count of the point estimate's own set
        point = block.get("point_estimate_layer1")
        if point is not None:
            key = "+".join(sorted(point))
            recorded = sets.get(key, 0)
            if block.get("exact_set_match_count") not in (None, recorded):
                problems.append(f"{tag}: exact_set_match_count "
                                f"{block['exact_set_match_count']} != {recorded} for set {key!r}")
            frac = block.get("exact_set_match_fraction")
            if frac is not None and (not isinstance(frac, (int, float))
                                     or abs(frac - recorded / n) > 1e-12):
                problems.append(f"{tag}: exact_set_match_fraction {frac!r} != {recorded}/{n}")
    return problems


def check_frequency_only_ensemble(ens):
    """A weaker check for records that store fractions without counts.

    A frequency that could not have come from a whole number of draws is still detectable, so the
    older v1 artifact is not left entirely unverifiable. It cannot be checked further than this, and
    that limitation is the reason v2 records counts.
    """
    problems = []
    n = ens.get("n_draws")
    if not isinstance(n, int) or n <= 0:
        return [f"n_draws must be a positive whole number, got {n!r}"]
    for scale, block in (ens.get("scales") or {}).items():
        for u, f in (block.get("candidate_layer1_frequency") or {}).items():
            if not isinstance(f, (int, float)) or not (0.0 <= f <= 1.0):
                problems.append(f"[{scale}]: frequency for {u} is {f!r}, not in [0, 1]")
                continue
            k = f * n
            if math.isnan(k) or abs(k - round(k)) > 1e-9:
                problems.append(f"[{scale}]: frequency {f} for {u} is not a whole number of "
                                f"{n} draws ({k:.6f}) - it cannot have come from those draws")
        frac = block.get("exact_match_fraction")
        if frac is not None:
            k = frac * n
            if not (0.0 <= frac <= 1.0) or abs(k - round(k)) > 1e-9:
                problems.append(f"[{scale}]: exact_match_fraction {frac} is not a whole number of "
                                f"{n} draws")
    return problems
