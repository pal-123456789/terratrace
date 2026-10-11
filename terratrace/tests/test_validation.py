"""Scientific-correctness validation suite tests.

Drives ``terratrace.validation`` (the real engine on synthetic terrains with
known relationships) and asserts the headline oracle, per-check record shape,
determinism, three individual checks, and that key metrics are scientifically
sane. Dependency-free: plain ``def test_*()``, assert-based, no pytest, no
network. ``run_validation()`` is ~2-3 s, so it is cached and run only twice
total across the whole module.
"""
from terratrace import validation


# Record ``name`` values (the ``check_`` prefix is stripped inside the module).
_EXPECTED_NAMES = (
    "self_distance_zero",
    "translation_invariance",
    "rotation90_invariance",
    "monotonic_roughness_discrimination",
    "dominance_recovery",
    "null_control",
    "water_candidate_blocked",
    "determinism",
    "curvature_zero_on_plane",
    "vrm_discriminates_roughness",
    "roughness_hurst_sane",
    "openness_flat",
    "openness_peak",
    "openness_pit_mirror",
    "geomorphon_flat",
    "geomorphon_cone_peak",
    "geomorphon_bowl_pit",
    "geomorphon_tilt_slope",
    "geomorphon_relief_invariance",
    "significance_clear_winner",
    "significance_near_tie_is_honest",
    "confidence_robust_on_clear_winner",
    "confidence_fragile_or_tie_on_near_tie",
)

# New line-of-sight morphology oracles added on top of the original battery.
_MORPH_NAMES = (
    "openness_flat",
    "openness_peak",
    "openness_pit_mirror",
    "geomorphon_flat",
    "geomorphon_cone_peak",
    "geomorphon_bowl_pit",
    "geomorphon_tilt_slope",
    "geomorphon_relief_invariance",
)

# Statistical-layer oracles: resampling significance + decision-confidence verdict.
_SIG_CONF_NAMES = (
    "significance_clear_winner",
    "significance_near_tie_is_honest",
    "confidence_robust_on_clear_winner",
    "confidence_fragile_or_tie_on_near_tie",
)

_N_CHECKS = len(_EXPECTED_NAMES)

_REPORT_CACHE = []


def _report():
    """One cached ``run_validation()`` report shared across tests."""
    if not _REPORT_CACHE:
        _REPORT_CACHE.append(validation.run_validation())
    return _REPORT_CACHE[0]


def _find(report, name):
    for c in report["checks"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"check {name!r} not in report")


def test_run_validation_headline_oracle():
    """The engine is scientifically correct: all checks pass."""
    report = _report()
    assert report["all_passed"] is True
    assert report["passed"] == _N_CHECKS
    assert report["failed"] == 0
    assert len(report["checks"]) == _N_CHECKS
    assert isinstance(report["package_hash"], str)
    assert report["package_hash"], "package_hash must be a non-empty string"


def test_every_check_record_shape_and_names():
    """Each record has name/passed/detail/metrics, passes, and the names are
    unique and exactly the expected set."""
    report = _report()
    names = []
    for c in report["checks"]:
        for key in ("name", "passed", "detail", "metrics"):
            assert key in c, (key, c)
        assert isinstance(c["name"], str)
        assert isinstance(c["detail"], str)
        assert isinstance(c["metrics"], dict)
        assert isinstance(c["passed"], bool), c["name"]
        assert c["passed"] is True, (c["name"], c["detail"])
        names.append(c["name"])
    assert len(names) == _N_CHECKS
    assert len(set(names)) == _N_CHECKS, f"duplicate check names: {names}"
    assert set(names) == set(_EXPECTED_NAMES), set(names) ^ set(_EXPECTED_NAMES)


