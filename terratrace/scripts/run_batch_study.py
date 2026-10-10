#!/usr/bin/env python3
"""Run a TerraTrace CROSS-REFERENCE batch study on REAL DEMs from a config.

A batch study is a robustness sweep: every Earth candidate is compared against
EVERY Mars reference window under EVERY decision mode (core / extended /
geomorphic). The synthesis reports how often each candidate stays Pareto
non-dominated across that whole grid -- i.e. whether the recommendation
survives a different choice of Mars reference AND a different morphology lens.
It calls terratrace.batch.run_real_batch, which reuses the SAME DEM loader and
comparison engine as scripts/run_real_study.py (study.load_real_units +
study.compare_units); so the units config is the run_real_study unit-dict
shape, with is_reference: true marking the Mars reference regions.

Requires: pip install -r requirements-real.txt (rasterio) AND the real DEM
files referenced by the config. Fetch the DEMs on a NETWORKED machine first;
this script does no downloading and refuses to run if any path is missing.

    python3 scripts/run_batch_study.py --config config/batch.example.yml
    python3 scripts/run_batch_study.py --config config/batch.example.yml --json
"""
import argparse
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import batch


def _fmt_float(x, nd=2):
    try:
        if x != x:  # NaN
            return "nan"
        return f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _print_synthesis(report):
    print(f"TerraTrace cross-reference batch — {report['suite']}")
    print("=" * 64)
    print(f"references : {', '.join(report['references'])}")
    print(f"candidates : {', '.join(report['candidates'])}")
    print(f"modes      : {', '.join(report['decision_modes'])}")
    print(f"n_cells    : {report['n_cells']}  (references x modes)")

    # Per-candidate robustness table.
    cands = report["candidates"]
    cand_w = max([len("candidate")] + [len(str(c)) for c in cands])
    print()
    print("Per-candidate robustness")
    print("-" * 64)
    print(f"{'candidate':<{cand_w}}  {'layer1_freq':>11}  {'rec_freq':>8}  "
          f"{'mean_layer':>10}  {'cells':>5}")
    for c in cands:
        pc = report["per_candidate"][c]
        print(f"{c:<{cand_w}}  {_fmt_float(pc['layer1_frequency']):>11}  "
              f"{_fmt_float(pc['recommended_frequency']):>8}  "
              f"{_fmt_float(pc['mean_layer']):>10}  {pc['cells_ranked']:>5}")

    print()
    cons = report["consensus_shortlist"]
    print("consensus_shortlist : " + (", ".join(cons) if cons else "(none)"))
    print("                      (non-dominated in EVERY reference x mode cell)")
    print("robust_ordering     : " + ", ".join(report["robust_ordering"]))

    # (reference x mode) cell grid.
    cells = report["cells"]
    ref_w = max([len("reference")] + [len(str(c["reference"])) for c in cells])
    mode_w = max([len("mode")] + [len(str(c["mode"])) for c in cells])
    state_w = max([len("state")] + [len(str(c["result_state"])) for c in cells])
    print()
    print("Cell grid (reference x mode)")
    print("-" * 64)
    print(f"{'reference':<{ref_w}}  {'mode':<{mode_w}}  "
          f"{'state':<{state_w}}  recommended")
    for c in cells:
        rec = c["recommended_unit"] if c["recommended_unit"] is not None else "-"
        print(f"{c['reference']:<{ref_w}}  {c['mode']:<{mode_w}}  "
              f"{c['result_state']:<{state_w}}  {rec}")

    print()
    print(f"note: {report['note']}")
    print(f"package_hash = {report['package_hash'][:16]}...")


def main():
    ap = argparse.ArgumentParser(
        description="Cross-reference, multi-lens batch study on real DEMs.")
    ap.add_argument("--config", required=True,
                    help="batch config YAML (see config/batch.example.yml)")
    ap.add_argument("--out", default="artifacts", help="output dir for --json")
    ap.add_argument("--json", action="store_true", help="write the batch report JSON")
    ap.add_argument("--no-reproject", action="store_true",
                    help="disable per-AOI azimuthal-equidistant reprojection (same-dx fallback)")
    ap.add_argument("--modes", default="core,extended,geomorphic",
                    help="comma-separated decision modes to sweep (default: core,extended,geomorphic)")
    ap.add_argument("--target-support", type=float, default=None,
                    help="common support in metres (default: config target_support_m or 1000)")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    units = cfg.get("units")
    if not units:
        sys.exit("Config has no 'units' list.")

    # Real DEMs are fetched on the user's (networked) machine; refuse to run if
    # any referenced file is absent, listing exactly what is missing.
    missing = [u["path"] for u in units if not os.path.exists(u["path"])]
    if missing:
        sys.exit("Missing DEM files (run fetch first):\n  " + "\n  ".join(missing))

    target_support = args.target_support
    if target_support is None:
        target_support = cfg.get("target_support_m", 1000.0)
    reproject = cfg.get("reproject", True)
    if args.no_reproject:
        reproject = False
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    report = batch.run_real_batch(
        units,
        target_support_m=target_support,
        min_valid=cfg.get("min_valid_fraction", 0.5),
        reproject=reproject,
        decision_modes=tuple(modes),
    )

    _print_synthesis(report)

    if args.json:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "batch.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
