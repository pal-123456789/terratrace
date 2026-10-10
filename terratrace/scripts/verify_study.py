#!/usr/bin/env python3
"""Verify a published study package's content hash.

Loads a study JSON, recomputes its SHA-256 content hash the same way the study
pipeline does (over every top-level key except ``package_hash``), and compares
it against the stored ``package_hash``. Prints the stored vs recomputed hash and
PASS/FAIL, and exits 0 when they match (1 otherwise) so it can gate a release.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import repro


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify a study package content hash.")
    ap.add_argument("path", nargs="?", default="artifacts/study.json",
                    help="path to the study package JSON (default: artifacts/study.json)")
    args = ap.parse_args(argv)

    with open(args.path, encoding="utf-8") as fh:
        pkg = json.load(fh)

    result = repro.verify_hash(pkg)
    print(f"path       : {args.path}")
    print(f"stored     : {result['stored']}")
    print(f"recomputed : {result['recomputed']}")
    print(f"result     : {'PASS' if result['match'] else 'FAIL'}")
    return 0 if result["match"] else 1


if __name__ == "__main__":
    sys.exit(main())
