#!/usr/bin/env python3
"""Generate sources.lock.yml for a real-data config (run where DEMs live).

Records SHA-256, size, native posting, rights, citation, and (via rasterio,
if available) CRS/bounds/shape/nodata for every input DEM.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import sourcelock


def _geo(path):
    try:
        import rasterio
    except Exception:
        return None
    try:
        with rasterio.open(path) as ds:
            b = ds.bounds
            return {"crs": str(ds.crs), "width": ds.width, "height": ds.height,
                    "nodata": ds.nodata,
                    "bounds": [b.left, b.bottom, b.right, b.top],
                    "res": [abs(ds.transform.a), abs(ds.transform.e)]}
    except Exception as exc:
        return {"error": str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="sources.lock.yml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    units = [cfg["reference"]] + cfg["earth_units"]
    entries = []
    for u in units:
        geo = _geo(u["path"]) if os.path.exists(u["path"]) else None
        entry = sourcelock.build_entry(u, geo=geo)
        entries.append(entry)
        flag = "ok" if entry["exists"] else "MISSING"
        print(f"[{flag}] {entry['id']}: sha256={str(entry['sha256'])[:16]} bytes={entry['bytes']}")

    lock = {"schema_version": "0.1.0",
            "target_support_m": cfg.get("target_support_m"),
            "reproject": cfg.get("reproject", True),
            "sources": entries}
    with open(args.out, "w", encoding="utf-8") as fh:
        yaml.safe_dump(lock, fh, sort_keys=False, allow_unicode=True)
    print(f"wrote {args.out} ({len(entries)} sources)")


if __name__ == "__main__":
    main()