def test_run_validation_is_deterministic():
    """Two independent runs agree on package_hash, the ordered (name, passed)
    sequence of every check, and the pass/fail tallies."""
    first = _report()
    second = validation.run_validation()
    assert first["package_hash"] == second["package_hash"]
    assert (first["passed"], first["failed"]) == (second["passed"], second["failed"])
    seq_a = [(c["name"], c["passed"]) for c in first["checks"]]
    seq_b = [(c["name"], c["passed"]) for c in second["checks"]]
    assert seq_a == seq_b
    outcomes_a = {c["name"]: c["passed"] for c in first["checks"]}
    outcomes_b = {c["name"]: c["passed"] for c in second["checks"]}
    assert outcomes_a == outcomes_b


def test_new_morphology_checks_present_and_pass():
    """The eight added openness/geomorphon oracles are registered in the report
    and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _MORPH_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_self_distance_zero_passes():
    rec = validation.check_self_distance_zero()
    assert rec["name"] == "self_distance_zero"
    assert rec["passed"] is True, rec["detail"]


def test_check_dominance_recovery_passes():
    rec = validation.check_dominance_recovery()
    assert rec["name"] == "dominance_recovery"
    assert rec["passed"] is True, rec["detail"]


def test_check_water_candidate_blocked_passes():
    rec = validation.check_water_candidate_blocked()
    assert rec["name"] == "water_candidate_blocked"
    assert rec["passed"] is True, rec["detail"]


def test_check_curvature_zero_on_plane_passes():
    """Every curvature descriptor vanishes on a tilted plane."""
    rec = validation.check_curvature_zero_on_plane()
    assert rec["name"] == "curvature_zero_on_plane"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert max(abs(m["profile"]), abs(m["plan"]), abs(m["mean"])) < 1e-6, m


def test_check_vrm_discriminates_roughness_passes():
    """VRM is ~0 on a plane and strictly increases with roughness amplitude,
    always bounded in [0, 1]."""
    rec = validation.check_vrm_discriminates_roughness()
    assert rec["name"] == "vrm_discriminates_roughness"
    assert rec["passed"] is True, rec["detail"]
    seq = rec["metrics"]["sequence"]
    assert seq[0] <= 1e-9, seq
    assert all(seq[i] < seq[i + 1] for i in range(len(seq) - 1)), seq
    assert all(0.0 <= s <= 1.0 for s in seq), seq


def test_check_roughness_hurst_sane_passes():
    """Hurst exponent ~1 for a smooth ramp, <0.1 for white noise."""
    rec = validation.check_roughness_hurst_sane()
    assert rec["name"] == "roughness_hurst_sane"
    assert rec["passed"] is True, rec["detail"]
    assert abs(rec["metrics"]["hurst_ramp"] - 1.0) < 1e-6, rec["metrics"]
    assert rec["metrics"]["hurst_noise"] < 0.1, rec["metrics"]


def test_monotonic_roughness_metric_strictly_increases():
    """Rougher candidates sit farther on the ruggedness axis — the engine has
    real discriminating power."""
    rec = _find(_report(), "monotonic_roughness_discrimination")
    rug = rec["metrics"]["ruggedness"]
    assert isinstance(rug, list) and len(rug) >= 2, rug
    assert all(rug[i] < rug[i + 1] for i in range(len(rug) - 1)), rug


def test_dominance_recovery_metric_rank_and_detail():
    """Closer candidate is Pareto layer 1 (and recommended); farther one is
    layer >= 2."""
    rec = _find(_report(), "dominance_recovery")
    rank = rec["metrics"]["rank"]
    assert rank["near"] == 1, rank
    assert rank["far"] >= 2, rank
    assert "recommended=near" in rec["detail"], rec["detail"]


def test_check_openness_flat_passes():
    """Flat plane: positive and negative openness are 90 deg everywhere."""
    rec = validation.check_openness_flat()
    assert rec["name"] == "openness_flat"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["positive_dev"] < 1e-6 and m["negative_dev"] < 1e-6, m


def test_check_openness_peak_passes():
    """Cone apex: positive openness > 90 and negative openness < 90."""
    rec = validation.check_openness_peak()
    assert rec["name"] == "openness_peak"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["positive"] > 90.0 > rec["metrics"]["negative"], rec["metrics"]


def test_check_openness_pit_mirror_passes():
    """Bowl centre mirrors a peak: negative openness > 90 and positive < 90."""
    rec = validation.check_openness_pit_mirror()
    assert rec["name"] == "openness_pit_mirror"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["negative"] > 90.0 > rec["metrics"]["positive"], rec["metrics"]


def test_check_geomorphon_flat_passes():
    """Flat plane is classified 'flat' almost everywhere."""
    rec = validation.check_geomorphon_flat()
    assert rec["name"] == "geomorphon_flat"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["flat_fraction"] > 0.95, rec["metrics"]
    assert rec["metrics"]["dominant"] == "flat", rec["metrics"]


def test_check_geomorphon_cone_peak_passes():
    """Cone apex classifies as 'peak' (FORM_NAMES index 1)."""
    rec = validation.check_geomorphon_cone_peak()
    assert rec["name"] == "geomorphon_cone_peak"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["form"] == "peak", rec["metrics"]
    assert rec["metrics"]["code"] == 1, rec["metrics"]


def test_check_geomorphon_bowl_pit_passes():
    """Bowl centre classifies as 'pit' (the antisymmetric mirror of the apex)."""
    rec = validation.check_geomorphon_bowl_pit()
    assert rec["name"] == "geomorphon_bowl_pit"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["form"] == "pit", rec["metrics"]


def test_check_geomorphon_tilt_slope_passes():
    """A uniform planar tilt is dominated by 'slope'."""
    rec = validation.check_geomorphon_tilt_slope()
    assert rec["name"] == "geomorphon_tilt_slope"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["dominant"] == "slope", rec["metrics"]


def test_check_geomorphon_relief_invariance_passes():
    """Landform composition is exactly invariant to a +100 m vertical offset."""
    rec = validation.check_geomorphon_relief_invariance()
    assert rec["name"] == "geomorphon_relief_invariance"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["forms"] >= 1, rec["metrics"]


def test_new_significance_confidence_checks_present_and_pass():
    """The four significance / decision-confidence oracles are registered in the
    report and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _SIG_CONF_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_significance_clear_winner_passes():
    """A clear single winner's recommendation is permutation-significant and the
    recommended unit is the closer candidate ('near')."""
    rec = validation.check_significance_clear_winner()
    assert rec["name"] == "significance_clear_winner"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["recommended"] == "near", rec["metrics"]
    assert rec["metrics"]["recommendation_significant"] is True, rec["metrics"]


