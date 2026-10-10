#!/usr/bin/env python3
"""Cross-body terrain-fingerprint similarity search -- offline synthetic demo.

    python3 scripts/fingerprint_search.py            # full similarity matrix
    python3 scripts/fingerprint_search.py --top 1    # only each candidate's best match

Builds a handful of synthetic planetary "reference" terrains (labelled
mars-like / moon-like) and several synthetic Earth "candidate" terrains, then
prints the cross-body table from
:func:`terratrace.fingerprint_library.cross_body_table`: the single reference
each candidate most resembles, followed by the candidate x reference
similarity matrix.

This demo is deliberately self-contained and NETWORK-FREE: it fabricates
terrains with :mod:`terratrace.synthetic` so it runs anywhere, offline and
deterministically. A real-data version would instead load Digital Elevation
Models (Mars MOLA/HRSC, lunar LOLA, Earth Copernicus, ...) through the
project's ``ingest`` layer and fingerprint those tiles; the search API used
here is identical.

Morphological resemblance only. "Most similar" means nearest in the fixed
fingerprint signature space -- NOT a classification, geological-equivalence,
or mission claim.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import fingerprint_library, synthetic

SHAPE = (64, 64)


def _reference_terrains():
    """Synthetic planetary reference terrains (map-scale morphology only)."""
    return {
        "mars-like": (synthetic.plane(SHAPE, slope_x=0.20, slope_y=0.10)
                      + synthetic.rough_field(SHAPE, amplitude=5.0, seed=11)),
        "moon-like": (synthetic.gaussian_hill(SHAPE, amplitude=15.0, sigma=18.0)
                      + synthetic.rough_field(SHAPE, amplitude=0.3, seed=12)),
    }


def _candidate_terrains():
    """Synthetic Earth candidate terrains to rank against the references."""
    return {
        "volcanic-badlands": (synthetic.plane(SHAPE, slope_x=0.22, slope_y=0.08)
                              + synthetic.rough_field(SHAPE, amplitude=5.0, seed=301)),
        "fractured-upland": (synthetic.plane(SHAPE, slope_x=0.14, slope_y=0.18)
                             + synthetic.rough_field(SHAPE, amplitude=4.0, seed=302)),
        "rolling-lowland": (synthetic.gaussian_hill(SHAPE, amplitude=15.0, sigma=18.0)
                            + synthetic.rough_field(SHAPE, amplitude=0.4, seed=303)),
        "sand-sheet": (synthetic.plane(SHAPE, slope_x=0.01, slope_y=0.0)
                       + synthetic.rough_field(SHAPE, amplitude=0.3, seed=304)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--top", type=int, default=None,
                    help="show only each candidate's TOP-N reference matches "
                         "in the matrix (default: all references)")
    args = ap.parse_args()

    references = _reference_terrains()
    candidates = _candidate_terrains()
    table = fingerprint_library.cross_body_table(references, candidates)

    print("TerraTrace cross-body fingerprint search (synthetic, offline)")
    print("=" * 64)
    print("references:", ", ".join(table["references"]))
    print("candidates:", ", ".join(table["candidates"]))
    print("morphological resemblance only -- not a classification/mission claim")
    print("-" * 64)

    print("best reference per candidate:")
    for cand in table["candidates"]:
        ref, sim = table["best_reference"][cand]
        print(f"  {cand:<20s} -> {ref:<12s} (similarity {sim:.4f})")

    print("-" * 64)
    print("similarity matrix (candidate x reference, best first):")
    for cand in table["candidates"]:
        row = table["similarity"][cand]
        ranked_refs = sorted(row, key=lambda r: (-row[r], r))
        if args.top is not None:
            ranked_refs = ranked_refs[:args.top]
        cells = "  ".join(f"{r}={row[r]:.4f}" for r in ranked_refs)
        print(f"  {cand:<20s} {cells}")

    print("=" * 64)
    sys.exit(0)


if __name__ == "__main__":
    main()
