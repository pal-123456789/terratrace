#!/usr/bin/env python3
"""Run a TerraTrace study on REAL DEMs described by the config.

Requires: pip install -r requirements-real.txt
Writes artifacts/ (study package) and viewer/index.html.
"""
import argparse
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import study, build_viewer
from terratrace.provenance import sha256_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="artifacts")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    units = [cfg["reference"]] + cfg["earth_units"]
    missing = [u["path"] for u in units if not os.path.exists(u["path"])]
    if missing:
        sys.exit("Missing DEM files (run fetch first):\n  " + "\n  ".join(missing))

    pkg = study.run_real_study(
        units,
        target_support_m=cfg.get("target_support_m", 1000.0),
        min_valid=cfg.get("min_valid_fraction", 0.5),
        reproject=cfg.get("reproject", True),
        decision_metrics=cfg.get("decision_metrics", "core"),
        n_boot=cfg.get("n_boot", 0),
    )

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "study.json"), "w", encoding="utf-8") as fh:
        json.dump(pkg, fh, indent=2, sort_keys=True)
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"release": "terratrace-v0.1.0-real",
                   "result_state": pkg["result_state"],
                   "recommended_unit": pkg["recommended_unit"],
                   "package_hash": pkg["package_hash"],
                   "claim_maturity": pkg["profile"]["claim_maturity"]}, fh, indent=2, sort_keys=True)

    build_viewer.main(["--study", os.path.join(args.out, "study.json"),
                       "--out", "viewer/index.html"])
    print(f"result_state     = {pkg['result_state']}")
    print(f"recommended_unit = {pkg['recommended_unit']}")
    print(f"package_hash     = {pkg['package_hash'][:16]}...")


if __name__ == "__main__":
    main()
