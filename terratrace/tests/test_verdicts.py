"""The three-part verdict: ranking, adequacy, sufficiency -- and that they stay separate.

The tests below come in two halves.

The FIRST half is the rules: unknown states are refused, a missing band cannot be promoted to an
adequate verdict, a band that admits known-different terrain is demoted rather than reported as a
positive, and the sufficiency reasons are the declared ones.

The SECOND half is the property that actually matters, and it is a *negative* property: it must be
impossible for the ranking to be read as adequacy. So the tests check that the composition keeps all
three answers visible when they disagree -- a definite ranking next to NOT_ESTABLISHED adequacy is a
normal outcome and must survive composition unreduced -- and that `conflation_errors` fires on each
way of collapsing them: a missing part, a smuggled composite score, an adequacy state with no band,
a recommended unit outside its own non-dominated set.

This module exists because the project withdrew a Mars claim by reading "non-dominated" as "a good
analog", and then published a lunar page whose survivor is 70 per cent away at one site. Both were
that same collapse. These tests are the guard against repeating it in code.
"""
import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from terratrace import verdicts as v                                  # noqa: E402

ARTIFACT = _ROOT / "artifacts" / "lunar_adequacy" / "lunar_adequacy.json"


def _ranking(state="RECOMMEND_FOLLOW_UP", unit="cand_a", layer1=("cand_a",)):
    return v.ranking_verdict(state, list(layer1), recommended_unit=unit)


def _suf(state="SUFFICIENT"):
    if state == "SUFFICIENT":
        return v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=True, effective_rank=3,
                                     n_realisations=100, ensemble_claim=True)
    raise AssertionError("helper only builds the SUFFICIENT case")


# ------------------------------------------------------------------ part 1: the rules

def test_an_unknown_ranking_state_is_refused():
    try:
        v.ranking_verdict("PROBABLY_FINE", ["a"], recommended_unit="a")
    except ValueError as exc:
        assert "unknown result_state" in str(exc)
    else:
        raise AssertionError("an undeclared result state must be refused, not carried through")


def test_adequacy_with_no_assessment_is_not_established_and_says_its_own_sentence():
    a = v.adequacy_verdict(None)
    assert a["state"] == "NOT_ESTABLISHED"
    assert a["adequate_candidates"] == []
    assert a["band"] is None
    assert a["note"].startswith("Absolute morphological adequacy has not been established")


def test_an_established_band_without_discrimination_is_reported_as_established():
    """The positive case must still exist, or the demotion rule below proves nothing."""
    ass = {"established": True, "any_adequate": True, "adequate_candidates": ["cand_a"],
           "per_descriptor": {"slope": {"established": True, "band": {"median": 0.1, "p95": 0.2}}}}
    a = v.adequacy_verdict(ass)
    assert a["state"] == "ESTABLISHED_ADEQUATE"
    assert a["adequate_candidates"] == ["cand_a"]


def test_a_band_that_admits_known_different_terrain_is_demoted_not_reported():
    """The rule this project actually needed on the lunar panel.

    A reference's own sub-window variability can be so wide that the band admits everything. A
    yardstick that calls every candidate adequate has established nothing, and reporting it as
    ESTABLISHED_ADEQUATE would be the false positive in its purest form.
    """
    ass = {"established": True, "any_adequate": True, "adequate_candidates": ["a", "b", "c"],
           "per_descriptor": {"slope": {"established": True, "band": {"median": 0.1, "p95": 9.0}}}}
    disc = v.band_discrimination([{"slope": 0.4}, {"slope": 0.5}, {"slope": 0.6}], {"slope": 9.0})
    assert disc["discriminates"] is False and disc["admitted"] == 3
    a = v.adequacy_verdict(ass, discrimination=disc)
    assert a["state"] == "NOT_ESTABLISHED", "a non-discriminating band must not yield adequacy"
    assert a["adequate_candidates"] == []
    assert "3 of 3" in a["note"] and "not evidence of similarity" in a["note"]


def test_discrimination_boundary_is_the_declared_fraction():
    three_above = [{"d": 0.1}, {"d": 5.0}, {"d": 6.0}, {"d": 7.0}]
    # one of four admitted = 0.25, under the default ceiling of 0.5 -> discriminates
    assert v.band_discrimination(three_above, {"d": 1.0})["discriminates"] is True
    # three of four admitted = 0.75 -> does not
    assert v.band_discrimination([{"d": 0.1}, {"d": 0.2}, {"d": 0.3}, {"d": 9.0}],
                                 {"d": 1.0})["discriminates"] is False
    # and the ceiling is a visible parameter, not a hidden constant
    assert v.band_discrimination([{"d": 0.1}, {"d": 0.2}, {"d": 0.3}, {"d": 9.0}], {"d": 1.0},
                                 max_admitted_fraction=1.0)["discriminates"] is True
    assert v.band_discrimination([], {"d": 1.0})["discriminates"] is None
    assert v.band_discrimination([{"d": 0.1}], {})["discriminates"] is None


