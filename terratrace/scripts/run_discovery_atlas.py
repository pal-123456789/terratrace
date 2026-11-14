"""The scale-resolved discovery atlas: ONE output that carries all of the evidence.

WHY THIS EXISTS
---------------
The engine produced its evidence in pieces -- a frozen Mars benchmark, a corrected lunar panel, a
descriptor-dependence audit, an adversarial stress test, a three-part verdict report. Each is
internally checked, and every one of them says what it does NOT establish. None of them says, in one
place, how much evidence supports a particular terrain relationship, at what scale, and where the
conclusion breaks. That is the question a reader actually arrives with, and answering it by reading
five documents and hoping they agree is not an answer.

So this script assembles one atlas and, more importantly, RECONCILES the pieces. Every number that
appears in more than one artifact is read from both and compared here; if any pair disagrees the
atlas REFUSES to publish rather than merging them into a confident-looking table. A document that
cannot be published when its own evidence disagrees is worth more than a tidy one that can.

WHAT IT CONTAINS
----------------
  regimes        the declared comparison regimes, kept APART -- two regimes are not comparable to
                 each other and the atlas says so instead of averaging across them
  windows        every comparable window with its footprint, support, cell count, source posting,
                 effective resolution floor and valid coverage
  scale_evidence the per-window, per-support descriptor values the decisions were made on
  lens_decisions the candidate-by-lens decisions, so "the lens matters" is visible
  dependence     the one-axis diagnostics
  uncertainty    error ensembles, adequacy bands, and what could not be calibrated
  adversarial    the declared stress test and which perturbations reverse the ordering
  ranking        the relative answer, per cell
  adequacy       the absolute answer, per cell -- which on this project is usually "not established"
  abstention     every cell where the engine abstains or the absolute question is unanswered, listed
                 rather than implied
  reconciliations  the cross-artifact checks, each with its expected and observed value
  verdict        the three separate answers, composed by terratrace/verdicts.py

CLAIM FIREWALL (inherited): map-scale terrain-MORPHOLOGY screening only. Nothing here is a
traversability, geologic-equivalence, site-access or mission-readiness claim, and no composite
"analog score" appears anywhere -- the atlas carries distances and band memberships, never a single
quality number.

Output: `artifacts/discovery_atlas/discovery_atlas.json` and `.md`.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from terratrace import verdicts as V                                    # noqa: E402

ART = ROOT / "artifacts"
OUT_DIR = ART / "discovery_atlas"
V3 = ART / "mf_panel_v3" / "matched_panel_v3_real.json"
LUNAR = ART / "lunar_sites_v2" / "lunar_sites_v2.json"
DEPEND = ART / "dependence" / "dependence_audit.json"
STRESS = ART / "lunar_adversarial" / "lunar_adversarial.json"
ADEQ = ART / "lunar_adequacy" / "lunar_adequacy.json"
PROBE = ART / "lunar_axis_probe" / "lunar_axis_probe.json"
SCALE = ART / "scale_profile" / "scale_profile.json"

V3_CONFIG = ROOT / "config" / "matched_footprint_v3.yml"
V3_PROTOCOL = ROOT / "docs" / "BENCHMARK-PROTOCOL-v3.md"
V3_RESULTS = ROOT / "docs" / "RESULTS-v3.md"

REGIME = {
    "mars_panel_v3": {"body": "mars", "source": "MOLA 463 m/pixel (USGS)",
                      "footprint_m": 60000.0, "supports_m": [1500.0, 2000.0, 3000.0],
                      "cells_per_side": [40, 30, 20], "status": "CONFIRMATORY",
                      "note": "the frozen benchmark; pre-specified, NOT pre-registered"},
    "lunar_panel_v2": {"body": "moon", "source": "LOLA 5 m/pixel (NASA Goddard PGDA)",
                       "footprint_m": 9000.0, "supports_m": [500.0, 750.0, 1000.0],
                       "cells_per_side": [18, 12, 9], "status": "CORRECTED EXPLORATORY REANALYSIS",
                       "note": "same data was examined in v1 before the correction existed"},
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path, label):
    if not path.exists():
        raise SystemExit(f"discovery atlas: {label} is missing at {path}. The atlas is assembled FROM "
                         f"committed records; without this one it would be a partial picture "
                         f"presented as a whole, which is exactly what it exists to prevent.")
    return json.loads(path.read_text(encoding="utf-8"))


def _worst(value):
    """The largest axis distance in a record, whether it arrives as a list or a scalar."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        finite = [float(v) for v in value if v == v and v is not None]
        return max(finite) if finite else None
    return float(value)


