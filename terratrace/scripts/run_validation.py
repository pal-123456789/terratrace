#!/usr/bin/env python3
"""Run the TerraTrace scientific-correctness validation suite and report.

    python3 scripts/run_validation.py              # human report, exit!=0 on any failure
    python3 scripts/run_validation.py --json        # also write artifacts/validation.json

The suite drives the REAL comparison engine on synthetic terrains with KNOWN
relationships and asserts the distances + Pareto decision behave as geomorphometry
requires (self-distance zero, offset/rotation invariance, monotonic discrimination,
dominance recovery, null control, water-blocking, determinism). It is CI-friendly:
exit code is non-zero if any check fails. Pure NumPy + the engine; no network.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import validation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="write the report JSON")
    ap.add_argument("--out", default="artifacts", help="output dir for --json")
    args = ap.parse_args()

    report = validation.run_validation()
    print(f"TerraTrace validation — {report['suite']}")
    print("=" * 60)
    for c in report["checks"]:
        print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}")
        print(f"       {c['detail']}")
    print("=" * 60)
    print(f"passed={report['passed']} failed={report['failed']} "
          f"all_passed={report['all_passed']}  hash={report['package_hash'][:16]}...")

    if args.json:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "validation.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        print(f"wrote {path}")

    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
