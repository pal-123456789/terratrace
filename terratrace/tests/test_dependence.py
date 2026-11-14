"""The dependence audit: the algebra, the statistics, and the numbers that bound the lunar claim.

The claim under test is unusually specific, which makes it unusually testable. `slope_deg` is
`degrees(arctan(|grad z|))` and `relief(window=3, alpha=0)` is the 3x3 max-minus-min, so for a
locally planar surface

    relief = 2 d tan(slope) * rho,    rho = (|a| + |b|) / hypot(a, b)  in [1, sqrt(2)]

and the two descriptors cannot be independent evidence. These tests check that derivation against
the ENGINE's own functions rather than against the algebra that produced it, then check that the
panel-level statistics say what the artifact says they say — and include the negative controls,
because a rank-1 result is only meaningful if the rank can come out greater than 1.
"""
import json
import math
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from terratrace import dependence as dep, features                 # noqa: E402

AUDIT = _ROOT / "artifacts" / "dependence" / "dependence_audit.json"


# ------------------------------------------------------------------ rank statistics

def test_pearson_and_spearman_differ_where_they_should():
    """A perfectly monotone but curved relationship: Spearman 1.0, Pearson well below it."""
    x = np.arange(1, 21, dtype=float)
    y = np.exp(x / 3.0)
    assert abs(dep.spearman(x, y) - 1.0) < 1e-12, "a strictly increasing map must give rho = 1"
    assert dep.pearson(x, y) < 0.9, "Pearson should be dragged down by the curvature"
    assert abs(dep.pearson(x, 3 * x + 1) - 1.0) < 1e-12


def test_a_flat_axis_reports_no_correlation_rather_than_zero():
    """Zero spread means the correlation is undefined; returning 0.0 would be a fabricated number."""
    assert dep.pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
    assert dep.pearson([1.0], [2.0]) is None


def test_rankdata_averages_ties():
    assert dep.rankdata([5, 5, 5]).tolist() == [2.0, 2.0, 2.0]
    assert dep.rankdata([1, 2, 3]).tolist() == [1.0, 2.0, 3.0]
    assert dep.rankdata([10, 20, 20, 40]).tolist() == [1.0, 2.5, 2.5, 4.0]


# ------------------------------------------------------------------ the spectrum

def test_effective_rank_is_one_for_a_duplicated_axis_and_n_for_independent_ones():
    rng = np.random.default_rng(11)
    a = rng.normal(size=60)
    cols = {"a": a, "a_copy": a * 2.0 + 5.0, "a_third": -a}
    _, corr = dep.correlation_matrix(cols)
    assert dep.effective_rank(corr, 0.95) == 1, "three copies of one axis must span one dimension"
    assert abs(dep.participation_ratio(corr) - 1.0) < 1e-6

    indep = {f"x{i}": rng.normal(size=60) for i in range(3)}
    _, corr2 = dep.correlation_matrix(indep)
    assert dep.effective_rank(corr2, 0.95) == 3, (
        "independent axes must NOT come out rank 1 -- if they do, the statistic is broken and the "
        "lunar finding it supports is worthless")


def test_vif_explodes_for_a_collinear_axis():
    """The diagnostic that names the offending axis rather than just its symptom."""
    rng = np.random.default_rng(5)
    a = rng.normal(size=80)
    b = rng.normal(size=80)
    _, corr = dep.correlation_matrix({"a": a, "exact_copy": 3 * a - 1, "b": b})
    v = dep.vif({"a": a, "exact_copy": 3 * a - 1, "b": b}, ["a", "exact_copy", "b"])
    assert v["a"] > 1e6 and v["exact_copy"] > 1e6, f"collinear axes must show huge VIF: {v}"
    assert v["b"] < 5.0, f"an unrelated axis must not be flagged: {v}"
    assert dep.condition_number(corr) > 1e6


# ------------------------------------------------------------------ the derivation, vs the engine

def test_the_planar_relation_holds_against_the_engines_own_functions():
    """The core claim, checked by calling slope_deg and relief, not by re-deriving it.

    This is the test that makes 'slope and relief are one measurement' a fact rather than an
    impression: on a synthetic plane the two engine functions must reproduce the closed form to
    floating point, in the interior where the stencils are complete.
    """
    d, n = 25.0, 41
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    for a, b in ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (-0.7, 0.3), (0.01, 0.01)):
        z = a * (xx * d) + b * (yy * d)
        got_slope = float(np.nanmean(features.slope_deg(z, d, d)[2:-2, 2:-2]))
        got_relief = float(np.nanmean(features.relief(z, window=3, alpha=0.0)[2:-2, 2:-2]))
        want_relief, two_d_tan, rho = dep.planar_relief_over_slope(a, b, d)
        want_slope = math.degrees(math.atan(math.hypot(a, b)))
        assert abs(got_slope - want_slope) < 1e-9, f"({a},{b}) slope {got_slope} != {want_slope}"
        assert abs(got_relief - want_relief) < 1e-9, f"({a},{b}) relief {got_relief} != {want_relief}"
        assert abs(got_relief - two_d_tan * rho) < 1e-9


