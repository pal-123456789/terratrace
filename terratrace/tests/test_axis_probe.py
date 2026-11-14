"""The independent-axis probe: the estimator, the invariant, and the claim it bounds.

The load-bearing tests here are the two NEGATIVE CONTROLS and they are different kinds.

The first is statistical. A redundancy estimator that cannot say REDUNDANT about something which IS
redundant, or NON_REDUNDANT about something which is not, produces a ranking with no meaning. Both
directions are constructed synthetically: a descriptor defined as an exact function of the three axes
must come out fully explained, and one built to be independent of them must not.

The second is the frontier control, and it is the reason this experiment is worth publishing at all.
Adding a coordinate to a Pareto comparison can only PROMOTE a co-winner -- never remove one -- so a
removal is a machinery failure rather than a result. A test asserts the invariant holds on the real
record, and the artifact is checked for the control itself: 300 random coordinates against which the
candidate axes are judged, because without it "the frontier moved" would be presented as a property
of the descriptor when it is a property of adding a dimension.

The analytic claim also gets a test, at machine precision, in both directions: the three declared
axes are invariant under a quarter turn of a plane, and NOT invariant under a 45-degree rotation.
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))          # harness.py lives HERE, not in the package

from harness import require                                        # noqa: E402
from terratrace import axis_probe as ap, decision                  # noqa: E402

ARTIFACT = _ROOT / "artifacts" / "lunar_axis_probe" / "lunar_axis_probe.json"
CONFIG = _ROOT / "config" / "lunar_axis_probe_v1.yml"
AX3 = ["mean_slope_deg", "mean_relief3_m", "elev_std_m"]


def _panel_script():
    spec = importlib.util.spec_from_file_location("_lunar_v2", _ROOT / "scripts" / "lunar_sites_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ the estimator

def test_the_chance_level_is_the_published_one_and_is_not_trivial():
    assert abs(ap.chance_level_raw_r2(8, 3) - 3.0 / 7.0) < 1e-15
    assert ap.chance_level_raw_r2(8, 3) > 0.42, (
        "at n=8 and p=3 a raw R2 of 0.5 is barely above chance, which is why the statistic is "
        "adjusted; if this number were small the whole argument would be wrong")
    assert ap.chance_level_raw_r2(2, 1) is None


def test_adjusted_r2_calls_a_constant_response_undefined_rather_than_zero():
    """A constant descriptor is the one case where a low R2 is guaranteed and means nothing."""
    X = np.arange(8.0).reshape(-1, 1) @ np.ones((1, 3)) + np.random.default_rng(0).normal(size=(8, 3))
    r2, adj = ap.adjusted_r2(np.full(8, 5.0), X)
    assert r2 is None and adj is None, "a constant response must be UNDEFINED, not a perfect fit or a zero"


def test_adjusted_r2_is_near_chance_for_a_random_response_and_one_for_an_exact_one():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(8, 3))
    exact = 2.0 * X[:, 0] - 1.5 * X[:, 1] + 0.25 * X[:, 2]
    r2, adj = ap.adjusted_r2(exact, X)
    assert abs(r2 - 1.0) < 1e-12 and abs(adj - 1.0) < 1e-12, "an exact linear function is fully explained"
    raws = [ap.adjusted_r2(rng.normal(size=8), X)[0] for _ in range(400)]
    adjs = [ap.adjusted_r2(rng.normal(size=8), X)[1] for _ in range(400)]
    assert abs(np.mean(raws) - ap.chance_level_raw_r2(8, 3)) < 0.10, (
        f"raw R2 on noise should average the chance level, got {np.mean(raws):.3f}")
    assert abs(np.mean(adjs)) < 0.10, (
        f"adjusted R2 on noise should average ~0, got {np.mean(adjs):.3f} -- otherwise the "
        f"threshold is not interpretable")
    assert np.mean(adjs) < np.mean(raws) - 0.3, "the adjustment must actually adjust, not decorate"


def test_within_cell_cv_refuses_the_two_ways_it_is_meaningless():
    """A constant descriptor gives a CV of exactly 0, which the threshold then excludes -- reporting
    it as UNDEFINED instead would hide a real (if useless) value. What must be UNDEFINED is a spread
    divided by a near-zero mean, because that ratio is a denominator artefact."""
    assert ap.within_cell_cv([3.0] * 8) == 0.0, "a constant descriptor has zero spread, and that is a value"
    assert ap.within_cell_cv([1e-12, -1e-12, 2e-12, -2e-12, 1e-12, 1e-12, -1e-12, 0.0]) is None, (
        "a mean indistinguishable from zero makes the ratio unstable, and admitting it lets a "
        "signed or compositional descriptor through on a denominator artefact")
    assert ap.within_cell_cv([0.0] * 8) is None, "an all-zero vector has no scale to divide by"
    got = ap.within_cell_cv([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    assert got is not None and abs(got - float(np.std(np.arange(1, 9))) / 4.5) < 1e-12
    assert ap.within_cell_cv([1.0, np.nan, 3.0]) is None, "a non-finite value is not a spread"


def test_the_two_normalisations_are_different_and_only_one_is_always_defined():
    assert ap.engine_fractional_distance(0.0, 4.0) is None, (
        "the engine's normalisation divides by the reference and is undefined at zero; returning a "
        "number here would hide the NaN trap the probe exists to report")
    assert abs(ap.engine_fractional_distance(2.0, 3.0) - 0.5) < 1e-15
    v = ap.range_distance_vector([0.0, 1.0, 2.0, 4.0], 0)
    assert v is not None and abs(v[3] - 1.0) < 1e-15 and abs(v[0]) < 1e-15
    assert ap.range_distance_vector([0.0, 0.0, 0.0, 1.0], 0).max() == 1.0
    assert ap.range_distance_vector([5.0] * 4, 0) is None, "a constant axis has no distance to give"
    assert ap.range_distance_vector([0.0, np.nan, 2.0], 0) is None


# ------------------------------------------------------------------ the invariant and the buckets

def test_adding_a_coordinate_can_only_promote_and_a_removal_is_caught():
    base = ["a"]
    assert ap.promoted_only(base, ["a", "b"]) == (["b"], [])
    assert ap.promoted_only(base, ["a", "b", "c"]) == (["b", "c"], [])
    prom, removed = ap.promoted_only(["a", "b"], ["a"])
    assert removed == ["b"], (
        "a removal must be REPORTED, not scored as a promotion -- Pareto dominance makes it "
        "impossible, so it means the added coordinate is not finite somewhere")


def test_classification_boundaries_are_the_declared_ones():
    assert ap.classify(-0.5) == ap.NON_REDUNDANT
    assert ap.classify(0.0) == ap.NON_REDUNDANT
    assert ap.classify(0.001) == ap.PARTIALLY_INDEPENDENT
    assert ap.classify(0.25) == ap.PARTIALLY_INDEPENDENT
    assert ap.classify(0.251) == ap.REDUNDANT
    assert ap.classify(1.0) == ap.REDUNDANT
    assert ap.classify(None) == ap.UNDEFINED, "an undefined R2 is not a redundant one"


# ------------------------------------------------------------------ the analytic claim

def test_the_plane_family_has_the_gradient_it_claims():
    z = ap.plane(0.30, 37.0, n=18, dx=500.0)
    gx, gy = np.gradient(z, 500.0)
    assert abs(float(np.hypot(gx, gy).mean()) - 0.30) < 1e-12, (
        "the plane must have gradient magnitude g regardless of azimuth, or the invariance test is "
        "comparing two different surfaces")


def test_the_declared_axes_agree_with_the_panels_own_implementation():
    """The duplication is deliberate; this keeps it from drifting into a different measurement."""
    v2 = _panel_script()
    rng = np.random.default_rng(11)
    for dx in (500.0, 750.0, 1000.0):
        z = rng.normal(size=(18, 18)) * 30.0 + 1000.0
        z[0, 0] = np.nan
        mine, theirs = ap.declared_axes(z, dx), v2.axes_of(z, dx)
        assert set(mine) == set(theirs)
        for k in mine:
            assert abs(mine[k] - theirs[k]) < 1e-12, f"{k} drifted: {mine[k]} vs {theirs[k]}"


def test_the_three_axes_are_blind_to_a_quarter_turn_and_NOT_blind_to_a_45_degree_turn():
    """The analytic claim, at machine precision, asserted in both directions.

    The second half matters as much as the first: if relief were invariant under 45 degrees too, the
    axes would be blind to all of orientation and the claim would be far stronger than it is.
    """
    rep = ap.invariance_report(dx=500.0)
    for op in ("theta_plus_90", "ninety_minus_theta", "theta_plus_180"):
        assert max(rep[op].values()) < 1e-9, (
            f"{op} moves a declared axis by {max(rep[op].values()):.3e}, so the axes are not exactly "
            f"blind to it and the analytic half does not hold")
    assert rep["theta_plus_45"]["mean_relief3_m"] > 100.0, (
        "a 45-degree rotation must move mean_relief3_m through the bounded rho factor by a large "
        "amount; getting ~0 would mean the axes are blind to orientation entirely, which is a "
        "different and much stronger claim than the one being made")
    assert rep["theta_plus_45"]["mean_slope_deg"] < 1e-9, (
        "mean slope is a function of gradient magnitude alone and must not move at any azimuth")


# ------------------------------------------------------------------ the record

def test_the_bank_symmetry_is_recorded_and_pinned():
    """How many bank scalars the quarter-turn argument can even apply to.

    Pinned deliberately. The first version of this figure was computed by an ad-hoc check that
    aliased the theta=90 bank into both sides of the comparison and reported 3 of 187 -- a number
    that was pure artefact. Measuring it inside the probe is what made it checkable; the count below
    must be re-measured rather than remembered, and a change in it is a change in the argument.
    """
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    bq = a["invariance"]["bank_quarter_turn"]
    assert bq["n_checked"] >= 150, "too few bank scalars were computable on a plane to bound anything"
    assert bq["n_changed"] == 48, (
        f"{bq['n_changed']} bank scalars are now quarter-turn non-invariant (was 48); the analytic "
        f"half's reach changed and the write-up has to be re-read")
    assert len(bq["changed"]) == bq["n_changed"]
    assert all(v > 1e-9 for v in bq["changed"].values())


def test_the_symmetry_argument_does_not_identify_the_descriptor_the_measurement_does():
    """The honest seam between the two halves, asserted so it cannot be smoothed over in prose.

    The nugget is the most independent descriptor the measurement finds, and it is quarter-turn
    INVARIANT, so the symmetry argument cannot see it. A write-up that implied the analytic half
    predicted the answer would be wrong, and this is the test that keeps that from happening.
    """
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    changed = a["invariance"]["bank_quarter_turn"]["changed"]
    assert "/variogram/nugget" not in changed, (
        "the nugget became quarter-turn non-invariant, so the analytic half now covers it and the "
        "paragraph about the two halves disagreeing is no longer true")
    best = a["verdict"]["most_independent_admissible_descriptor"]["key"]
    assert best == "/variogram/nugget"
    assert best not in changed


def test_the_record_exists_and_the_precondition_was_met_before_it_was_written():

    require(ARTIFACT.exists(), "artifacts/lunar_axis_probe/lunar_axis_probe.json is force-added; a "
                              "published sensitivity result has no evidence in the tree without it")
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert a["provenance"]["status"] == "EXPLORATORY SENSITIVITY PROBE"
    assert "not a pre-registration" in a["provenance"]["not"], (
        "the probe ran on cells already examined; the record has to say so in its own provenance "
        "block rather than relying on a reader to remember")
    assert a["frontier"]["baseline_mismatches"] == [], (
        "the probe did not reproduce the v2 layer-1 sets, so it probed a different panel")
    assert a["frontier"]["baseline_frontier_size_counts"] == {"1": 18}, (
        "the published baseline is a sole non-dominated candidate at all 18 cells")


def test_the_record_declares_no_removals_and_its_control_is_present():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert a["frontier"]["removals_detected"] == 0
    for t in a["frontier"]["per_descriptor"]:
        assert t["removal_alarms"] == [], f"a removal was recorded for {t['key']}"
        assert 0 <= t["changed_cells"] <= 18
    c = a["random_control"]
    assert c["draws"] == 300 and c["n_cells"] == 18, (
        "the frontier numbers are only readable next to the control, so the control must be in the record")
    assert 10.0 < c["mean_changed_cells"] < 18.0, (
        "an arbitrary 4th coordinate is expected to move the frontier in most cells; if it did not, "
        "the observed changes would be attributable to the descriptors instead")
    assert c["fraction_unchanged"] > 0.0, "some draws must leave the frontier intact, or the control is degenerate"


def test_no_candidate_axis_beats_the_random_control_and_the_record_says_so():
    """The finding, pinned. If a future axis DOES beat the control, that is a change in the result."""
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    n = a["verdict"]["n_descriptors_beating_the_random_control"]
    assert n == 0, (
        f"{n} descriptors now move the frontier further than an arbitrary coordinate does; that is "
        f"a different finding and it has to be reported, not absorbed")
    assert len(a["frontier"]["per_descriptor"]) > 100, "the decision test must cover the whole pool"
    assert "NUMBER of axes" in a["verdict"]["reading"], (
        "the reading must attribute the fragility to the dimensionality of the rule, because that "
        "is what the control shows")


def test_the_measurement_controls_pass_in_the_record():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert a["controls"]["pass"] is True, (
        "the two exact identities -- the bank's slope mean and the Declared-axis slope mean -- must "
        "come out fully explained; if they do not, the estimator is wrong and every ranking in the "
        "record is meaningless")
    for k, v in a["controls"]["exact_identity"].items():
        assert abs(v - 1.0) < 1e-9, f"{k} came out at {v}"
    near = a["controls"]["near_identity"]
    assert near, "the different-estimator controls are missing"
    for k, v in near.items():
        assert 0.9 < v < 1.0, (
            f"{k} is a DIFFERENT estimator of the same idea (a 5x5 window against a 3x3 one, or an "
            f"rms against a mean); it should be very high and must not be exactly 1.0, and {v} is "
            f"neither -- which would mean the estimator is comparing the wrong things")
        assert abs(v - 1.0) > 1e-6, f"{k} came out as an exact identity; then it belongs in the exact set"
    rows = a["descriptors"]
    assert len(rows) == a["pool"]["n_admissible"] > 100
    assert rows == sorted(rows, key=lambda r: r["median_adjusted_r2"]), "the ranking is not sorted by the statistic"
    assert all(r["classification"] in (ap.NON_REDUNDANT, ap.PARTIALLY_INDEPENDENT, ap.REDUNDANT)
               for r in rows)


def test_the_circular_descriptor_is_named_and_excluded():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    ex = {e["key"] for e in a["circular_excluded"]}
    assert ex, "the circular descriptor is not excluded, so the probe may be promoting an unusable axis"
    assert all(k.endswith("orientation_deg") for k in ex)
    assert all(t["key"] not in ex for t in a["frontier"]["per_descriptor"]), (
        "an excluded circular descriptor reached the decision test")


def test_the_nan_audit_is_recorded_and_the_declared_axes_are_not_in_it():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    na = a["nan_audit"]
    assert na["n_descriptors_affected"] > 0, (
        "the audit exists to report the latent defect; finding nothing would mean it is not looking")
    assert not any(k.endswith(("mean_slope_deg", "mean_relief3_m", "elev_std_m")) for k in na["affected"])
    assert "strictly positive" in na["note"]


def test_the_protocol_is_frozen_and_names_its_pilot_disclosure():
    text = CONFIG.read_text(encoding="utf-8")
    assert "declared_before_the_recorded_run: true" in text
    assert "pilot_disclosed" in text, (
        "a pilot run influenced the admissibility rule; a protocol that hides that is not a record "
        "of what was decided before the measurement")
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert a["provenance"]["protocol_sha256"] == __import__("hashlib").sha256(
        CONFIG.read_bytes()).hexdigest(), (
        "the recorded protocol hash does not match the committed protocol, so 'frozen before the "
        "run' is not a mechanical claim")
