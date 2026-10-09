#!/usr/bin/env python3
"""Fetch real Earth DEMs for each AOI in the config (run on a networked machine).

Requires: pip install -r requirements-real.txt
Env: OPENTOPO_API_KEY (free key from https://portal.opentopography.org)
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import ingest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    key = os.environ.get("OPENTOPO_API_KEY")
    if not key:
        sys.exit("Set OPENTOPO_API_KEY (free key: https://portal.opentopography.org).")

    ref = cfg["reference"]
    if not os.path.exists(ref["path"]):
        print(f"[!] Mars reference missing: {ref['path']}")
        print("    Download 'Mars MGS MOLA DEM 463m' GeoTIFF from USGS Astrogeology")
        print("    https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m")

    for unit in cfg["earth_units"]:
        bbox = unit["bbox"]  # west, south, east, north
        demtype = unit.get("demtype", "COP30")
        out = unit["path"]
        print(f"[*] fetching {unit['id']} {demtype} bbox={bbox} -> {out}")
        ingest.fetch_copernicus_glo30(bbox, key, out, demtype=demtype)
        print(f"    done: {out}")
    print("All Earth DEMs fetched. Next: scripts/run_real_study.py")


if __name__ == "__main__":
    main()
