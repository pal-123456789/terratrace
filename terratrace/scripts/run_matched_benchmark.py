#!/usr/bin/env python3
"""Reproducible matched-footprint benchmark experiment for TerraTrace.

This is the Milestone-2 experiment runner. The ``--synthetic`` path is the frozen,
offline METHOD-VALIDATION experiment: it plants a known footprint confound (a rough
core inside a smooth apron) and shows that a matched-footprint comparison recovers
the correct analog while a mismatched comparison does not. It writes a machine-
readable evidence bundle (JSON) and prints a readable summary.

    python scripts/run_matched_benchmark.py --synthetic --out artifacts/mf_bench

The REAL Mars-Earth path (``--config``) is the scientific-discovery experiment and
requires rasterio + the cached DEMs on a networked machine; its protocol is frozen
in docs/BENCHMARK-PROTOCOL.md and config/matched_footprint.example.yml. The real
runner (windowed reprojected crops) is the next build and is NOT stubbed here as if
complete -- running --config prints exactly what is needed.

Scope / claim firewall: map-scale terrain-morphology screening only -- not a
traversability, geologic-equivalence, site-access, or mission-readiness claim.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import matched_benchmark as mb, synthetic

# Frozen synthetic scene (identical to tests/test_matched_benchmark.py).
_N = 400
_DX = 30.0
_CORE_RADIUS_M = 700.0
_SMALL = 1200.0
_LARGE = 12000.0
_SUPPORT = 90.0


def _scene():
    ii, jj = np.indices((_N, _N))
    r = np.hypot(ii - _N // 2, jj - _N // 2) * _DX
    core = r < _CORE_RADIUS_M
    X = synthetic.rough_field((_N, _N), amplitude=25.0, seed=1)
    Y = synthetic.rough_field((_N, _N), amplitude=4.0, seed=1)
    return {"ref": np.where(core, X, Y),
            "A_smooth": synthetic.rough_field((_N, _N), amplitude=4.0, seed=2),
            "B_rough": synthetic.rough_field((_N, _N), amplitude=25.0, seed=3)}


def run_synthetic(out):
    units = _scene()
    small = mb.matched_cell(units, _DX, "ref", _SMALL, _SUPPORT, decision_metrics="core",
                            n_boot=120, bootstrap_method="block", block_size=4)
    large = mb.matched_cell(units, _DX, "ref", _LARGE, _SUPPORT, decision_metrics="core")
    mism = mb.mismatched_cell(units, _DX, "ref", _LARGE, _SMALL, _SUPPORT, decision_metrics="core")
    baselines = {d: mb.single_descriptor_baseline(units, _DX, "ref", _SMALL, _SUPPORT, descriptor=d)
                 for d in ("slope", "relief")}
    ablation = mb.lens_ablation_matched(units, _DX, "ref", _SMALL, _SUPPORT)
    grid = mb.extent_support_grid(units, _DX, "ref",
                                  extents=[_SMALL, 2400.0, 4800.0, _LARGE],
                                  supports=[90.0, 150.0, 300.0], decision_metrics="core")

    print("=" * 74)
    print("TerraTrace matched-footprint benchmark -- SYNTHETIC method validation")
    print("=" * 74)
    print("Ground truth: reference has a ROUGH core (amp 25) in a SMOOTH apron (amp 4);")
    print("for the core AOI, B_rough is the correct analog.\n")
    print(f"matched   @ core extent {_SMALL:>6.0f} m  -> {small['result_state']:20s} rec={small['recommended_unit']}")
    print(f"matched   @ large     {_LARGE:>6.0f} m  -> {large['result_state']:20s} rec={large['recommended_unit']}")
    print(f"MISMATCHED ref{_LARGE:.0f}/cand{_SMALL:.0f} -> {mism['result_state']:20s} rec={mism['recommended_unit']}  (ratio {mism['footprint_ratio']:.0f})")
    verdict = ("DETECTED: matched recovers B_rough; mismatched flips to "
               + str(mism["recommended_unit"]) + " -- footprint confound caught."
               if small["recommended_unit"] == "B_rough"
               and mism["recommended_unit"] != small["recommended_unit"]
               else "NO FLIP (inspect)")
    print(f"\nconfound check: {verdict}")
    print(f"block-bootstrap non-domination @ core: {small.get('nondominated_freq')}")
    print("baselines @ core:  " + "; ".join(f"{d}->{baselines[d]['closest']}" for d in baselines))
    print("lens ablation @ core: " + "; ".join(f"{k}={v['recommended_unit']}" for k, v in ablation.items()))

    payload = {
        "experiment": "matched_footprint_synthetic_v1",
        "ground_truth": {"core_amp": 25.0, "apron_amp": 4.0, "correct_core_analog": "B_rough"},
        "matched_small": small, "matched_large": large, "mismatched": mism,
        "baselines": baselines, "lens_ablation": ablation, "grid": grid,
        "note": "map-scale morphology screening only; method validation, not a Mars result.",
    }
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "matched_benchmark_synthetic.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    print(f"\n[bundle] wrote {path}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Matched-footprint benchmark (morphology screening only).")
    ap.add_argument("--synthetic", action="store_true", help="run the offline synthetic method-validation experiment")
    ap.add_argument("--config", help="real Mars-Earth run (requires rasterio + cached DEMs; see BENCHMARK-PROTOCOL.md)")
    ap.add_argument("--out", default="artifacts/mf_bench", help="output directory for the evidence bundle")
    args = ap.parse_args(argv)
    if args.synthetic:
        return run_synthetic(args.out)
    if args.config:
        print("Real matched-footprint run is not yet implemented in this iteration.\n"
              "It needs windowed, per-body reprojected crops via rasterio on a machine\n"
              "that has the DEMs (data/mars/mola_463m.tif, data/earth/*.tif).\n"
              "Frozen protocol + resource estimate: docs/BENCHMARK-PROTOCOL.md\n"
              "Frozen inputs: config/matched_footprint.example.yml\n"
              "Smallest next step: implement crop-on-reprojected-grid, then rerun with --config.")
        return 2
    ap.error("specify --synthetic (offline) or --config (real; see BENCHMARK-PROTOCOL.md)")


if __name__ == "__main__":
    raise SystemExit(main())
