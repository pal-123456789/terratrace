"""Exploratory lunar demonstration on REAL LOLA terrain (NASA Goddard PGDA, 5 m/px).

This is the first TerraTrace comparison that uses real lunar elevation data. It is
EXPLORATORY, and the distinction matters:

* The confirmatory Mars benchmark (protocol v3) is untouched by this script.
* It does not use the frozen core-lens axis set. It uses THREE DECLARED AXES, computed by the
  engine's own descriptor functions, and names them in the output so a reader can see exactly
  what was compared:
      1. mean slope, degrees            (features.slope_deg)
      2. mean 3x3 local relief, metres  (features.relief)
      3. window elevation std, metres   (the roughness family the v3 sigma labels report)
* The decision is the engine's Pareto machinery (`decision.non_dominated`).

Product: NASA Goddard Planetary Geodesy and Geophysics Archive, "South Pole Landing Site LOLA
DEMs" (Barker et al. 2021, PSS 203, 105119; site numbering from Mazarico et al. 2011, Icarus
211). 5 m/pixel GeoTIFF, south polar stereographic, metres, MOON_ME / DE421.

REGIME, and why it differs from the Mars panel: the published product is 16 km x 16 km, so the
study's 60 km extent is impossible. The common support here is 500-1000 m, which is above every
unit's 3x-source floor for Moon (15 m) and Earth (90 m) but BELOW MOLA's (1389 m). Mars is
therefore deliberately excluded from this regime rather than forced into it.
"""
import hashlib
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import LightSource

# Repository-relative, never absolute: the previous revision hard-coded this session's sandbox
# path, so the command this project documents for reproducing the result could not have run on
# any other machine — it only ever worked here.
ROOT = pathlib.Path(__file__).resolve().parent.parent          # .../terratrace
sys.path.insert(0, str(ROOT))
from terratrace import decision, features, matched_real, reproject, support  # noqa: E402

MOON_TIF = ROOT / "data" / "moon" / "Site01_surf.tif"
OUT_JSON = ROOT / "artifacts" / "lunar_site01" / "lunar_site01_exploratory.json"
OUT_PNG = ROOT / "docs" / "figures" / "lunar-site01.png"

EXTENT_M = 16000.0
SUPPORTS = [500.0, 750.0, 1000.0]

EARTH = [
    ("earth_nullarbor", "Australia", "data/earth/nullarbor_cop30.tif", -30.3, 129.0),
    ("earth_llano_estacado", "USA", "data/earth/llano_estacado_cop30.tif", 33.0, -102.0),
    ("earth_deccan_traps", "India", "data/earth/deccan_traps_cop30.tif", 20.0, 76.0),
    ("earth_snake_river_plain", "USA", "data/earth/snake_river_plain_cop30.tif", 43.05, -114.05),
    ("earth_harrat_khaybar", "Saudi Arabia", "data/earth/harrat_khaybar_cop30.tif", 25.5, 40.0),
    ("earth_odadahraun", "Iceland", "data/earth/odadahraun_cop30.tif", 65.23, -16.54),
    ("earth_nevada_basin", "USA", "data/earth/nevada_basin_cop30.tif", 36.2, -115.6),
]


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def axes_of(z, dx):
    """The three declared axes. NaN-safe over the finite interior."""
    slope = features.slope_deg(z, dx, dx)
    relief = features.relief(z, window=3, alpha=0.0)
    finite = np.isfinite(z)
    return {
        "mean_slope_deg": float(np.nanmean(slope)),
        "mean_relief3_m": float(np.nanmean(relief)),
        "elev_std_m": float(np.nanstd(z[finite])),
    }


def to_support(z, native_m, target_m):
    factor = max(int(round(target_m / native_m)), 1)
    agg, rec = support.block_aggregate(z, factor, native_m, aggregation="mean", min_valid=0.5)
    return agg, native_m * factor, rec


def centre_crop_square(z, extent_m, dx, target_cells):
    """Crop to the largest centred square that rounds to `target_cells` at this spacing."""
    n = int(round(extent_m / dx))
    h, w = z.shape
    n = min(n, h, w)
    r0 = (h - n) // 2
    c0 = (w - n) // 2
    return z[r0:r0 + n, c0:c0 + n]


# ---------------------------------------------------------------- lunar window
with __import__("rasterio").open(MOON_TIF) as ds:
    moon = ds.read(1).astype("float64")
    moon_dx = float(ds.res[0])
    moon_crs = ds.crs.to_string() if ds.crs else None
moon_meta = {
    "product": "NASA Goddard PGDA 'South Pole Landing Site LOLA DEMs', Site01 (Connecting ridge)",
    "file": MOON_TIF.name,
    "sha256": sha256(MOON_TIF),
    "native_posting_m": moon_dx,
    "crs": moon_crs,
    "shape": list(moon.shape),
    "extent_km": round(moon.shape[0] * moon_dx / 1000.0, 2),
    "citation": "Barker et al. (2021), Planet. Space Sci. 203, 105119; site numbering from "
                "Mazarico et al. (2011), Icarus 211, 1066-1081",
}
print(f"lunar: {moon.shape} @ {moon_dx} m  = {moon_meta['extent_km']} km across")
print(f"       sha256 {moon_meta['sha256'][:16]}")

# ---------------------------------------------------------------- earth windows
earth_grids = {}
for uid, where, path, lat, lon in EARTH:
    bbox = matched_real._center_bbox(lon, lat, EXTENT_M, "earth")
    z, dx = reproject.read_aoi_metric(path, bbox, 30.0, "earth")
    earth_grids[uid] = (np.asarray(z, dtype=float), float(dx), where, lon, lat)
    print(f"  earth {uid:24s} {z.shape} @ {dx:.1f} m")

