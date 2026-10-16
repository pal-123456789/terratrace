#!/usr/bin/env python3
"""Reproducible matched-footprint benchmark experiment for TerraTrace.

This is the Milestone-2 experiment runner. The ``--synthetic`` path is the frozen,
offline METHOD-VALIDATION experiment: it plants a known footprint confound (a rough
core inside a smooth apron) and shows that a matched-footprint comparison recovers
the correct analog while a mismatched comparison does not. It writes a machine-
readable evidence bundle (JSON) and prints a readable summary.

    python scripts/run_matched_benchmark.py --synthetic --out artifacts/mf_bench

The REAL Mars-Earth path (``--config``) is the scientific-discovery experiment and
requires rasterio + the cached DEMs on the data machine. The config decides which
frozen protocol runs: a config with a ``panel`` key is the v2 REFERENCE PANEL
(docs/BENCHMARK-PROTOCOL-v2.md, config/matched_footprint_v2.yml ->
``matched_real.run_real_panel``); any other config is the v1 single-reference run
(docs/BENCHMARK-PROTOCOL.md, config/matched_footprint.example.yml ->
``matched_real.run_real_matched``). Without rasterio, --config prints an honest
blocked message and exits 2.

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


def _load_config(path):
    """Parse the matched-footprint YAML config into a plain dict.

    PyYAML is imported LAZILY here (not at module top) so the offline --synthetic
    path and the engine's NumPy-only tests never require yaml; it ships in
    requirements-real alongside rasterio. Mirrors scripts/run_real_analog_study.py.
    """
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# Printed when --config is requested but rasterio is unavailable here. The real
# runner IS implemented (terratrace.matched_real); it is BLOCKED in this environment
# only because the windowed, per-body reprojected DEM reads need rasterio + the
# cached DEMs, which live on the data machine.
_RASTERIO_BLOCKED = (
    "Real matched-footprint run is BLOCKED here: rasterio is not importable in this\n"
    "environment, so the windowed, per-body reprojected DEM crops cannot be read.\n"
    "The runner itself is implemented (terratrace.matched_real.run_real_matched).\n"
    "On the data machine (rasterio installed; data/mars/mola_463m.tif + "
    "data/earth/*.tif present)\n"
    "this exact command runs the experiment end-to-end and writes the evidence bundle.\n"
    "Frozen protocol + resource estimate: docs/BENCHMARK-PROTOCOL.md\n"
    "Frozen inputs: config/matched_footprint.example.yml")

# The same honest block for a v2 (reference-panel) config.
_RASTERIO_BLOCKED_V2 = (
    "Real v2 REFERENCE-PANEL run is BLOCKED here: rasterio is not importable in this\n"
    "environment, so the windowed, per-body reprojected DEM crops cannot be read.\n"
    "The runner itself is implemented (terratrace.matched_real.run_real_panel).\n"
    "On the data machine (rasterio installed; data/mars/mola_463m.tif + "
    "data/earth/*.tif present)\n"
    "this exact command runs the panel end-to-end and writes matched_panel_real.json.\n"
    "Frozen protocol + H1-H4 decision rules: docs/BENCHMARK-PROTOCOL-v2.md\n"
    "Frozen inputs: config/matched_footprint_v2.yml")


def _is_panel(cfg):
    return isinstance(cfg, dict) and "panel" in cfg


def dispatch(cfg, out, config_path=None):
    """Route a loaded config to its REAL runner: a ``panel`` key -> the v2 reference
    panel (``matched_real.run_real_panel``, with ``config_path`` recorded in the
    bundle); otherwise the v1 single-reference run (``matched_real.run_real_matched``).
    Raises ImportError when rasterio is unavailable (``main`` turns that into the
    honest blocked message + exit 2)."""
    from terratrace import matched_real
    if _is_panel(cfg):
        if config_path:
            cfg = dict(cfg, config_path=config_path)
        return matched_real.run_real_panel(cfg, out=out)
    return matched_real.run_real_matched(cfg, out=out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Matched-footprint benchmark (morphology screening only).")
    ap.add_argument("--synthetic", action="store_true", help="run the offline synthetic method-validation experiment")
    ap.add_argument("--config", help="real Mars-Earth run (requires rasterio + cached DEMs); a config with a 'panel' key runs the v2 reference panel (BENCHMARK-PROTOCOL-v2.md), otherwise v1 (BENCHMARK-PROTOCOL.md)")
    ap.add_argument("--out", default="artifacts/mf_bench", help="output directory for the evidence bundle")
    args = ap.parse_args(argv)
    if args.synthetic:
        return run_synthetic(args.out)
    if args.config:
        cfg = _load_config(args.config)
        try:
            dispatch(cfg, args.out, config_path=args.config)
            return 0
        except ImportError:
            # rasterio (the ONLY real-data dependency, isolated in
            # matched_real.load_metric_grids / load_panel_grids) is unavailable here
            # -> honest block.
            print(_RASTERIO_BLOCKED_V2 if _is_panel(cfg) else _RASTERIO_BLOCKED)
            return 2
    ap.error("specify --synthetic (offline) or --config (real; see BENCHMARK-PROTOCOL.md)")


if __name__ == "__main__":
    raise SystemExit(main())
