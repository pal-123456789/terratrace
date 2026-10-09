#!/usr/bin/env python3
"""Human-readable summary + sanity checks for a study package.

Flags degenerate results (empty/low valid fraction, all-zero or non-finite
distance vectors) so a run that "succeeded" but produced meaningless data
is caught.
"""
import argparse
import json
import math
import sys


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default="artifacts/study.json")
    args = ap.parse_args(argv)
    pkg = json.load(open(args.study, encoding="utf-8"))

    prof = pkg["profile"]
    print(f"source           : {prof.get('source_label')}")
    print(f"target_support_m : {prof.get('target_support_m')}")
    print(f"result_state     : {pkg['result_state']}")
    print(f"recommended_unit : {pkg['recommended_unit']}")
    print("-" * 60)
    print(f"{'unit':<20}{'eligible':<10}{'valid':<8}{'zero':<8}vector")
    warnings = []
    for uid, meta in pkg["unit_metadata"].items():
        vf = meta.get("valid_fraction", float("nan"))
        zf = meta.get("zero_fraction")
        zf_s = f"{zf:.2f}" if isinstance(zf, (int, float)) else "-"
        elig = pkg["eligibility"].get(uid, {}).get("eligible")
        vec = pkg["baseline_vectors"].get(uid)
        vecs = "-" if vec is None else "[" + ", ".join(f"{v:.3f}" for v in vec) + "]"
        print(f"{uid:<20}{str(elig):<10}{vf:<8.3f}{zf_s:<8}{vecs}")
        if uid != "mars_reference" and elig and vec is not None:
            if not all(math.isfinite(v) for v in vec):
                warnings.append(f"{uid}: non-finite distance (reprojection/data problem)")
            if all(abs(v) < 1e-9 for v in vec):
                warnings.append(f"{uid}: all-zero distance (identical/empty arrays?)")
        if elig and vf < 0.2:
            warnings.append(f"{uid}: very low valid fraction ({vf:.2f})")
        if isinstance(zf, (int, float)) and zf > 0.6:
            warnings.append(f"{uid}: {zf:.0%} pixels ~0 m - likely water; mask or choose a land AOI")
    ext = pkg.get("extended_metrics")
    if ext:
        print("-" * 60)
        print(f"{'unit':<20}{'aspect_disp':<14}hypsometric_integral")
        for uid, m in ext.items():
            ad = m.get("aspect_dispersion")
            hi = m.get("hypsometric_integral")
            ad_s = f"{ad:.3f}" if isinstance(ad, (int, float)) else "-"
            hi_s = f"{hi:.3f}" if isinstance(hi, (int, float)) else "nan"
            print(f"{uid:<20}{ad_s:<14}{hi_s}")
    print("-" * 60)
    print("pairwise rank-flip:", pkg.get("pairwise_flip_matrix") or "n/a")
    print(f"evidence nodes   : {len(pkg['evidence_graph']['nodes'])}")

    if warnings:
        print("\nSANITY WARNINGS:")
        for w in warnings:
            print("  !", w)
        return 1
    print("\nOK: no degeneracy detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