def test_the_direction_factor_is_bounded_by_one_and_root_two():
    """rho can neither fall below 1 nor exceed sqrt(2), over any orientation or scale."""
    lo, hi = dep.rho_bounds()
    assert (lo, hi) == (1.0, math.sqrt(2.0))
    worst_lo, worst_hi = 10.0, 0.0
    for a in np.linspace(0, 4, 41):
        for b in np.linspace(0, 4, 41):
            if a == 0 and b == 0:
                continue
            _, _, rho = dep.planar_relief_over_slope(a, b, 30.0)
            assert lo - 1e-12 <= rho <= hi + 1e-12, f"({a},{b}) gave rho {rho} outside [{lo},{hi}]"
            worst_lo, worst_hi = min(worst_lo, rho), max(worst_hi, rho)
    assert worst_lo < 1.0001, "the lower bound is attained only for an axis-aligned gradient"
    assert worst_hi > 1.4141, "the upper bound is attained only for a diagonal gradient"


def test_rho_is_scale_free_so_the_relation_cannot_be_broken_by_resolution():
    """rho depends on the gradient's DIRECTION only, which is why the redundancy is scale-invariant."""
    for d in (5.0, 30.0, 500.0):
        for a, b in ((1.0, 0.0), (1.0, 1.0), (3.0, 1.0)):
            _, _, rho = dep.planar_relief_over_slope(a, b, d)
            _, _, rho2 = dep.planar_relief_over_slope(a * 1000, b * 1000, d)
            assert abs(rho - rho2) < 1e-12, "rho moved with the gradient magnitude"


def test_the_planar_fit_recovers_the_direction_factor_from_data():
    """On axis-aligned planes rho = 1 exactly, so the fitted scale must come back as 1.

    Several planes, not one: the fit has a single free scale and a one-point sample has no spread,
    so a single plane would make the fit undefined rather than wrong. (The first version of this
    test passed one plane and got `None` back for exactly that reason.)
    """
    d, n = 30.0, 31
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    slopes, reliefs = [], []
    for a in (0.01, 0.05, 0.1, 0.2, 0.4):
        z = a * (xx * d)                      # axis-aligned: rho = (|a| + 0) / |a| = 1
        slopes.append(float(np.nanmean(features.slope_deg(z, d, d)[2:-2, 2:-2])))
        reliefs.append(float(np.nanmean(features.relief(z, window=3, alpha=0.0)[2:-2, 2:-2])))
    r2, k, m = dep.planar_r2(reliefs, slopes, d)
    assert m == len(slopes)
    assert abs(k - 1.0) < 1e-9, f"axis-aligned planes must give rho = 1, got {k}"
    assert r2 > 0.9999, f"the closed form should explain an axis-aligned family exactly, R2={r2}"


# ------------------------------------------------------------------ the recorded audit

def test_the_audit_record_is_present_and_self_consistent():
    assert AUDIT.exists(), (
        "artifacts/dependence/dependence_audit.json is committed (git add -f: the artifacts/ tree "
        "is ignored and a small record backing a published claim is force-added on purpose). If it "
        "is missing, the published one-axis finding has no evidence in the tree.")
    a = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert a["analytic"]["verified_against_engine"] is True, (
        "the analytic slope/relief identity did not reproduce against the engine; the one-axis "
        "conclusion rests on it")
    assert a["analytic"]["worst_relief_error_m"] < 1e-9
    lo, hi = a["analytic"]["rho_bounds_provable"]
    assert [lo, hi] == [1.0, math.sqrt(2.0)], f"the recorded bounds are {[lo, hi]}"
    obs_lo, obs_hi = a["analytic"]["rho_observed_range"]
    assert lo - 1e-9 <= obs_lo and obs_hi <= hi + 1e-9, "an observed rho escaped the provable band"


def test_the_audit_says_one_dimension_and_the_fit_agrees():
    if not AUDIT.exists():
        return
    a = json.loads(AUDIT.read_text(encoding="utf-8"))
    for support, entry in a["panel"].items():
        for pool, block in entry["pools"].items():
            assert block["effective_rank_95"] == 1, (
                f"{support}/{pool} spans {block['effective_rank_95']} dimensions; the one-axis "
                f"statement in the docs and the decks is then wrong")
            pf = block["planar_fit"]
            assert 1.0 <= pf["scale_k"] <= math.sqrt(2.0), (
                f"{support}/{pool} fitted a direction factor {pf['scale_k']} outside the provable "
                f"[1, sqrt(2)] band, which cannot happen for a locally planar surface")
            assert pf["r2"] > 0.95, (f"{support}/{pool} planar fit R2 {pf['r2']} is too low for the "
                                     f"closed form to be doing the explaining")
    assert a["verdict"]["three_axes_are_one_dimension"] is True
    assert a["verdict"]["frontier_invariant_to_any_single_axis_drop"] is True, (
        "dropping an axis now changes the frontier, so the axes are NOT interchangeable and the "
        "rank-1 claim is too strong")


def test_the_audit_covers_every_support_and_both_pools():
    """A rank-1 claim from one support and one pool would be a sample, not a finding."""
    if not AUDIT.exists():
        return
    a = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert set(a["panel"]) == {"500", "750", "1000"}
    for entry in a["panel"].values():
        assert set(entry["pools"]) == {"candidates_only", "cross_body"}
        assert entry["pools"]["candidates_only"]["n_units"] == 7
        assert entry["pools"]["cross_body"]["n_units"] == 13
    assert set(a["leave_one_axis_out"]) == {"500", "750", "1000"}
    for v in a["leave_one_axis_out"].values():
        assert len(v["per_site"]) == 6, "the leave-one-out must cover all six lunar references"
