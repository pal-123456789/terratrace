#!/usr/bin/env python3
"""Quick QA / data-health report for a DEM file (run where rasterio is installed).

    python3 scripts/profile_dem.py data/earth/candidate_b_cop30.tif
    python3 scripts/profile_dem.py --bbox W S E N data/mars/mola_463m.tif   # window
    python3 scripts/profile_dem.py --json dem.tif                            # full dict

Prints valid/water/NaN fractions, robust relief, percentiles, and advisory flags
(see terratrace.profile). Exit code is non-zero when a BLOCKING flag fires
(ALL_NAN / LOW_VALID_FRACTION / WATER_CONTAMINATION), so it is CI-friendly.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import ingest, profile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="path to a GeoTIFF DEM")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"),
                    help="only profile this window (in the raster CRS)")
    ap.add_argument("--water-value", type=float, default=0.0,
                    help="sea-level proxy in the DEM datum (default 0.0 m)")
    ap.add_argument("--json", action="store_true", help="print the full profile dict")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        sys.exit(f"no such file: {args.path}")

    if args.bbox:
        z, posting = ingest.window_from_bbox(args.path, tuple(args.bbox))
    else:
        z, posting = ingest.load_dem_array(args.path)

    s = profile.summarize(z, posting_m=posting, water_value=args.water_value)
    p = s["profile"]
    if args.json:
        print(json.dumps(s, indent=2, sort_keys=True))
    else:
        print(f"file           : {args.path}")
        print(f"shape          : {p['shape']}  posting ~ {posting:.1f} m")
        print(f"valid fraction : {p['valid_fraction']:.3f}  (nan {p['nan_fraction']:.3f})")
        print(f"water fraction : {p['water_fraction']:.3f}  (sea-level proxy @ {args.water_value:g} m)")
        print(f"elevation      : min {p['min']:.1f}  p50 {p['p50']:.1f}  max {p['max']:.1f}")
        print(f"robust relief  : {p['relief']:.1f} m  (p99 - p1)")
        print(f"flags          : {s['flags'] or 'none'}")
        print(f"verdict        : {'OK' if s['ok'] else 'REVIEW (blocking flag set)'}")
    sys.exit(0 if s["ok"] else 2)


if __name__ == "__main__":
    main()
