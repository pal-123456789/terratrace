#!/usr/bin/env python3
"""Crop a small, committable Mars AOI sample from the ~2 GB global MOLA DEM.

The global file exceeds GitHub's 100 MB limit; this writes a few-MB GeoTIFF of
just the reference study window so the repo can carry a real Mars sample.

Requires rasterio. Run on the machine that holds data/mars/mola_463m.tif.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="data/mars/mola_sample.tif")
    args = ap.parse_args()

    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    from terratrace.reproject import geographic_crs

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    ref = cfg["reference"]
    src_path = ref["path"]
    bbox = ref.get("bbox")
    body = ref.get("body", "mars")
    if not os.path.exists(src_path):
        sys.exit(f"Missing {src_path} — download the global MOLA 463 m DEM first "
                 "(see data/mars/README.md).")
    if not bbox:
        sys.exit("reference.bbox is required in the config to crop a sample.")

    with rasterio.open(src_path) as ds:
        if ds.crs is None:
            sys.exit(f"{src_path} has no CRS; cannot crop safely.")
        west, south, east, north = bbox  # degrees on the body
        sw, ss, se, sn = transform_bounds(geographic_crs(body), ds.crs, west, south, east, north)
        win = from_bounds(sw, ss, se, sn, ds.transform)
        data = ds.read(1, window=win)
        prof = ds.profile.copy()
        prof.update(height=data.shape[0], width=data.shape[1],
                    transform=ds.window_transform(win), compress="deflate", predictor=2)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with rasterio.open(args.out, "w", **prof) as dst:
        dst.write(data, 1)
    mb = os.path.getsize(args.out) / 1e6
    print(f"wrote {args.out} ({mb:.1f} MB, {data.shape[1]}x{data.shape[0]} px)")
    if mb > 95:
        print("WARNING: sample >95 MB — tighten the bbox before committing to GitHub.")


if __name__ == "__main__":
    main()