def test_check_significance_near_tie_is_honest_passes():
    """A near-tie is reported honestly: not a lone recommendation, or the
    recommendation is NOT significant (no manufactured significance)."""
    rec = validation.check_significance_near_tie_is_honest()
    assert rec["name"] == "significance_near_tie_is_honest"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["state"] != "RECOMMEND_FOLLOW_UP" or m["recommendation_significant"] is False, m


def test_check_confidence_robust_on_clear_winner_passes():
    """Clear winner -> 'robust' verdict with bootstrap + significance both
    evaluated and positive (a documented rule over per-signal classes, no score)."""
    rec = validation.check_confidence_robust_on_clear_winner()
    assert rec["name"] == "confidence_robust_on_clear_winner"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["verdict"] == "robust", rec["metrics"]
    assert rec["metrics"]["significant"] is True, rec["metrics"]


def test_check_confidence_fragile_or_tie_on_near_tie_passes():
    """Near-tie -> the decision confidence is NEVER 'robust' (fragile/qualified/
    tie/indeterminate only)."""
    rec = validation.check_confidence_fragile_or_tie_on_near_tie()
    assert rec["name"] == "confidence_fragile_or_tie_on_near_tie"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["verdict"] != "robust", rec["metrics"]
    assert rec["metrics"]["verdict"] in {"fragile", "qualified", "tie",
                                         "indeterminate"}, rec["metrics"]
