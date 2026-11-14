"""The discovery atlas: it must reconcile, and it must REFUSE when the records disagree.

An atlas that merges five records into one confident-looking table is easy to write and worth
nothing, because the interesting failure is not a missing number -- it is two records that disagree
while both look well formed. So the property this file tests is not "the atlas has the right
numbers". It is "the atlas cannot publish when its evidence contradicts itself".

Every reconciliation is therefore exercised by CORRUPTING the record it reads and asserting that
that specific check names the disagreement. A check that no corruption can trip is decoration, and a
matrix test like this is the only way to tell the two apart.

The reconciliations take their records as ARGUMENTS, which is what makes this testable without
touching a single committed artifact on disk: a test that corrupts a file to test a corruption check
can leave the repository broken if it crashes between the write and the restore.
"""
import copy
import importlib.util
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))          # harness.py lives HERE, not in the package

from harness import require                                        # noqa: E402
from terratrace import verdicts as V                               # noqa: E402

_spec = importlib.util.spec_from_file_location("_atlas", _ROOT / "scripts" / "run_discovery_atlas.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

ARTIFACT = _ROOT / "artifacts" / "discovery_atlas" / "discovery_atlas.json"
MARKDOWN = _ROOT / "artifacts" / "discovery_atlas" / "discovery_atlas.md"


def _records():
    """Fresh copies of the five records the atlas reconciles."""
    return (json.loads(A.V3.read_text(encoding="utf-8")),
            json.loads(A.LUNAR.read_text(encoding="utf-8")),
            json.loads(A.DEPEND.read_text(encoding="utf-8")),
            json.loads(A.STRESS.read_text(encoding="utf-8")),
            json.loads(A.ADEQ.read_text(encoding="utf-8")))


DOCUMENTED = {"v3_bundle": A.sha256(A.V3), "v3_config": A.sha256(A.V3_CONFIG)}
ALL_CHECKS = {"documented_hash:v3_bundle", "documented_hash:v3_config",
              "lunar_headline:panel", "lunar_headline:stress_baseline",
              "ranking:adequacy_matches_panel", "dependence:agrees_with_stress",
              "stress:summary_matches_rows", "adequacy:summary_matches_cells",
              "regimes:disjoint_supports", "v3:hypothesis_counts_sum"}


# ------------------------------------------------------------------ it reconciles when they agree

def test_the_uncorrupted_records_reconcile_cleanly():
    rec = A.reconcile(*_records(), DOCUMENTED)
    bad = rec.refused()
    assert bad == [], f"the committed records already disagree: {bad}"
    assert {r["check"] for r in rec.rows} == ALL_CHECKS, (
        "the set of reconciliations changed; that is a change in what the atlas guarantees")


# ------------------------------------------------------------------ it refuses when they do not

def test_every_reconciliation_can_actually_fail():
    """The matrix. One corruption per check, each asserted to trip THAT check.

    A reconciliation that cannot be made to fail is not a check, it is a sentence. This is the only
    test in the suite whose purpose is to prove the other checks are real.
    """
    v3, lunar, dep, stress, adeq = _records()
    base = A.reconcile(v3, lunar, dep, stress, adeq, DOCUMENTED).refused()
    assert base == []

    def corrupt(check, mutate, documented=None):
        v3c, lunarc, depc, stressc, adeqc = copy.deepcopy((v3, lunar, dep, stress, adeq))
        args = [v3c, lunarc, depc, stressc, adeqc]
        mutate(*args)
        rec = A.reconcile(*args, documented or DOCUMENTED)
        failed = {r["check"] for r in rec.refused()}
        assert check in failed, (
            f"corrupting the record for {check} did not trip it; the checks that DID fail were "
            f"{sorted(failed) or 'none'} -- so {check} is not testing what it says")

    def _trip_lunar_panel(v3c, lunarc, depc, stressc, adeqc):
        lunarc["scales"]["500m"]["Site01"]["layer1"] = ["earth_nullarbor"]

    def _trip_stress_baseline(v3c, lunarc, depc, stressc, adeqc):
        stressc["baseline"]["reproduces_v2_artifact"] = False

    def _trip_ranking(v3c, lunarc, depc, stressc, adeqc):
        adeqc["cells"]["Site01@500m"]["verdict"]["relative_ranking"]["recommended_unit"] = None

    def _trip_dependence(v3c, lunarc, depc, stressc, adeqc):
        depc["verdict"]["three_axes_are_one_dimension"] = False

    def _trip_stress_summary(v3c, lunarc, depc, stressc, adeqc):
        stressc["summary"]["n_stable_perturbations"] += 1

    def _trip_adequacy_summary(v3c, lunarc, depc, stressc, adeqc):
        adeqc["summary"]["nearest_unit_is_a_sibling_lunar_site"]["count"] -= 1

    def _trip_hypotheses(v3c, lunarc, depc, stressc, adeqc):
        v3c["hypotheses"]["R"]["counts"]["unchanged"] += 1

    corrupt("lunar_headline:panel", _trip_lunar_panel)
    corrupt("lunar_headline:stress_baseline", _trip_stress_baseline)
    corrupt("ranking:adequacy_matches_panel", _trip_ranking)
    corrupt("dependence:agrees_with_stress", _trip_dependence)
    corrupt("stress:summary_matches_rows", _trip_stress_summary)
    corrupt("adequacy:summary_matches_cells", _trip_adequacy_summary)
    corrupt("v3:hypothesis_counts_sum", _trip_hypotheses)
    corrupt("documented_hash:v3_bundle", lambda *a: None,
            documented={"v3_bundle": "0" * 64, "v3_config": DOCUMENTED["v3_config"]})
    corrupt("documented_hash:v3_config", lambda *a: None,
            documented={"v3_bundle": DOCUMENTED["v3_bundle"], "v3_config": "0" * 64})

    # the regime check reads a module-level declaration, so it is corrupted there
    original = dict(A.REGIME)
    try:
        A.REGIME["mars_panel_v3"] = dict(A.REGIME["mars_panel_v3"], supports_m=[500.0, 750.0, 1000.0])
        rec = A.reconcile(v3, lunar, dep, stress, adeq, DOCUMENTED)
        assert "regimes:disjoint_supports" in {r["check"] for r in rec.refused()}, (
            "two regimes sharing a support must be caught, or 'nothing is pooled across them' is "
            "an assertion with no test behind it")
    finally:
        A.REGIME.clear()
        A.REGIME.update(original)


def test_the_refusal_is_loud_and_names_the_disagreement():
    v3, lunar, dep, stress, adeq = _records()
    stress["baseline"]["reproduces_v2_artifact"] = False
    bad = A.reconcile(v3, lunar, dep, stress, adeq, DOCUMENTED).refused()
    assert len(bad) == 1
    assert bad[0]["check"] == "lunar_headline:stress_baseline"
    assert bad[0]["expected"] is True and bad[0]["observed"] is False
    assert bad[0]["where"].endswith("lunar_adversarial.json"), (
        "a refusal has to point at the record that disagrees, or a reader cannot act on it")


# ------------------------------------------------------------------ the published record

def test_the_atlas_record_is_present_and_every_reconciliation_passed():
    require(ARTIFACT.exists(), "artifacts/discovery_atlas/discovery_atlas.json is force-added; the "
                              "published atlas has no evidence in the tree without it")
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert a["reconciliations"], "the atlas published with no reconciliations"
    failed = [r for r in a["reconciliations"] if not r["ok"]]
    assert failed == [], f"the atlas published with failing reconciliations: {failed}"
    assert {r["check"] for r in a["reconciliations"]} == ALL_CHECKS


def test_the_atlas_carries_every_section_it_claims_to():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    for key in ("regimes", "windows", "scale_evidence", "lens_decisions", "dependence",
                "uncertainty", "adversarial", "ranking", "adequacy", "abstention",
                "reconciliations", "verdict", "headline"):
        assert key in a, f"the atlas is missing {key}, so it is a partial picture presented as a whole"
    assert len(a["windows"]) >= 30
    assert a["abstention"], "an atlas with no abstention rows is not this project's atlas"


def test_the_headline_recomputes_from_the_sections_it_summarises():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    h = a["headline"]
    assert h["ranking_cells"] == len(a["ranking"])
    assert h["ranking_definite_cells"] == sum(1 for r in a["ranking"].values()
                                              if r["recommended_unit"])
    assert h["adequacy_not_established_cells"] == sum(1 for x in a["adequacy"].values()
                                                     if x["state"] == "NOT_ESTABLISHED")
    assert h["abstention_rows"] == len(a["abstention"])
    assert h["stress_stable_of_counted"][1] == a["adversarial"]["n_counted"]
    assert h["stress_stable_of_counted"][0] == a["adversarial"]["n_stable"]
    assert h["sibling_nearest"]["count"] < h["sibling_nearest"]["of"]


def test_the_two_regimes_are_declared_disjoint_and_pooled_nowhere():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    names = [k for k in a["regimes"] if not k.startswith("_")]
    assert len(names) == 2
    for name in names:
        assert a["regimes"][name]["cross_regime_comparable"] is False
    assert "NOT comparable" in a["regimes"]["_note"]
    supports = [set(a["regimes"][n]["supports_m"]) for n in names]
    assert not (supports[0] & supports[1]), "the regimes share a support; nothing stops pooling them"
    # and the windows must be labelled by regime, so no reader can pool them by accident
    assert {w["regime"] for w in a["windows"]} == set(names)


def test_the_atlas_verdict_is_separable_and_carries_no_composite():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert V.conflation_errors(a["verdict"]) == []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, val in o.items():
                yield path + "/" + str(k)
                yield from walk(val, path + "/" + str(k))
        elif isinstance(o, (list, tuple)):
            for i, val in enumerate(o):
                yield from walk(val, f"{path}[{i}]")

    bad = [p for p in walk(a)
           if p.rsplit("/", 1)[-1].lower().strip("[]0123456789") in V.SCORE_LIKE_KEYS]
    assert bad == [], f"a composite score appears in the atlas at {bad}"


def test_the_adequate_count_is_what_the_reasons_say_it_is():
    """The atlas must not claim sufficiency it does not have, nor hide the reasons it lacks it."""
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    s = a["verdict"]["evidence_sufficiency"]
    if s["state"] != "SUFFICIENT":
        assert s["reasons"], "a verdict short of SUFFICIENT must name what was missing"
    assert a["uncertainty"]["adequacy_bands_calibrated"] == 0, (
        "the atlas says an adequacy band was calibrated; the lunar panel's bands all failed the "
        "discrimination test, so that number must be zero or the two records disagree")
    assert a["adequacy"], "no per-cell adequacy was recorded"


def test_the_generated_report_quotes_the_atlas_rather_than_restating_it():
    require(MARKDOWN.exists(), "the atlas markdown was not written alongside the json")
    md = MARKDOWN.read_text(encoding="utf-8")
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    h = a["headline"]
    assert f"definite at {h['ranking_definite_cells']} of {h['ranking_cells']} lunar cells" in md
    assert f"not established** at {h['adequacy_not_established_cells']} cells" in md
    assert f"{h['abstention_rows']} rows below" in md
    assert f"{h['stress_stable_of_counted'][1]} " in md
    for r in a["reconciliations"]:
        assert f"`{r['check']}`" in md, f"the report omits the reconciliation {r['check']}"
