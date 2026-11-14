"""The ensemble record must be checkable — and the checker must be able to fail.

The test these replace contained `assert abs(...) >= 0`, which is true for every real number. A
checker that cannot fail is decoration, so every invariant in `terratrace/evidence.py` is exercised
here against a deliberately corrupted record.
"""
import copy
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from terratrace import evidence                                     # noqa: E402

V2 = _ROOT / "artifacts" / "lunar_sites_v2" / "lunar_sites_v2.json"
V1 = _ROOT / "artifacts" / "lunar_sites" / "lunar_sites_exploratory.json"


def _good():
    """A small, internally consistent ensemble: 6 draws, candidate X on layer 1 in all six."""
    return {
        "n_draws": 6,
        "n_realisations": 6,
        "site": "Site01",
        "scales": {
            "500m": {
                "point_estimate_layer1": ["x"],
                "exact_set_match_count": 6,
                "exact_set_match_fraction": 1.0,
                "candidate_layer1_count": {"x": 6},
                "candidate_layer1_frequency": {"x": 1.0},
                "layer1_set_counts": {"x": 6},
                "distinct_layer1_sets": 1,
            }
        },
    }


def test_a_consistent_record_is_accepted():
    assert evidence.check_ensemble_counts(_good()) == []


def test_a_count_that_disagrees_with_its_frequency_is_detected():
    bad = _good()
    bad["scales"]["500m"]["candidate_layer1_count"]["x"] = 5      # frequency still says 1.0
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "a count contradicting its own frequency passed"
    assert any("frequency" in p for p in problems), problems


def test_a_frequency_that_could_not_come_from_the_draws_is_detected():
    bad = _good()
    bad["scales"]["500m"]["candidate_layer1_count"]["x"] = 6
    bad["scales"]["500m"]["candidate_layer1_frequency"]["x"] = 0.5   # 3 of 6, not 6 of 6
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "an impossible frequency passed"
    assert any("frequency" in p for p in problems), problems


def test_a_missing_candidate_is_detected():
    bad = _good()
    bad["scales"]["500m"]["candidate_layer1_count"]["y"] = 2
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "a candidate present in counts but absent from frequencies passed"
    assert any("different candidates" in p for p in problems), problems


def test_set_counts_that_do_not_sum_to_the_draws_are_detected():
    bad = _good()
    bad["scales"]["500m"]["layer1_set_counts"] = {"x": 4}         # 4 of 6 draws accounted for
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "an ensemble losing two draws passed"
    assert any("realisations" in p for p in problems), problems


def test_an_impossible_membership_count_is_detected():
    bad = _good()
    bad["scales"]["500m"]["candidate_layer1_count"]["x"] = 7      # more draws than exist
    bad["scales"]["500m"]["candidate_layer1_frequency"]["x"] = 7 / 6
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "a candidate on layer 1 in 7 of 6 draws passed"
    assert any("impossible" in p for p in problems), problems


def test_membership_counts_must_match_the_recorded_sets():
    bad = _good()
    # every draw's set has two members, so the sets imply 12 member slots, but only 6 are recorded
    bad["scales"]["500m"]["layer1_set_counts"] = {"x+y": 6}
    bad["scales"]["500m"]["point_estimate_layer1"] = ["x"]
    bad["scales"]["500m"]["exact_set_match_count"] = 0
    bad["scales"]["500m"]["exact_set_match_fraction"] = 0.0
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "6 membership slots against sets implying 12 passed"
    assert any("member slots" in p for p in problems), problems


def test_a_record_without_counts_is_refused_rather_than_guessed():
    """Fractions alone cannot be checked, and the checker says so instead of passing them."""
    bad = _good()
    del bad["scales"]["500m"]["candidate_layer1_count"]
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "a frequencies-only record was accepted by the count checker"
    assert any("cannot be checked" in p for p in problems), problems


def test_an_inconsistent_draw_count_is_detected():
    bad = _good()
    bad["n_realisations"] = 5
    problems = evidence.check_ensemble_counts(bad)
    assert problems, "n_realisations disagreeing with n_draws passed"


def test_the_frequency_only_checker_detects_impossible_fractions():
    """v1 stores no counts, but a fraction that is not a whole number of draws is still wrong."""
    ok = {"n_draws": 6, "scales": {"500m": {"candidate_layer1_frequency": {"x": 1.0},
                                            "exact_match_fraction": 1.0}}}
    assert evidence.check_frequency_only_ensemble(ok) == []
    # 0.7 of 6 draws is 4.2 draws, which no draw count can produce. (0.5 of 6 is 3 draws and is
    # perfectly legal -- that was the first version of this test, and it was wrong.)
    bad = {"n_draws": 6, "scales": {"500m": {"candidate_layer1_frequency": {"x": 0.7},
                                             "exact_match_fraction": 1.0}}}
    problems = evidence.check_frequency_only_ensemble(bad)
    assert problems, "0.7 of 6 draws passed the frequency-only checker"
    assert any("whole number" in p for p in problems), problems


def test_the_committed_records_pass_their_own_checks():
    """The real artifacts, checked with the same code the producing script runs."""
    if V2.exists():
        v2 = json.loads(V2.read_text(encoding="utf-8"))
        assert evidence.check_ensemble_counts(v2["ensemble"]) == []
        assert v2["ensemble"]["honest_label"].count("100") == 1, v2["ensemble"]["honest_label"]
    if V1.exists():
        v1 = json.loads(V1.read_text(encoding="utf-8"))
        assert evidence.check_frequency_only_ensemble(v1["ensemble"]) == []


def test_corruption_of_the_real_record_is_detected():
    """The strongest version: take the committed v2 record and break one number in it."""
    if not V2.exists():
        return
    real = json.loads(V2.read_text(encoding="utf-8"))["ensemble"]
    assert evidence.check_ensemble_counts(real) == []
    bad = copy.deepcopy(real)
    scale = next(iter(bad["scales"]))
    candidate = next(iter(bad["scales"][scale]["candidate_layer1_count"]))
    bad["scales"][scale]["candidate_layer1_count"][candidate] -= 1
    problems = evidence.check_ensemble_counts(bad)
    assert problems, (
        f"decrementing {candidate}'s count in the committed record was not detected - the test "
        f"above would then be vacuous on the real data too")
