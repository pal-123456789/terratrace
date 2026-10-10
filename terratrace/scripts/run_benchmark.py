#!/usr/bin/env python3
"""Run the TerraTrace reproducibility + performance benchmark and report.

    python3 scripts/run_benchmark.py                       # default sizes, human report
    python3 scripts/run_benchmark.py --sizes 48,96,192 --repeats 3 --json

Runs a pinned battery of end-to-end studies whose behavioural invariants must
hold (which state is reached, which unit wins, what is blocked), a hash-stability
check, and a wall-clock scaling profile. Exit code is non-zero if any invariant
scenario fails; timings are reported, never pass/failed (they are host-dependent).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import benchmark


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="48,96,144",
                    help="comma-separated square grid sizes for the scaling profile")
    ap.add_argument("--repeats", type=int, default=3, help="timing repeats (median reported)")
    ap.add_argument("--json", action="store_true", help="write the report JSON")
    ap.add_argument("--out", default="artifacts", help="output dir for --json")
    args = ap.parse_args()
    sizes = tuple(int(s) for s in args.sizes.split(",") if s.strip())

    report = benchmark.run_benchmark(sizes=sizes, repeats=args.repeats)
    print(f"TerraTrace benchmark — {report['suite']}")
    print("=" * 60)
    for s in report["scenarios"]:
        print(f"[{'PASS' if s['passed'] else 'FAIL'}] {s['name']}: {s['detail']}")
    print("-" * 60)
    print(f"{'grid':>8} {'cells':>9} {'seconds':>10}   state")
    for row in report["scaling"]:
        print(f"{row['size']:>6}^2 {row['cells']:>9,} {row['seconds']:>10.4f}   {row['state']}")
    print("=" * 60)
    print(f"passed={report['passed']} failed={report['failed']} "
          f"all_passed={report['all_passed']}  hash={report['package_hash'][:16]}...")

    if args.json:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "benchmark.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        print(f"wrote {path}")

    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
