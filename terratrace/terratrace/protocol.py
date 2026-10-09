"""Draft research-study protocol generator.

The protocol is explicitly a DRAFT. It describes what a terrestrial study
would need to measure next; it is not a permit, a safety approval, or an
authorized test plan.
"""
from __future__ import annotations


def draft_protocol(result_state, recommended_unit, profile, gap_ledger):
    objective = {
        "RECOMMEND_FOLLOW_UP": (
            "Design a map-scale terrain follow-up study at the recommended "
            "candidate unit to investigate the declared morphology hypothesis."),
        "TIE": (
            "Collect discriminating data because current evidence does not "
            "separate the candidate units."),
        "INDETERMINATE": (
            "Resolve sensitivity: the ranking depends on declared assumptions."),
        "NOT_COMPARABLE": (
            "Establish a comparable common support before any ranking."),
        "BLOCKED": (
            "Resolve data, rights, or access status before proceeding."),
    }.get(result_state, "Clarify the study question and evidence.")

    return {
        "status": "draft",
        "authorization": "NOT_AUTHORIZED: access, ecology, and safety unverified",
        "result_state": result_state,
        "recommended_unit": recommended_unit,
        "objective": objective,
        "hypothesis": (
            "At the declared common support, candidate terrain reproduces the "
            "reference slope/relief/ruggedness/connectivity distributions "
            "within stated tolerances."),
        "measurements_required_next": [
            "higher-resolution terrain survey to assess sub-support structure",
            "surface material/geotechnical characterization (separate study)",
            "illumination and visibility modelling (separate study)",
            "field access, ecological, and community authorization review",
        ],
        "acceptance_criteria": [
            "feature distributions within predeclared tolerance at common support",
            "result stable across declared sensitivity scenarios",
            "no eligibility blocker (data, rights, ecology, safety)",
        ],
        "rejection_criteria": [
            "ranking reverses under reasonable support/threshold changes",
            "valid-data fraction below declared minimum",
            "access or governance status cannot be verified",
        ],
        "stop_conditions": [
            "permission not granted",
            "protected-area or community constraint",
            "safety or environmental risk",
        ],
        "transfer_boundary": gap_ledger["note"],
        "profile": profile,
    }
