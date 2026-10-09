"""Command-line entry point: run a study and emit a study package."""
from __future__ import annotations

import argparse
import json
import os

from .study import run_study
from .provenance import sha256_json


def main(argv=None):
    ap = argparse.ArgumentParser(description="TerraTrace reference study runner")
    ap.add_argument("--out", default="artifacts", help="output directory")
    ap.add_argument("--target-support-m", type=float, default=100.0)
    ap.add_argument("--native-posting-m", type=float, default=25.0)
    args = ap.parse_args(argv)

    pkg = run_study(target_support_m=args.target_support_m,
                    native_posting_m=args.native_posting_m)

    os.makedirs(args.out, exist_ok=True)
    files = {
        "study.json": pkg,
        "profile.json": pkg["profile"],
        "transfer-gap-ledger.json": pkg["transfer_gap_ledger"],
        "draft-protocol.json": pkg["draft_protocol"],
        "evidence-graph.json": pkg["evidence_graph"],
    }
    checksums = {}
    for name, obj in files.items():
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True)
        checksums[name] = sha256_json(obj)

    manifest = {
        "release": "terratrace-v0.1.0",
        "result_state": pkg["result_state"],
        "recommended_unit": pkg["recommended_unit"],
        "package_hash": pkg["package_hash"],
        "artifacts": checksums,
        "claim_maturity": pkg["profile"]["claim_maturity"],
    }
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    with open(os.path.join(args.out, "checksums.txt"), "w", encoding="utf-8") as fh:
        for name, digest in sorted(checksums.items()):
            fh.write(f"{digest}  {name}\n")

    print(f"result_state       = {pkg['result_state']}")
    print(f"recommended_unit   = {pkg['recommended_unit']}")
    print(f"package_hash       = {pkg['package_hash'][:16]}...")
    print(f"artifacts written  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