def test_a_control_passing_one_descriptor_and_failing_another_is_not_admitted():
    """Membership means inside the band on EVERY established descriptor, same as adequacy itself."""
    disc = v.band_discrimination([{"slope": 0.1, "relief": 500.0}],
                                 {"slope": 1.0, "relief": 1.0})
    assert disc["admitted"] == 0 and disc["discriminates"] is True


def test_sufficiency_is_insufficient_when_the_comparison_barely_exists():
    for kwargs, why in [
        (dict(n_candidates=2, n_supports=3, min_valid_fraction=1.0), "candidates"),
        (dict(n_candidates=7, n_supports=1, min_valid_fraction=1.0), "support"),
        (dict(n_candidates=7, n_supports=3, min_valid_fraction=0.2), "coverage"),
    ]:
        s = v.sufficiency_verdict(**kwargs)
        assert s["state"] == "INSUFFICIENT", f"{why} should have made the evidence insufficient"
        assert s["reasons"]


def test_sufficiency_names_every_weak_evidenced_item_and_only_then_is_marginal():
    clean = v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=True, effective_rank=3,
                                  n_realisations=100, ensemble_claim=True)
    assert clean["state"] == "SUFFICIENT" and clean["reasons"] == []

    for kwargs, needle in [
        (dict(adequacy_band_established=False), "no adequacy band"),
        (dict(effective_rank=1), "single dimension"),
        (dict(n_realisations=6, ensemble_claim=True), "6 error realisations"),
        (dict(n_supports=2), "2 supports"),
    ]:
        base = dict(n_candidates=7, n_supports=3, min_valid_fraction=1.0,
                    adequacy_band_established=True, effective_rank=3, n_realisations=100,
                    ensemble_claim=True)
        base.update(kwargs)
        s = v.sufficiency_verdict(**base)
        assert s["state"] == "MARGINAL", f"{kwargs} should have made the evidence marginal"
        assert any(needle in r for r in s["reasons"]), f"{kwargs} -> {s['reasons']}"


def test_an_ensemble_claim_without_an_ensemble_is_marginal_even_with_a_big_one_elsewhere():
    s = v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=True, effective_rank=3,
                              n_realisations=None, ensemble_claim=True)
    assert s["state"] == "MARGINAL"
    assert any("error realisations" in r for r in s["reasons"])


# ------------------------------------------------------------------ part 2: they stay separate

def test_a_definite_ranking_beside_no_adequacy_survives_composition_unreduced():
    rank = v.ranking_verdict("RECOMMEND_FOLLOW_UP", ["earth_nevada_basin"],
                             recommended_unit="earth_nevada_basin")
    ade = v.adequacy_verdict(None)
    suf = v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=True, effective_rank=3,
                                n_realisations=100, ensemble_claim=True)
    vd = v.three_part_verdict(rank, ade, suf)
    assert vd["relative_ranking"]["state"] == "RECOMMEND_FOLLOW_UP"
    assert vd["relative_ranking"]["recommended_unit"] == "earth_nevada_basin"
    assert vd["absolute_adequacy"]["state"] == "NOT_ESTABLISHED"
    for key in v.QUESTIONS:
        assert key in vd, "composition dropped a part"
    assert "expected outcome" in vd["reading"]


def test_adequacy_without_a_ranking_is_also_composable():
    """The separation is not one-directional: a band can be calibrated while the field is a tie."""
    rank = v.ranking_verdict("TIE", ["a", "b"])
    ade = v.adequacy_verdict({"established": True, "any_adequate": False, "adequate_candidates": [],
                              "per_descriptor": {"slope": {"established": True,
                                                           "band": {"median": 0.1, "p95": 0.2}}}})
    suf = v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=True, effective_rank=3)
    vd = v.three_part_verdict(rank, ade, suf)
    assert vd["absolute_adequacy"]["state"] == "ESTABLISHED_NONE_ADEQUATE"
    assert vd["relative_ranking"]["state"] == "TIE"


def test_conflation_errors_catches_every_way_of_collapsing_the_three():
    rank = v.ranking_verdict("RECOMMEND_FOLLOW_UP", ["a"], recommended_unit="a")
    ade = v.adequacy_verdict(None)
    suf = v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=True, effective_rank=3)
    good = {"relative_ranking": rank, "absolute_adequacy": ade, "evidence_sufficiency": suf}
    assert v.conflation_errors(good) == []

    missing = {"relative_ranking": rank, "absolute_adequacy": ade}
    assert any("evidence_sufficiency is missing" in p for p in v.conflation_errors(missing))

    scored = dict(good, analog_score=0.87)
    assert any("composite score" in p for p in v.conflation_errors(scored))

    nested = dict(good, absolute_adequacy=dict(ade, summary={"overall": "fine"}))
    assert any("composite score" in p for p in v.conflation_errors(nested))

    bandless = dict(good, absolute_adequacy=dict(ade, state="ESTABLISHED_ADEQUATE"))
    assert any("no calibrated band" in p for p in v.conflation_errors(bandless))

    bogus = dict(good, relative_ranking=dict(rank, state="LOOKS_GOOD"))
    assert any("unknown ranking state" in p for p in v.conflation_errors(bogus))

    outside = dict(good, relative_ranking=dict(rank, recommended_unit="not_in_layer1"))
    assert any("not in its own non-dominated set" in p for p in v.conflation_errors(outside))

    contradictory = dict(good, relative_ranking=v.ranking_verdict("TIE", ["a", "b"],
                                                                  recommended_unit="a"))
    assert any("with a recommended unit" in p for p in v.conflation_errors(contradictory))


