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
)

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
    """The engine is scientifically correct: all 8 checks pass."""
    report = _report()
    assert report["all_passed"] is True
    assert report["passed"] == 8
    assert report["failed"] == 0
    assert len(report["checks"]) == 8
    assert isinstance(report["package_hash"], str)
    assert report["package_hash"], "package_hash must be a non-empty string"


def test_every_check_record_shape_and_names():
    """Each record has name/passed/detail/metrics, passes, and the 8 names are
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
    assert len(names) == 8
    assert len(set(names)) == 8, f"duplicate check names: {names}"
    assert set(names) == set(_EXPECTED_NAMES), set(names) ^ set(_EXPECTED_NAMES)


def test_run_validation_is_deterministic():
    """Two independent runs agree on package_hash and every per-check outcome."""
    first = _report()
    second = validation.run_validation()
    assert first["package_hash"] == second["package_hash"]
    outcomes_a = {c["name"]: c["passed"] for c in first["checks"]}
    outcomes_b = {c["name"]: c["passed"] for c in second["checks"]}
    assert outcomes_a == outcomes_b


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
