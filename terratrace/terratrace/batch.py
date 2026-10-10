"""Cross-reference, multi-lens batch studies.

A single study compares one Mars reference against a slate of Earth candidates.
Real analog screening is stronger when a candidate is tested against SEVERAL Mars
reference regions and under SEVERAL independent decision-axis sets (core /
extended / geomorphic). This module runs that grid and synthesises it:

For every (reference x decision-mode) cell it runs the full `compare_units`
pipeline and records each candidate's Pareto-layer rank, the result state, and
the recommendation. It then reports, per candidate, how often it is
non-dominated (Pareto layer 1) across all cells, how often it is the sole
recommendation, and a CONSENSUS shortlist of candidates that are non-dominated in
*every* cell -- i.e. robust to both the choice of Mars reference and the choice of
morphology lens.

This is a transparent robustness synthesis, NOT a composite "Mars-likeness"
score, and it inherits the engine's claim firewall: map-scale morphology only.
Pure NumPy + the engine; the array-level `run_batch` needs no network or rasterio
and is fully testable; `run_real_batch` loads real DEMs via the shared loader.
"""
from __future__ import annotations

import numpy as np

from . import study, provenance

DEFAULT_MODES = ("core", "extended", "geomorphic")


def run_batch(units, references, candidates, native_posting_m, target_support_m=100.0,
              min_valid=0.5, rights=None, decision_modes=DEFAULT_MODES, source_label="batch"):
    """Compare every candidate against every reference under every decision mode.

    units: {unit_id: 2-D elevation array} covering all references AND candidates.
    references / candidates: lists of ids present in `units`.
    native_posting_m: scalar or {id: metres}. Returns a hashed batch report.
    """
    if not references or not candidates:
        raise ValueError("need at least one reference and one candidate")
    rights = rights or {u: "verified_allowed" for u in units}
    cells = []
    for ref in references:
        raw = {ref: units[ref]}
        raw.update({c: units[c] for c in candidates})
        for mode in decision_modes:
            pkg = study.compare_units(
                raw, rights, native_posting_m, reference_id=ref,
                target_support_m=target_support_m, min_valid=min_valid,
                source_label=source_label, decision_metrics=mode)
            ranks = (pkg.get("frontier") or {}).get("rank", {})
            elig = pkg.get("eligibility", {})
            cells.append({
                "reference": ref, "mode": mode,
                "result_state": pkg["result_state"],
                "recommended_unit": pkg["recommended_unit"],
                "ranks": {c: ranks.get(c) for c in candidates},
                "eligible": {c: elig.get(c, {}).get("eligible") for c in candidates},
            })
    return _summarise(references, candidates, decision_modes, cells)


def _summarise(references, candidates, decision_modes, cells):
    """Aggregate the (reference x mode) cells into a per-candidate synthesis."""
    n_cells = len(cells)
    per_candidate = {}
    for c in candidates:
        ranked = [cell["ranks"].get(c) for cell in cells if cell["ranks"].get(c) is not None]
        layer1 = sum(1 for cell in cells if cell["ranks"].get(c) == 1)
        rec = sum(1 for cell in cells if cell["recommended_unit"] == c)
        per_candidate[c] = {
            "layer1_frequency": layer1 / n_cells if n_cells else 0.0,
            "recommended_frequency": rec / n_cells if n_cells else 0.0,
            "mean_layer": float(np.mean(ranked)) if ranked else float("nan"),
            "cells_ranked": len(ranked),
        }
    # Consensus: non-dominated (layer 1) in EVERY cell, and eligible/ranked in all.
    consensus = sorted(
        c for c in candidates
        if per_candidate[c]["cells_ranked"] == n_cells and per_candidate[c]["layer1_frequency"] == 1.0)
    # Robust ordering: most-often non-dominated first, then shallowest mean layer.
    ordering = sorted(
        candidates,
        key=lambda c: (-per_candidate[c]["layer1_frequency"],
                       per_candidate[c]["mean_layer"] if per_candidate[c]["cells_ranked"] else float("inf"),
                       c))
    report = {
        "suite": "terratrace-batch",
        "references": list(references),
        "candidates": list(candidates),
        "decision_modes": list(decision_modes),
        "n_cells": n_cells,
        "cells": cells,
        "per_candidate": per_candidate,
        "consensus_shortlist": consensus,
        "robust_ordering": ordering,
        "note": ("layer1_frequency = fraction of (reference x decision-mode) cells in which the "
                 "candidate is Pareto non-dominated (layer 1). consensus_shortlist = non-dominated "
                 "in EVERY cell (robust to reference and morphology lens). This is a transparent "
                 "robustness synthesis, NOT a composite Mars-likeness score; morphology only."),
    }
    report["package_hash"] = provenance.sha256_json(
        {k: v for k, v in report.items() if k != "package_hash"})
    return report


def run_real_batch(units, target_support_m=1000.0, min_valid=0.5, reproject=True,
                   decision_modes=DEFAULT_MODES, references=None):
    """Batch over REAL DEMs. `units` is the run_real_study unit-dict list; every
    unit with is_reference=True is a reference (or pass `references` explicitly),
    the rest are candidates. Requires rasterio."""
    raw, rights, native, ref_ids = study.load_real_units(units, target_support_m, reproject)
    refs = references if references is not None else ref_ids
    if not refs:
        raise ValueError("no references: set is_reference=True on >=1 unit or pass references=")
    candidates = [u for u in raw if u not in set(refs)]
    return run_batch(raw, refs, candidates, native, target_support_m=target_support_m,
                     min_valid=min_valid, rights=rights, decision_modes=decision_modes,
                     source_label="real_batch")