def test_composition_refuses_a_verdict_that_conflates():
    rank = v.ranking_verdict("TIE", ["a", "b"], recommended_unit="a")   # impossible pairing
    ade = v.adequacy_verdict(None)
    suf = v.sufficiency_verdict(7, 3, 1.0)
    try:
        v.three_part_verdict(rank, ade, suf)
    except ValueError as exc:
        assert "conflates" in str(exc)
    else:
        raise AssertionError("composition must refuse a contradictory verdict, not publish it")


def test_provisional_is_carried_but_the_ranking_is_never_deleted():
    s = v.sufficiency_verdict(7, 3, 1.0, adequacy_band_established=False, effective_rank=1,
                              n_realisations=6, ensemble_claim=True)
    assert s["state"] == "MARGINAL"
    rank = v.ranking_verdict("RECOMMEND_FOLLOW_UP", ["a"], recommended_unit="a",
                             provisional=s["state"] != "SUFFICIENT")
    assert rank["provisional"] is True
    assert rank["recommended_unit"] == "a" and rank["state"] == "RECOMMEND_FOLLOW_UP", (
        "poor evidence must mark a ranking provisional, never erase it -- deleting what was "
        "computed hides the computation rather than qualifying it")


# ------------------------------------------------------------------ the record

def test_the_lunar_adequacy_record_separates_the_three_and_says_so():
    assert ARTIFACT.exists(), (
        "artifacts/lunar_adequacy/lunar_adequacy.json is force-added; without it the published "
        "three-part separation has no evidence in the tree")
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    s = a["summary"]
    cells = list(a["cells"].values())
    assert s["n_cells"] == len(cells) == 18
    assert s["ranking_definite"] == 18, "the panel's ranking should still be definite everywhere"
    assert s["adequacy_not_established"] == 18, (
        "adequacy is now established somewhere, which contradicts the published statement that the "
        "reference's own band does not discriminate on this panel")
    assert s["sufficiency_states"] == ["MARGINAL"]
    for c in cells:
        vd = c["verdict"]
        assert v.conflation_errors(vd) == [], f"{c['site']}@{c['support_m']}: {vd}"
        assert vd["relative_ranking"]["provisional"] is True
        assert vd["absolute_adequacy"]["discrimination"]["discriminates"] is False


def test_the_sibling_nearest_finding_is_in_the_record_and_counted_from_the_cells():
    """The uncomfortable number has to be recomputed from the rows, not trusted as a summary."""
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    total = sib = 0
    for c in a["cells"].values():
        for entry in c["nearest_unit_per_descriptor"].values():
            total += 1
            sib += bool(entry["is_sibling_site"])
    assert a["summary"]["nearest_unit_is_a_sibling_lunar_site"] == {"of": total, "count": sib}
    assert sib == 18 and total == 24, (
        f"the sibling-nearest result moved to {sib} of {total}; that is a change in the finding and "
        f"must be reported, not absorbed")
    assert "closest to the Moon' is false" in a["summary"]["reading"]


def test_no_composite_score_is_published_anywhere_in_the_record():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, val in o.items():
                yield path + "/" + str(k)
                yield from walk(val, path + "/" + str(k))
        elif isinstance(o, (list, tuple)):
            for i, val in enumerate(o):
                yield from walk(val, f"{path}[{i}]")

    bad = [p for p in walk(a)
           if p.rsplit("/", 1)[-1].lower().strip("[]0123456789") in v.SCORE_LIKE_KEYS]
    assert bad == [], f"a composite score appears at {bad}"


def test_the_band_width_diagnostic_explains_the_demotion():
    """The record must let a reader check WHY the band failed, not just take the demotion on trust."""
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    c = a["cells"]["Site01@500m"]
    assert c["band_width_diagnostic"], "no band-width diagnostic was recorded"
    for desc, bw in c["band_width_diagnostic"].items():
        assert bw["band_p95"] > 0 and bw["max_candidate_distance"] > 0
        assert abs(bw["band_over_max"] - bw["band_p95"] / bw["max_candidate_distance"]) < 1e-9
    # and at least one descriptor's band is wide enough that it cannot be a useful yardstick
    assert any(bw["band_over_max"] > 1.0 for bw in c["band_width_diagnostic"].values())