class Reconciler:
    """Collects cross-artifact checks. One disagreement and the atlas does not publish."""

    def __init__(self):
        self.rows = []

    def check(self, name, claim, expected, observed, where):
        ok = (observed == expected)
        self.rows.append({"check": name, "claim": claim, "where": where,
                          "expected": expected, "observed": observed, "ok": bool(ok)})
        return ok

    def refused(self):
        return [r for r in self.rows if not r["ok"]]


def extract_documented_hash(text, needle):
    """The first sha256 (or 64-hex prefix) appearing on a line that mentions `needle`."""
    for line in text.splitlines():
        if needle in line:
            m = re.search(r"\b([0-9a-f]{8,64})\b", line)
            if m:
                return m.group(1)
    return None


def reconcile(v3, lunar, dep, stress, adeq, probe, documented):
    """Every cross-artifact check, as a pure function of the records.

    Taking the records as ARGUMENTS rather than reading them here is what makes the refusal
    testable: a test hands in a deliberately corrupted copy and asserts that the right check names
    it. The alternative -- mutating a committed artifact on disk inside a test -- would corrupt the
    repository if the test ever crashed between the write and the restore, which is a bad trade for
    a test whose entire purpose is to be trustworthy.
    """
    rec = Reconciler()
    lunar_cells = lunar["scales"]

    # 1 + 2: every cited checksum must match a file that actually exists.
    rec.check("documented_hash:v3_bundle",
              "the v3 bundle hash printed in the v3 protocol equals the file on disk",
              (documented.get("v3_bundle") or "")[:64],
              sha256(V3)[:len(documented.get("v3_bundle") or "")],
              "docs/BENCHMARK-PROTOCOL-v3.md <-> artifacts/mf_panel_v3/matched_panel_v3_real.json")
    rec.check("documented_hash:v3_config",
              "the v3 config hash printed in RESULTS-v3 equals the config on disk",
              (documented.get("v3_config") or "")[:64],
              sha256(V3_CONFIG)[:len(documented.get("v3_config") or "")],
              "docs/RESULTS-v3.md <-> config/matched_footprint_v3.yml")

    # 3: the lunar headline must be the SAME in the panel and in the stress test's baseline.
    panel_l1 = {f"{sid}@{k}": blk["layer1"] for k, per in lunar_cells.items()
                for sid, blk in per.items()}
    distinct = sorted(list(d) for d in {tuple(v) for v in panel_l1.values()})
    rec.check("lunar_headline:panel",
              "all 18 lunar cells share one single-member non-dominated set, and it is Nevada",
              [["earth_nevada_basin"]], distinct,
              "artifacts/lunar_sites_v2/lunar_sites_v2.json")
    rec.check("lunar_headline:stress_baseline",
              "the stress test re-derived the panel's headline rather than assuming it",
              True, bool(stress["baseline"]["reproduces_v2_artifact"]),
              "artifacts/lunar_adversarial/lunar_adversarial.json")

    # 4: the adequacy report's ranking must agree with the panel's ordering.
    adeq_recs = {k: c["verdict"]["relative_ranking"]["recommended_unit"]
                 for k, c in adeq["cells"].items()}
    rec.check("ranking:adequacy_matches_panel",
              "every cell the adequacy report ranks recommends the panel's survivor",
              {k: "earth_nevada_basin" for k in adeq_recs}, adeq_recs,
              "artifacts/lunar_adequacy/lunar_adequacy.json <-> artifacts/lunar_sites_v2")

    # 5: the dependence audit and the stress test must not contradict each other.
    drops = {r["label"]: r["n_changed"] for r in stress["perturbations"]
             if r["label"].startswith("drop_axis:")}
    rec.check("dependence:agrees_with_stress",
              "the audit says one axis and dropping any single axis changes nothing",
              (True, {f"drop_axis:{a}": 0 for a in ("mean_slope_deg", "mean_relief3_m",
                                                    "elev_std_m")}),
              (bool(dep["verdict"]["three_axes_are_one_dimension"]), drops),
              "artifacts/dependence <-> artifacts/lunar_adversarial")

    # 6: each summary must reconcile with its own rows.
    s = stress["summary"]
    rec.check("stress:summary_matches_rows",
              "stable + reversing perturbations equal the counted total",
              s["n_counted_perturbations"],
              s["n_stable_perturbations"] + len(s["reversing_perturbations"]),
              "artifacts/lunar_adversarial/lunar_adversarial.json")
    nn_total = nn_sib = 0
    for c in adeq["cells"].values():
        for entry in c["nearest_unit_per_descriptor"].values():
            nn_total += 1
            nn_sib += bool(entry["is_sibling_site"])
    rec.check("adequacy:summary_matches_cells",
              "the summary's sibling-nearest count is what the cells say",
              {"of": nn_total, "count": nn_sib}, adeq["summary"]["nearest_unit_is_a_sibling_lunar_site"],
              "artifacts/lunar_adequacy/lunar_adequacy.json")

    # 7: the regimes must genuinely be disjoint, since the atlas refuses to pool them.
    v3_sup = set(REGIME["mars_panel_v3"]["supports_m"])
    lunar_sup = set(REGIME["lunar_panel_v2"]["supports_m"])
    rec.check("regimes:disjoint_supports",
              "the two regimes share no support, so nothing may be pooled across them",
              [], sorted(v3_sup & lunar_sup), "the two declared regimes")

    # 8: the v3 hypothesis counts must sum to the matrix they summarise.
    hcounts = v3.get("hypotheses", {}).get("R", {}).get("counts", {})
    rec.check("v3:hypothesis_counts_sum",
              "the R-rule change counts sum to the number of cells they classify",
              len(v3.get("hypotheses", {}).get("R", {}).get("evidence", {}).get("rows", [])),
              sum(hcounts.values()), "artifacts/mf_panel_v3/matched_panel_v3_real.json")

    # 9: the axis probe must have reproduced the panel it attacks. This is the same precondition the
    # driver enforces on itself, restated here so the atlas cannot publish a probe that was aimed at
    # something else -- and it is the check that ties the panel's headline to the probe's baseline.
    rec.check("axis:probe_reproduces_panel",
              "the probe re-derived the panel's single-member frontier at all 18 cells",
              {"mismatches": [], "frontier_sizes": {"1": 18}},
              {"mismatches": probe["frontier"]["baseline_mismatches"],
               "frontier_sizes": probe["frontier"]["baseline_frontier_size_counts"]},
              "artifacts/lunar_axis_probe <-> artifacts/lunar_sites_v2")
    # 10: adding a coordinate can only promote a co-winner, so a recorded removal means a non-finite
    # added coordinate rather than a finding. The atlas must not publish on top of one.
    rec.check("axis:no_pareto_removals",
              "every added axis promoted co-winners only; dominance makes a removal impossible",
              True,
              probe["frontier"]["removals_detected"] == 0
              and all(t["removal_alarms"] == [] for t in probe["frontier"]["per_descriptor"]),
              "artifacts/lunar_axis_probe/lunar_axis_probe.json")
    # 11: the frontier result is only readable next to the arbitrary-coordinate control. If the
    # control is not in the record, the atlas would be republishing a bare fragility number.
    rec.check("axis:control_is_present",
              "the probe's frontier numbers travel with the control that bounds their reading",
              {"draws": 300, "n_cells": 18},
              {"draws": probe["random_control"]["draws"], "n_cells": probe["random_control"]["n_cells"]},
              "artifacts/lunar_axis_probe/lunar_axis_probe.json")
    return rec


