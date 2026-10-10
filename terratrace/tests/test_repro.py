"""Reproducibility-verifier fixtures (integrity tooling, no new claims)."""
from terratrace import repro, study

CANONICAL_HASH = "8f4890777ee462a2266c053d2e498ccdd7c133ddc5a101d36988331fa7da8167"


def test_verify_hash_matches_for_authentic_package():
    pkg = study.run_study()
    v = repro.verify_hash(pkg)
    assert v["match"] is True
    assert v["stored"] == v["recomputed"]
    assert v["stored"] == pkg["package_hash"]


def test_tampered_value_breaks_hash_match():
    # Mutate a nested/top-level value WITHOUT refreshing package_hash.
    pkg = study.run_study()
    pkg["result_state"] = "X"
    v = repro.verify_hash(pkg)
    assert v["match"] is False
    assert v["recomputed"] != v["stored"]


def test_missing_package_hash_is_handled():
    pkg = study.run_study()
    pkg.pop("package_hash", None)
    v = repro.verify_hash(pkg)
    assert v["stored"] is None
    assert v["match"] is False
    # recompute still succeeds and yields a 64-char hex digest.
    assert len(v["recomputed"]) == 64
    int(v["recomputed"], 16)


def test_identical_packages_have_empty_diff():
    a = study.run_study()
    b = study.run_study()
    assert repro.diff_packages(a, b) == []


def test_diff_lists_exactly_the_mutated_key():
    a = study.run_study()
    b = study.run_study()
    b["result_state"] = "MUTATED"
    assert repro.diff_packages(a, b) == ["result_state"]


def test_diff_restricted_to_given_keys():
    a = study.run_study()
    b = study.run_study()
    b["result_state"] = "MUTATED"
    # Restricting away the changed key hides the difference.
    assert repro.diff_packages(a, b, keys=["profile"]) == []
    assert repro.diff_packages(a, b, keys=["profile", "result_state"]) == ["result_state"]


def test_synthetic_study_is_reproducible():
    r = repro.verify_synthetic_reproducible()
    assert r["match"] is True
    assert isinstance(r["hash"], str)
    assert len(r["hash"]) == 64
    int(r["hash"], 16)  # valid hex


def test_canonical_hash_locks_reproducibility():
    # Locks the published synthetic study hash. The match-based checks above
    # stand on their own if a given environment yields a different (but still
    # deterministic) value.
    assert repro.recompute_hash(study.run_study()) == CANONICAL_HASH
    assert repro.verify_synthetic_reproducible()["hash"] == CANONICAL_HASH
