"""Independent-toolchain re-derivation of two TerraTrace descriptors.

Scope, stated honestly up front:

* The reprojection to a metric grid is NOT independently reproduced. TerraTrace uses
  rasterio, which IS GDAL; any GDAL-based route would share the same code. That step is
  therefore excluded from the claim, and the comparison is made on the identical array.
* What IS independently reproduced is the descriptor operator: slope and local relief,
  recomputed from the same elevation array by two implementations that share no code
  with TerraTrace --
    - RichDEM (Barnes, C++), published terrain-analysis algorithms;
    - WhiteboxTools 2.3.6 (Whitebox Geospatial), an independent GIS toolkit.
  TerraTrace's slope is a 4-neighbour central difference; RichDEM's and WhiteboxTools'
  are 3x3 stencil estimators (Horn / Zevenbergen-Thorne family). A small systematic
  difference is therefore EXPECTED and is quantified rather than assumed away.
"""
import json
import os
import pathlib
import sys

import numpy as np
import rasterio
import richdem as rd
import whitebox
import yaml

TT = pathlib.Path("/sessions/intelligent-blissful-thompson/mnt/Nasa Space App Hackathon 2026/terratrace")
sys.path.insert(0, str(TT))
os.chdir(TT)          # config paths are relative to the engine root
from terratrace import features, matched_benchmark as mb, matched_real, support  # noqa: E402

WORK = pathlib.Path("/tmp/gis_repro")
WORK.mkdir(parents=True, exist_ok=True)
ND = -9999.0

cfg = yaml.safe_load((TT / "config" / "matched_footprint_v3.yml").read_text(encoding="utf-8"))
grids, spacings, rights, reference_id = matched_real.load_metric_grids(cfg)

# The reference is deliberately held out of the candidate dict; read it through the very
# same function the loader uses, with the same reference parameters, so nothing about the
# ingest differs.
REF_ID = "mars_arcadia"   # the v3 primary confirmatory reference
_ref = next(u for u in cfg["units"] if u["id"] == REF_ID)
_res = float(_ref["native_posting_m"])
_extent = float(cfg["extent_m"]) * float(cfg.get("mismatch_ratio",
                matched_real._DEFAULT_MISMATCH_RATIO)) * matched_real._READ_MARGIN
grids[REF_ID], spacings[REF_ID] = matched_real._read_unit_metric(
    _ref, _ref.get("body", "mars"), _res, _extent)
print(f"loaded {len(grids)} units; reference = {reference_id}")

wbt = whitebox.WhiteboxTools()
wbt.set_verbose_mode(False)
wbt.set_working_dir(str(WORK))


def interior_mask(z, k=1):
    """Cells whose (2k+1)^2 neighbourhood is entirely finite -- the honest comparison set."""
    m = np.isfinite(z)
    for dr in range(-k, k + 1):
        for dc in range(-k, k + 1):
            m &= np.roll(np.roll(np.isfinite(z), dr, axis=0), dc, axis=1)
    m[:k, :] = m[-k:, :] = False
    m[:, :k] = m[:, -k:] = False
    return m


def stats(a, b, mask, label):
    d = np.abs(a[mask] - b[mask])
    return {
        "n_cells": int(mask.sum()),
        f"{label}_mean_abs_diff": float(np.mean(d)),
        f"{label}_median_abs_diff": float(np.median(d)),
        f"{label}_p95_abs_diff": float(np.percentile(d, 95)),
        f"{label}_max_abs_diff": float(np.max(d)),
        f"{label}_corr": float(np.corrcoef(a[mask], b[mask])[0, 1]),
        f"{label}_tt_mean": float(np.mean(a[mask])),
        f"{label}_other_mean": float(np.mean(b[mask])),
    }


def write_tif(arr, dx, path):
    """A metric placeholder CRS. Only the cell size matters to a descriptor operator; the
    georeferencing is deliberately NOT part of this comparison (see module docstring)."""
    filled = np.where(np.isfinite(arr), arr, ND).astype("float32")
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                       count=1, dtype="float32", crs="EPSG:3857", nodata=ND,
                       transform=rasterio.transform.from_origin(0, 0, dx, dx)) as ds:
        ds.write(filled, 1)
    return path


TARGET_SUPPORT_M = 1500.0
results = {}