# ---------------------------------------------------------------- per-support comparison
results = {"provenance": {"lunar": moon_meta, "extent_m": EXTENT_M,
                          "supports_m": SUPPORTS, "axes": ["mean_slope_deg", "mean_relief3_m", "elev_std_m"],
                          "decision": "decision.non_dominated (Pareto, no composite score)",
                          "status": "EXPLORATORY -- not the frozen core-lens confirmatory panel",
                          "mars_excluded_because": "MOLA effective floor 1389 m exceeds every support tested here"},
           "scales": {}}

for target in SUPPORTS:
    moon_agg, moon_sup, _ = to_support(moon, moon_dx, target)
    moon_agg = centre_crop_square(moon_agg, EXTENT_M, moon_sup, moon_agg.shape[0])
    vecs, axes = {}, {}
    axes["LUNAR_Site01"] = axes_of(moon_agg, moon_sup)
    vecs["LUNAR_Site01"] = [axes["LUNAR_Site01"][k] for k in results["provenance"]["axes"]]
    cells = list(moon_agg.shape)

    for uid, (z, dx, where, lon, lat) in earth_grids.items():
        sub = centre_crop_square(z, EXTENT_M, dx, 0)
        agg, sup, rec = to_support(sub, dx, target)
        # match the lunar cell count exactly, so footprints are physically equal
        n = moon_agg.shape[0]
        h, w = agg.shape
        if h >= n and w >= n:
            r0, c0 = (h - n) // 2, (w - n) // 2
            agg = agg[r0:r0 + n, c0:c0 + n]
        axes[uid] = axes_of(agg, sup)
        vecs[uid] = [axes[uid][k] for k in results["provenance"]["axes"]]

    # An analog comparison is a comparison of DISTANCES to the reference, not of raw values:
    # ranking raw axes would merely return whichever candidate is smallest on every axis.
    # Each axis distance is expressed as a fraction of the reference's own value, so the three
    # axes are commensurate without inventing a weighting.
    ref = axes["LUNAR_Site01"]
    dist = {}
    for uid, a in axes.items():
        if uid == "LUNAR_Site01":
            continue
        dist[uid] = [abs(a[k] - ref[k]) / abs(ref[k]) if ref[k] else float("nan")
                     for k in results["provenance"]["axes"]]
    layer1 = decision.non_dominated(dist) if dist else set()
    results["scales"][f"{int(target)}m"] = {
        "support_m": moon_sup, "cells": cells, "axes": axes,
        "axis_distance_fraction": dist,
        "layer1": sorted(layer1),
        "lunar_is_the_reference": True,
    }
    print(f"\nsupport {moon_sup:.0f} m, {cells[0]}x{cells[1]} cells")
    print(f"   reference LUNAR_Site01: slope {ref['mean_slope_deg']:.3f} deg  "
          f"relief {ref['mean_relief3_m']:.2f} m  std {ref['elev_std_m']:.2f} m")
    for uid in [e[0] for e in EARTH]:
        a, d = axes[uid], dist[uid]
        print(f"   {uid:24s} slope {a['mean_slope_deg']:8.3f}  relief {a['mean_relief3_m']:9.2f}  "
              f"std {a['elev_std_m']:8.2f} | d_slope {d[0]:7.3f}  d_relief {d[1]:7.3f}  "
              f"d_std {d[2]:7.3f}  {'LAYER-1' if uid in layer1 else ''}")

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nwrote {OUT_JSON}")

# ---------------------------------------------------------------- figure
cmap = LinearSegmentedColormap.from_list("moon", ["#05070c", "#171b26", "#3a4053", "#6d7488", "#a8adbb", "#e9ecf2"])
fig = plt.figure(figsize=(13.33, 6.0), dpi=110, facecolor="#05070c")
ax = fig.add_axes([0.03, 0.06, 0.46, 0.82])
ls = LightSource(azdeg=315, altdeg=45)
rgb = ls.shade(moon, cmap=cmap, vert_exag=1.0, dx=moon_dx, dy=moon_dx, blend_mode="soft")
ax.imshow(rgb, interpolation="bilinear")
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_color("#1d2634")
fig.text(0.03, 0.92, "Lunar Site01 — Connecting ridge", color="#eef2f7", fontsize=15, fontweight="bold")
fig.text(0.03, 0.885, "real LOLA 5 m/px, south polar stereographic · 16 km across · NASA Goddard PGDA",
         color="#8c9aad", fontsize=10.5)

ax2 = fig.add_axes([0.56, 0.10, 0.41, 0.78])
ax2.set_facecolor("#05070c")
sup = results["scales"]["750m"]
names = ["LUNAR_Site01"] + [e[0] for e in EARTH]
vals = [sup["axes"][n]["elev_std_m"] for n in names]
cols = ["#e0913f"] + ["#6fd6c0" if n not in sup["layer1"] else "#f2d5ab" for n in names[1:]]
y = np.arange(len(names))[::-1]
ax2.barh(y, vals, color=cols, height=0.62)
ax2.set_yticks(y); ax2.set_yticklabels([n.replace("earth_", "").replace("LUNAR_", "") for n in names],
                                       color="#8c9aad", fontsize=10)
ax2.tick_params(axis="x", colors="#8c9aad", labelsize=9)
for s in ax2.spines.values():
    s.set_color("#1d2634")
ax2.set_xlabel("window elevation std (m) at the common 750 m support", color="#8c9aad", fontsize=10)
ax2.set_title("declared axis 3 of 3 · exploratory", color="#8c9aad", fontsize=10.5, loc="left")
fig.savefig(OUT_PNG, facecolor="#05090f")
print(f"wrote {OUT_PNG}")