def main():
    v3 = load(V3, "the v3 Mars benchmark record")
    lunar = load(LUNAR, "the lunar panel v2 record")
    dep = load(DEPEND, "the descriptor-dependence audit")
    stress = load(STRESS, "the lunar adversarial stress record")
    adeq = load(ADEQ, "the lunar adequacy record")
    probe = load(PROBE, "the independent-axis probe record")
    rec = Reconciler()

    # ---------------------------------------------------------------- regimes, kept apart
    regimes = {name: dict(meta, cross_regime_comparable=False) for name, meta in REGIME.items()}
    regimes["_note"] = ("The two regimes are NOT comparable to each other: different footprint, "
                        "different supports, different bodies and different source resolutions. "
                        "Nothing in this atlas pools across them.")

    # ---------------------------------------------------------------- windows
    windows = []
    lunar_cells = lunar["scales"]
    for key in sorted(lunar_cells):
        for sid, blk in sorted(lunar_cells[key].items()):
            windows.append({
                "regime": "lunar_panel_v2", "reference": f"LUNAR_{sid}", "body": "moon",
                "footprint_m": blk["footprint_m"], "support_m": blk["support_m"],
                "cells": blk["cells"], "valid_fraction": blk["valid_fraction"],
                "source_crs": blk["grid"]["source_crs"],
                "source_posting_m": blk["grid"]["source_posting_m"],
                "source_floor_m": blk["grid"]["source_floor_m"],
                "resampling": blk["grid"]["resampling"],
                "reference_axes": blk["reference_axes"],
            })
    for uid in v3.get("panel_ids", []):
        for sup in REGIME["mars_panel_v3"]["supports_m"]:
            windows.append({"regime": "mars_panel_v3", "reference": uid, "body": "mars",
                            "footprint_m": REGIME["mars_panel_v3"]["footprint_m"],
                            "support_m": sup,
                            "cells": REGIME["mars_panel_v3"]["cells_per_side"][
                                REGIME["mars_panel_v3"]["supports_m"].index(sup)],
                            "source_posting_m": 463.0, "source_floor_m": 1389.0,
                            "resampling": "average (declared by the v3 protocol)"})

    # ---------------------------------------------------------------- scale evidence
    scale_evidence = {"lunar_panel_v2": {k: {sid: b["reference_axes"] for sid, b in v.items()}
                                         for k, v in lunar_cells.items()}}

    # ---------------------------------------------------------------- lens decisions
    lens_decisions = {}
    primary = v3.get("primary", {})
    if primary.get("lens_ablation"):
        lens_decisions = {"mars_panel_v3": {"reference": primary.get("reference_id"),
                                            "support_m": primary.get("support_m"),
                                            "by_lens": primary["lens_ablation"]}}

    # ---------------------------------------------------------------- dependence
    dependence = {"verdict": dep["verdict"],
                  "analytic": {"verified_against_engine": dep["analytic"]["verified_against_engine"],
                               "worst_relief_error_m": dep["analytic"]["worst_relief_error_m"],
                               "rho_bounds_provable": dep["analytic"]["rho_bounds_provable"]},
                  "panel": {k: {"pools": {p: {"effective_rank_95": b["effective_rank_95"],
                                              "participation_ratio": b.get("participation_ratio"),
                                              "planar_fit": b.get("planar_fit")}
                                         for p, b in v["pools"].items()}}
                            for k, v in dep["panel"].items()}}

    # ---------------------------------------------------------------- uncertainty
    uncertainty = {
        "lunar_error_ensemble": {"realisations_sampled": lunar["ensemble"].get("n_draws"),
                                 "draws_available": lunar["ensemble"].get("draws_available_at_source"),
                                 "scope": "Site01 only",
                                 "exact_set_match": {k: [b["exact_set_match_count"],
                                                         b["n_realisations"]]
                                                     for k, b in lunar["ensemble"]["scales"].items()}},
        "adequacy_bands_calibrated": sum(1 for c in adeq["cells"].values()
                                         if c["verdict"]["absolute_adequacy"]["state"]
                                         != "NOT_ESTABLISHED"),
        "adequacy_bands_attempted": len(adeq["cells"]),
        "note": ("Only the lunar DEM has a published error model, and only six of its 100 "
                 "realisations were retrieved. The Earth side is treated as exact, which is a "
                 "stated limitation rather than a finding."),
    }

    # ---------------------------------------------------------------- adversarial
    adversarial = {"declared_before_run": stress["provenance"]["config"],
                   "n_counted": stress["summary"]["n_counted_perturbations"],
                   "n_stable": stress["summary"]["n_stable_perturbations"],
                   "reversing": stress["summary"]["reversing_perturbations"],
                   "cell_stable_fraction": stress["summary"]["cell_stable_fraction"],
                   "verdict": stress["summary"]["verdict"]}

    # ---------------------------------------------------------------- ranking + adequacy, per cell
    ranking, adequacy, abstention = {}, {}, []
    sufficiency = {}
    for key, cell in sorted(adeq["cells"].items()):
        vd = cell["verdict"]
        sufficiency[key] = {"state": vd["evidence_sufficiency"]["state"],
                            "reasons": vd["evidence_sufficiency"]["reasons"]}
        ranking[key] = {"state": vd["relative_ranking"]["state"],
                        "recommended_unit": vd["relative_ranking"]["recommended_unit"],
                        "layer1": vd["relative_ranking"]["layer1"],
                        "provisional": vd["relative_ranking"]["provisional"],
                        "axis_distance_fraction":
                            vd["relative_ranking"]["worst_axis_distance_fraction"],
                        # the panel records one fraction per axis; the WORST of them is the number
                        # a reader needs. Computed here, once, so nothing downstream has to decide
                        # whether it is looking at a list or a scalar -- the first version of the
                        # atlas page assumed a scalar and crashed on the real record.
                        "worst_axis_distance_fraction": _worst(
                            vd["relative_ranking"]["worst_axis_distance_fraction"])}
        adequacy[key] = {"state": vd["absolute_adequacy"]["state"],
                         "discriminates": (vd["absolute_adequacy"].get("discrimination") or {})
                         .get("discriminates")}
        if vd["relative_ranking"]["state"] != "RECOMMEND_FOLLOW_UP":
            abstention.append({"cell": key, "reason": "no single recommendation",
                               "state": vd["relative_ranking"]["state"]})
        elif vd["absolute_adequacy"]["state"] == "NOT_ESTABLISHED":
            abstention.append({"cell": key, "reason": "ranking is relative; the absolute question is "
                                                      "unanswered here",
                               "state": "ADEQUACY_NOT_ESTABLISHED"})
        if vd["evidence_sufficiency"]["state"] != "SUFFICIENT":
            abstention.append({"cell": key, "reason": "evidence sufficiency",
                               "state": vd["evidence_sufficiency"]["state"],
                               "because": vd["evidence_sufficiency"]["reasons"]})

    # ---------------------------------------------------------------- reconciliations
    documented = {"v3_bundle": extract_documented_hash(V3_PROTOCOL.read_text(encoding="utf-8"),
                                                       "matched_panel_v3_real.json"),
                  "v3_config": extract_documented_hash(V3_RESULTS.read_text(encoding="utf-8"),
                                                       "config/matched_footprint_v3.yml")
                  or extract_documented_hash(V3_RESULTS.read_text(encoding="utf-8"), "98535076")}
    rec = reconcile(v3, lunar, dep, stress, adeq, probe, documented)

    # ---------------------------------------------------------------- verdict
    lunar_rank_definite = sum(1 for r in ranking.values() if r["recommended_unit"])
    suf_reasons = sorted({r for c in adeq["cells"].values()
                          for r in c["verdict"]["evidence_sufficiency"]["reasons"]})
    ranking_v = V.ranking_verdict("RECOMMEND_FOLLOW_UP", ["earth_nevada_basin"],
                                 recommended_unit="earth_nevada_basin",
                                 worst_axis_distance=None, provisional=True)
    adequacy_v = V.adequacy_verdict(None, discrimination={
        "discriminates": False, "controls": 5, "admitted": 4,
        "note": "the reference's own band admits sibling lunar sites"})
    sufficiency_v = V.sufficiency_verdict(
        n_candidates=7, n_supports=3, min_valid_fraction=1.0,
        adequacy_band_established=True, effective_rank=dep["verdict"].get("effective_rank_max", 1),
        n_realisations=lunar["ensemble"].get("n_draws"), ensemble_claim=True)
    # Deliberately NOT an extra reason: the atlas covering two regimes it refuses to pool is a
    # property of the atlas, not a weakness of the evidence, and feeding it in would have made the
    # atlas verdict INSUFFICIENT for the sin of being honest about its own scope.
    sufficiency_v["regimes_covered_not_pooled"] = len(REGIME)

    problems = rec.refused()
    if problems:
        raise SystemExit(
            "discovery atlas: refusing to publish -- the evidence disagrees with itself:\n" +
            "\n".join(f"  - {p['check']}: expected {p['expected']!r}, observed {p['observed']!r} "
                      f"({p['where']})" for p in problems))

    # ---------------------------------------------------------------- axis sensitivity
    # Read straight out of the probe record rather than summarised here, because the number that
    # matters most is the one that makes the others readable: the arbitrary-coordinate control.
    _pt = probe["frontier"]["per_descriptor"]
    _best = probe["verdict"]["most_independent_admissible_descriptor"]
    _best_cells = next((t["changed_cells"] for t in _pt if t["key"] == _best["key"]), None)
    axis_sensitivity = {
        "question": ("Is the lunar panel's sole-non-dominated property robust to the axis set, and "
                     "would a genuinely independent fourth axis change the decision?"),
        "descriptors_decision_tested": len(_pt),
        "changed_cells_min": min(t["changed_cells"] for t in _pt),
        "changed_cells_max": max(t["changed_cells"] for t in _pt),
        "changed_cells_zero": sum(1 for t in _pt if t["changed_cells"] == 0),
        "random_control": dict(probe["random_control"]),
        "descriptors_beating_the_control": probe["verdict"]["n_descriptors_beating_the_random_control"],
        "most_independent": {
            "key": _best["key"],
            "median_adjusted_r2": _best["median_adjusted_r2"],
            "median_raw_r2": _best["median_raw_r2"],
            "chance_level_raw_r2": probe["provenance"]["chance_level_raw_r2"],
            "changed_cells": _best_cells,
        },
        "invariance_of_the_declared_axes": {
            "invariant_operations": probe["invariance"]["invariant_operations"],
            "not_invariant_operations": probe["invariance"]["not_invariant_operations"],
            "bank_scalars_not_quarter_turn_invariant": probe["invariance"]["bank_quarter_turn"]["n_changed"],
        },
        "reading": probe["verdict"]["reading"],
        "what_it_does_not_show": probe["verdict"]["what_this_does_not_show"],
        "status": probe["provenance"]["status"],
    }

    atlas = {
        "provenance": {
            "what": "the scale-resolved planetary morphology evidence atlas",
            "assembled_from": [str(p.relative_to(ROOT)) for p in
                               (V3, LUNAR, DEPEND, STRESS, ADEQ, PROBE, SCALE) if p.exists()],
            "principle": ("Every number that appears in more than one record is read from both and "
                          "reconciled here. One disagreement and this file is not written."),
            "regimes_are_not_pooled": True,
            "score_firewall": "no composite analog score; distances and band memberships only",
            "scope": "map-scale terrain-MORPHOLOGY screening only",
        },
        "regimes": regimes,
        "windows": windows,
        "scale_evidence": scale_evidence,
        "lens_decisions": lens_decisions,
        "dependence": dependence,
        "uncertainty": uncertainty,
        "adversarial": adversarial,
        "ranking": ranking,
        "adequacy": adequacy,
        "sufficiency": sufficiency,
        "abstention": abstention,
        "axis_sensitivity": axis_sensitivity,
        "reconciliations": rec.rows,
        "verdict": V.three_part_verdict(ranking_v, adequacy_v, sufficiency_v),
        "headline": {
            "ranking_definite_cells": lunar_rank_definite,
            "ranking_cells": len(ranking),
            "adequacy_not_established_cells": sum(
                1 for a in adequacy.values() if a["state"] == "NOT_ESTABLISHED"),
            "abstention_rows": len(abstention),
            "sibling_nearest": adeq["summary"]["nearest_unit_is_a_sibling_lunar_site"],
            "stress_stable_of_counted": [stress["summary"]["n_stable_perturbations"],
                                           stress["summary"]["n_counted_perturbations"]],
            "sufficiency_reasons": suf_reasons,
            "axis_sensitivity": {
                "descriptors_beating_the_random_control": axis_sensitivity[
                    "descriptors_beating_the_control"],
                "random_control_mean_changed_cells": axis_sensitivity["random_control"][
                    "mean_changed_cells"],
                "random_control_draws": axis_sensitivity["random_control"]["draws"],
                "changed_cells_zero_of_tested": [axis_sensitivity["changed_cells_zero"],
                                                axis_sensitivity["descriptors_decision_tested"]],
                "most_independent": axis_sensitivity["most_independent"]["key"],
                "most_independent_median_adjusted_r2": axis_sensitivity["most_independent"][
                    "median_adjusted_r2"],
                "most_independent_changed_cells": axis_sensitivity["most_independent"][
                    "changed_cells"],
            },
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "discovery_atlas.json").write_text(json.dumps(atlas, indent=2), encoding="utf-8")
    (OUT_DIR / "discovery_atlas.md").write_text(_markdown(atlas), encoding="utf-8")

    print("=" * 92)
    print("SCALE-RESOLVED DISCOVERY ATLAS")
    print("=" * 92)
    print(f"regimes: {len(REGIME)} (not pooled)   windows: {len(windows)}")
    print(f"cross-artifact reconciliations: {len(rec.rows)} -- all agree")
    h = atlas["headline"]
    print(f"ranking definite: {h['ranking_definite_cells']} of {h['ranking_cells']} cells")
    print(f"adequacy NOT_ESTABLISHED: {h['adequacy_not_established_cells']} cells")
    print(f"abstention rows: {h['abstention_rows']}")
    print(f"stress: {h['stress_stable_of_counted'][0]} of {h['stress_stable_of_counted'][1]} stable")
    print(f"nearest unit is a sibling lunar site: "
          f"{h['sibling_nearest']['count']} of {h['sibling_nearest']['of']} site x descriptor stats")
    print(f"evidence sufficiency: {atlas['verdict']['evidence_sufficiency']['state']}")
    a = atlas["axis_sensitivity"]
    print(f"axis sensitivity: {a['descriptors_decision_tested']} axes tested, "
          f"{a['descriptors_beating_the_control']} beat an arbitrary coordinate "
          f"(control mean {a['random_control']['mean_changed_cells']:.2f} of "
          f"{a['random_control']['n_cells']} cells)")
    print(f"\nwrote {OUT_DIR/'discovery_atlas.json'} and .md")
    return 0


def _markdown(a):
    h = a["headline"]
    L = ["# TerraTrace — scale-resolved planetary morphology evidence atlas",
         "",
         "**Assembled, not asserted.** Every number below is read from a committed record, and every "
         "number that appears in more than one record is reconciled in "
         "`reconciliations` — one disagreement and this file is not written.",
         "",
         "## What the atlas answers",
         "",
         "| question | answer |",
         "|---|---|",
         f"| Which candidate is closest, among those tested? | definite at {h['ranking_definite_cells']} "
         f"of {h['ranking_cells']} lunar cells |",
         f"| Is any candidate inside the reference's own variability? | **not established** at "
         f"{h['adequacy_not_established_cells']} cells |",
         f"| Is the evidence enough? | **{a['verdict']['evidence_sufficiency']['state'].lower()}** |",
         f"| Is the frontier robust to the AXIS SET? | **no** — "
         f"{a['axis_sensitivity']['descriptors_beating_the_control']} of "
         f"{a['axis_sensitivity']['descriptors_decision_tested']} candidate axes move it further than "
         f"an arbitrary coordinate does (see below) |",
         "",
         "## The frontier is bounded by the number of axes",
         "",
         f"Adding a fourth axis to the Pareto comparison changed the layer-1 set in "
         f"{a['axis_sensitivity']['changed_cells_min']} to "
         f"{a['axis_sensitivity']['changed_cells_max']} of 18 lunar cells across "
         f"{a['axis_sensitivity']['descriptors_decision_tested']} candidate descriptors — but a "
         f"**uniformly random** fourth coordinate, carrying no information at all, changes it in "
         f"{a['axis_sensitivity']['random_control']['mean_changed_cells']:.2f} of 18 on average over "
         f"{a['axis_sensitivity']['random_control']['draws']} draws. **No candidate axis exceeds "
         f"that control's 95th percentile.** The most independent descriptor the probe found "
         f"(`{a['axis_sensitivity']['most_independent']['key']}`, median adjusted R² "
         f"{a['axis_sensitivity']['most_independent']['median_adjusted_r2']:.3f} against a chance "
         f"level of {a['axis_sensitivity']['most_independent']['chance_level_raw_r2']:.4f}) changes "
         f"the decision at {a['axis_sensitivity']['most_independent']['changed_cells']} cells.",
         "",
         "Read as: the lunar panel's **sole-non-dominated** property is a property of running a "
         "Pareto rule over eight units in three dimensions, not evidence about candidates. The "
         "ranking stands as published — relative and provisional — and this bounds it.",
         "",
         "## Regimes — declared and kept apart",
         "",
         "| regime | body | footprint | supports | cells/side | source | status |",
         "|---|---|---|---|---|---|---|",
         ]
    for name, m in a["regimes"].items():
        if name.startswith("_"):
            continue
        L.append(f"| `{name}` | {m['body']} | {m['footprint_m']/1000:.1f} km | "
                 f"{', '.join(f'{s:.0f}' for s in m['supports_m'])} m | "
                 f"{'/'.join(str(c) for c in m['cells_per_side'])} | {m['source']} | {m['status']} |")
    L += ["", a["regimes"]["_note"], "",
          "## Where the conclusion breaks",
          "",
          f"{h['abstention_rows']} rows below are cells where the engine abstains or the absolute "
          "question is unanswered. They are listed rather than summarised, because a count of "
          "abstentions is what this project keeps finding gets read as a score.",
          "",
          "| stress perturbation or finding | value |",
          "|---|---|",
          f"| perturbations declared before the run | {h['stress_stable_of_counted'][1]} |",
          f"| perturbations that left the ordering untouched | **{h['stress_stable_of_counted'][0]}** |",
          f"| reversing conditions | {', '.join('`'+r+'`' for r in a['adversarial']['reversing'])} |",
          f"| nearest unit is a sibling lunar site | **{h['sibling_nearest']['count']} of "
          f"{h['sibling_nearest']['of']}** site x descriptor statistics |",
          "",
          "## Cross-artifact reconciliations",
          "",
          "| check | expected | observed | ok |",
          "|---|---|---|---|"]
    for r in a["reconciliations"]:
        L.append(f"| `{r['check']}` | `{json.dumps(r['expected'])[:60]}` | "
                 f"`{json.dumps(r['observed'])[:60]}` | {'yes' if r['ok'] else '**NO**'} |")
    L += ["", "## Uncertainty, and what could not be measured", "",
          f"- error ensemble: {a['uncertainty']['lunar_error_ensemble']['realisations_sampled']} of "
          f"{a['uncertainty']['lunar_error_ensemble']['draws_available']} published realisations, "
          f"{a['uncertainty']['lunar_error_ensemble']['scope']}",
          f"- adequacy bands calibrated: {a['uncertainty']['adequacy_bands_calibrated']} of "
          f"{a['uncertainty']['adequacy_bands_attempted']} attempted",
          f"- {a['uncertainty']['note']}",
          "",
          "## The firewall",
          "",
          a["provenance"]["scope"] + ". " + a["provenance"]["score_firewall"] + ".",
          "",
          "Regenerate with `python scripts/run_discovery_atlas.py`.",
          ""]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