for uid in ("earth_llano_estacado", "earth_nullarbor", REF_ID):
    if uid not in grids:
        print(f"  {uid}: not loaded, skipping")
        continue
    z, sp = np.asarray(grids[uid], dtype=float), float(spacings[uid])
    sub, info = mb.crop_center(z, sp, float(cfg["extent_m"]))
    factor = max(int(round(TARGET_SUPPORT_M / sp)), 1)
    agg, rec = support.block_aggregate(sub, factor, sp, aggregation="mean", min_valid=0.5)
    dx = sp * factor
    print(f"\n{uid}: native {sp:.1f} m -> cropped {sub.shape} -> support {dx:.1f} m {agg.shape} "
          f"(valid {rec.valid_fraction:.3f})")

    mask = interior_mask(agg, 1)
    if mask.sum() < 50:
        print("  too few interior cells, skipping")
        continue
    filled = np.where(np.isfinite(agg), agg, float(np.nanmedian(agg)))

    # --- slope -------------------------------------------------------------------
    tt_slope = features.slope_deg(agg, dx, dx)
    tif = write_tif(agg, dx, WORK / f"{uid}.tif")

    # RichDEM reads cell size from a geotransform. Built from a bare array it assumes
    # 1x1 cells -- which on a 1500 m grid inflated slope to ~50 degrees.
# RichDEM has no GDAL bindings here, so it cannot read a cell size from a raster and
    # treats one cell as one horizontal unit. Its documented remedy for non-unit cells is
    # to express elevation in the horizontal unit, so we pass z/dx; slope_degrees is then
    # directly comparable. (Supplying a geotransform kwarg did not change its behaviour.)
    dem = rd.rdarray(filled / dx, no_data=ND)
    rd_slope = np.asarray(rd.TerrainAttribute(dem, attrib="slope_degrees"), dtype=float)

    wbt.slope(dem=str(tif), output=str(WORK / f"{uid}_slope.tif"), units="degrees")
    with rasterio.open(WORK / f"{uid}_slope.tif") as ds:
        wbt_slope = ds.read(1).astype(float)
    if wbt_slope.shape != agg.shape:
        wbt_slope = wbt_slope[:agg.shape[0], :agg.shape[1]]

    r = {"unit": uid, "native_posting_m": sp, "support_m": dx,
         "grid_shape": list(agg.shape), "valid_fraction": rec.valid_fraction}
    r.update(stats(tt_slope, rd_slope, mask, "slope_richdem"))
    r.update(stats(tt_slope, wbt_slope, mask, "slope_whitebox"))
    r["tt_slope_mean"] = float(np.mean(tt_slope[mask]))
    r["tt_slope_median"] = float(np.median(tt_slope[mask]))

    # --- relief, window 3 (max - min) --------------------------------------------
    tt_relief = features.relief(agg, window=3, alpha=0.0)
    wbt.range_filter(i=str(tif), output=str(WORK / f"{uid}_range.tif"), filterx=3, filtery=3)
    with rasterio.open(WORK / f"{uid}_range.tif") as ds:
        wbt_range_full = ds.read(1).astype(float)
        wbt_range_full[wbt_range_full == ND] = np.nan
    # range_filter keeps the input size; TerraTrace's relief is valid on the interior only
    rr = tt_relief
    # Do not assume the window convention matches: search the 3x3 alignment neighbourhood and
    # report the best AND the naive same-index alignment, so the reader sees both.
    best, naive = None, None
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            r0, c0 = 1 + dr, 1 + dc
            if r0 < 0 or c0 < 0:
                continue
            ww = wbt_range_full[r0:r0 + rr.shape[0], c0:c0 + rr.shape[1]]
            if ww.shape != rr.shape:
                continue
            rm = interior_mask(rr, 1) & np.isfinite(rr) & np.isfinite(ww)
            if rm.sum() <= 50:
                continue
            mad = float(np.mean(np.abs(rr[rm] - ww[rm])))
            if dr == 0 and dc == 0:
                naive = mad
            if best is None or mad < best[0]:
                best = (mad, rm, ww, (dr, dc), int(rm.sum()))
    if best is not None:
        mad, rm, ww, off, n = best
        r.update(stats(rr, ww, rm, "relief_aligned"))
        r["relief_best_alignment_dr_dc"] = list(off)
        r["relief_n_cells"] = n
        r["tt_relief_mean"] = float(np.mean(rr[rm]))
        if naive is not None:
            r["relief_naive_same_index_mean_abs_diff"] = float(naive)

    results[uid] = r
    for k, v in r.items():
        if isinstance(v, float):
            print(f"    {k:34s} {v:,.4f}")
        else:
            print(f"    {k:34s} {v}")

(WORK / "reproduction.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nwrote {WORK / 'reproduction.json'}")
