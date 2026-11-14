"""Lunar screening on real LOLA terrain: all six published south-polar sites, plus an
error-ensemble test of whether the result survives the DEM's own uncertainty.

This supersedes `lunar_site01_demo.py` (one site, no uncertainty). It is EXPLORATORY, and the
distinction is carried in every output rather than in a footnote:

* the confirmatory Mars benchmark (protocol v3) is untouched;
* these are three DECLARED axes — mean slope, mean 3x3 relief, window elevation std — computed by
  the engine's own descriptor functions, NOT the frozen core-lens set;
* no base-suitability claim of any kind. Morphology only.

REGIME. Every published site is ~16 km across at 5 m/pixel, so the Mars study's 60 km extent is
impossible and the common support here is 500-1000 m. That is above the 3x-source floor for the
Moon (15 m) and for Earth (90 m) but BELOW MOLA's (1389 m), so **Mars is excluded by arithmetic
rather than convenience**. All six sites are analysed at the same declared supports.

UNCERTAINTY. The archive publishes 100 *clones* per site: realisations of the DEM drawn from its own
error covariance. They are the correct input for a propagation test, and they are used here instead
of independent per-pixel noise from the total-uncertainty raster. The reason is not pedantry: adding
independent Gaussian noise pixel-by-pixel and then aggregating to a 750 m block divides the mean
error by ~sqrt(22500) = 150, which would manufacture a stability the data does not have. LOLA's
errors are spatially correlated over the spot spacing, and the clones carry that correlation.

Output: `artifacts/lunar_sites/lunar_sites_exploratory.json` and `docs/figures/lunar-sites.png`.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt      # noqa: E402
import numpy as np                   # noqa: E402
import rasterio                      # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LightSource   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from terratrace import decision, features, matched_real, reproject, support  # noqa: E402

MOON = ROOT / "data" / "moon"
OUT_JSON = ROOT / "artifacts" / "lunar_sites" / "lunar_sites_exploratory.json"
OUT_PNG = ROOT / "docs" / "figures" / "lunar-sites.png"

EXTENT_M = 16000.0
SUPPORTS = [500.0, 750.0, 1000.0]
AXES = ["mean_slope_deg", "mean_relief3_m", "elev_std_m"]

# every published south-polar candidate region, named as the archive names them
SITES = [
    ("Site01", "Connecting ridge"),
    ("Site04", "Shackleton rim"),
    ("Site07", "Peak near Shackleton"),
    ("Site11", "de Gerlache rim"),
    ("Site20", "Leibnitz beta plateau"),
    ("Site23", "Malapert massif"),
]

EARTH = [
    ("earth_nullarbor", "Australia", "nullarbor_cop30.tif", -30.3, 129.0),
    ("earth_llano_estacado", "USA", "llano_estacado_cop30.tif", 33.0, -102.0),
    ("earth_deccan_traps", "India", "deccan_traps_cop30.tif", 20.0, 76.0),
    ("earth_snake_river_plain", "USA", "snake_river_plain_cop30.tif", 43.05, -114.05),
    ("earth_harrat_khaybar", "Saudi Arabia", "harrat_khaybar_cop30.tif", 25.5, 40.0),
    ("earth_odadahraun", "Iceland", "odadahraun_cop30.tif", 65.23, -16.54),
    ("earth_nevada_basin", "USA", "nevada_basin_cop30.tif", 36.2, -115.6),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def axes_of(z, dx):
    """The three declared axes, NaN-safe."""
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
    return agg, float(rec.target_support_m)


def centre_square(z, n):
    """Centre-crop to n x n, so every unit in a comparison covers the same ground."""
    h, w = z.shape
    n = min(n, h, w)
    r0, c0 = (h - n) // 2, (w - n) // 2
    return z[r0:r0 + n, c0:c0 + n]


def read_band(path):
    with rasterio.open(path) as ds:
        return ds.read(1).astype("float64"), float(ds.res[0])


def read_meta(path):
    with rasterio.open(path) as ds:
        return {"native_posting_m": float(ds.res[0]), "shape": [ds.height, ds.width],
                "crs": ds.crs.to_string() if ds.crs else None,
                "extent_km": round(ds.height * float(ds.res[0]) / 1000.0, 2)}


def distances(axes, ref):
    """Fractional distance to the reference on each declared axis (so the axes are commensurate
    without inventing a weighting, and the decision stays the engine's Pareto machinery)."""
    out = {}
    for uid, a in axes.items():
        if uid == ref:
            continue
        out[uid] = [abs(a[k] - axes[ref][k]) / abs(axes[ref][k]) if axes[ref][k] else float("nan")
                    for k in AXES]
    return out


def main():
    cells = {int(s): int(round(EXTENT_M / s)) for s in SUPPORTS}

    # ---------------- Earth candidates: axes depend only on the support, not on the lunar site,
    # so they are computed once per support instead of once per site.
    earth_raw = {}
    for uid, where, fname, lat, lon in EARTH:
        path = ROOT / "data" / "earth" / fname
        bbox = matched_real._center_bbox(lon, lat, EXTENT_M, "earth")
        z, dx = reproject.read_aoi_metric(path, bbox, 30.0, "earth")
        earth_raw[uid] = (np.asarray(z, dtype=float), float(dx))
    earth_axes = {}
    for target in SUPPORTS:
        n = cells[int(target)]
        per = {}
        for uid, (z, dx) in earth_raw.items():
            agg, sup = to_support(centre_square(z, int(round(EXTENT_M / dx))), dx, target)
            per[uid] = axes_of(centre_square(agg, n), sup)
        earth_axes[int(target)] = per

    provenance = {
        "product": "NASA Goddard PGDA 'South Pole Landing Site LOLA DEMs', 5 m/pixel",
        "archive": "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/",
        "citation": "Barker et al. (2021), Planet. Space Sci. 203, 105119; site numbering from "
                    "Mazarico et al. (2011), Icarus 211, 1066-1081",
        "extent_m": EXTENT_M, "supports_m": SUPPORTS, "axes": AXES,
        "decision": "decision.non_dominated (Pareto, no composite score)",
        "status": "EXPLORATORY -- not the frozen core-lens confirmatory panel; no base-suitability claim",
        "mars_excluded_because": "MOLA effective floor 1389 m exceeds every support tested here",
        "uncertainty_input": "author-published perturbed DEM clones (error covariance), not "
                             "independent per-pixel noise",
        "sites": {},
    }

    results = {"provenance": provenance, "scales": {}, "ensemble": {}}

    # ---------------- every site, at every support
    for sid, sname in SITES:
        surf = MOON / f"{sid}_surf.tif"
        if not surf.exists():
            print(f"  {sid}: surf raster absent, skipped")
            continue
        provenance["sites"][sid] = {"name": sname, "surf_sha256": sha256(surf), **read_meta(surf)}
        z, dx = read_band(surf)
        for target in SUPPORTS:
            key = f"{int(target)}m"
            n = cells[int(target)]
            agg, sup = to_support(z, dx, target)
            vecs = {f"LUNAR_{sid}": axes_of(centre_square(agg, n), sup)}
            vecs.update(earth_axes[int(target)])
            dist = distances(vecs, f"LUNAR_{sid}")
            results["scales"].setdefault(key, {})[sid] = {
                "support_m": sup, "cells": [n, n],
                "reference_axes": vecs[f"LUNAR_{sid}"],
                "axis_distance_fraction": dist,
                "layer1": sorted(decision.non_dominated(dist)),
            }
        print(f"  {sid} ({sname}): {read_meta(surf)['extent_km']} km across")

    # ---------------- self-check: the generalised code must reproduce the published single-site run
    ref = results["scales"]["750m"]["Site01"]
    published = ROOT / "artifacts" / "lunar_site01" / "lunar_site01_exploratory.json"
    if published.exists():
        old = json.loads(published.read_text(encoding="utf-8"))["scales"]["750m"]
        for axis in AXES:
            a, b = ref["reference_axes"][axis], old["axes"]["LUNAR_Site01"][axis]
            assert abs(a - b) < 1e-6, f"generalisation changed Site01 {axis}: {a} vs {b}"
        assert ref["layer1"] == old["layer1"], "generalisation changed the Site01 layer-1 set"
        print("  self-check: reproduces the published Site01 result exactly")

    # ---------------- error ensemble on the site that has clones
    clone_dir = MOON / "clones"
    clones = sorted(clone_dir.glob("Site01_*.tif")) if clone_dir.exists() else []
    if clones:
        z0, dx = read_band(MOON / "Site01_surf.tif")
        ens = {"n_draws": len(clones), "site": "Site01", "scales": {}}
        for target in SUPPORTS:
            key = f"{int(target)}m"
            n = cells[int(target)]
            point = results["scales"][key]["Site01"]
            members, ref_axes, sets = [], [], []
            for c in clones:
                zc, _ = read_band(c)
                fridge, sup = to_support(zc, dx, target)
                vecs = {f"LUNAR_Site01": axes_of(centre_square(fridge, n), sup)}
                vecs.update(earth_axes[int(target)])
                d = distances(vecs, "LUNAR_Site01")
                l1 = sorted(decision.non_dominated(d))
                sets.append(tuple(l1))
                members.extend(l1)
                ref_axes.append(vecs["LUNAR_Site01"])
            from collections import Counter
            counts = Counter(members)
            set_counts = Counter(sets)
            point_set = tuple(sorted(point["layer1"]))
            ens["scales"][key] = {
                "point_estimate_layer1": sorted(point_set),
                "exact_match_fraction": set_counts.get(point_set, 0) / len(clones),
                "candidate_layer1_frequency": {k: v / len(clones) for k, v in sorted(counts.items())},
                "distinct_layer1_sets": len(set_counts),
                "reference_axis_range": {
                    a: [min(r[a] for r in ref_axes), max(r[a] for r in ref_axes)] for a in AXES},
                "point_estimate_reference": {a: point["reference_axes"][a] for a in AXES},
            }
        results["ensemble"] = ens
        print(f"  ensemble: {len(clones)} clone realisation(s) of Site01's own error")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {OUT_JSON}")

    # ---------------- reporting
    for key in results["scales"]:
        print(f"\nsupport {key} ({cells[int(float(key[:-1]))]}x{cells[int(float(key[:-1]))]} cells)")
        for sid, _ in SITES:
            b = results["scales"][key].get(sid)
            if not b:
                continue
            r = b["reference_axes"]
            print(f"   {sid:7s} slope {r['mean_slope_deg']:7.3f}  relief {r['mean_relief3_m']:8.2f}  "
                  f"std {r['elev_std_m']:8.2f}  -> layer-1 {b['layer1']}")
        agree = [sid for sid, _ in SITES
                 if results["scales"][key].get(sid)
                 and results["scales"][key][sid]["layer1"] == results["scales"][key]["Site01"]["layer1"]]
        print(f"   sites whose layer-1 set equals Site01's: {len(agree)}/{len(SITES)} {agree}")

    if results["ensemble"]:
        print("\nensemble (Site01, author-published error realisations):")
        for key, b in results["ensemble"]["scales"].items():
            print(f"   {key}: exact-set match {b['exact_match_fraction']:.0%} over "
                  f"{results['ensemble']['n_draws']} draws, {b['distinct_layer1_sets']} distinct "
                  f"layer-1 set(s); point estimate {b['point_estimate_layer1']}")
            for k, v in b["candidate_layer1_frequency"].items():
                print(f"        {k:24s} in layer 1 for {v:.0%} of draws")

    # ---------------- figure: every site, and the ensemble frequencies
    cmap = LinearSegmentedColormap.from_list(
        "moon", ["#05070c", "#171b26", "#3a4053", "#6d7488", "#a8adbb", "#e9ecf2"])
    have = [s for s, _ in SITES if (MOON / f"{s}_surf.tif").exists()]
    fig = plt.figure(figsize=(13.8, 7.4), dpi=110, facecolor="#05070c")
    ls = LightSource(azdeg=315, altdeg=45)
    for i, sid in enumerate(have):
        z, dx = read_band(MOON / f"{sid}_surf.tif")
        ax = fig.add_axes([0.025 + (i % 3) * 0.24, 0.52 - (i // 3) * 0.42, 0.21, 0.36])
        rgb = ls.shade(z[::4, ::4], cmap=cmap, vert_exag=1.0, dx=dx * 4, dy=dx * 4,
                       blend_mode="soft")
        ax.imshow(rgb, interpolation="bilinear")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#1d2634")
        b = results["scales"]["750m"].get(sid)
        sub = f"slope {b['reference_axes']['mean_slope_deg']:.1f}° · relief {b['reference_axes']['mean_relief3_m']:.0f} m" if b else ""
        fig.text(0.025 + (i % 3) * 0.24, 0.895 - (i // 3) * 0.42,
                 f"{sid} — {dict(SITES)[sid]}", color="#eef2f7", fontsize=10.5, fontweight="bold")
        fig.text(0.025 + (i % 3) * 0.24, 0.875 - (i // 3) * 0.42, sub, color="#8c9aad", fontsize=8.5)
        fig.text(0.025 + (i % 3) * 0.24, 0.50 - (i // 3) * 0.42,
                 "real LOLA 5 m/px · 16 km", color="#5d6b7e", fontsize=8)

    ax2 = fig.add_axes([0.72, 0.10, 0.255, 0.80])
    ax2.set_facecolor("#05070c")
    names = [e[0] for e in EARTH]
    if results["ensemble"]:
        freqs = [results["ensemble"]["scales"]["750m"]["candidate_layer1_frequency"].get(n, 0.0)
                 for n in names]
        ax2.barh(np.arange(len(names))[::-1], [f * 100 for f in freqs],
                 color=["#6fd6c0" if f > 0 else "#2a3242" for f in freqs], height=0.6)
        ax2.set_yticks(np.arange(len(names))[::-1])
        ax2.set_yticklabels([n.replace("earth_", "") for n in names], color="#8c9aad", fontsize=9.5)
        ax2.set_xlabel("% of Site01 error realisations in which the candidate is on layer 1",
                       color="#8c9aad", fontsize=9)
        ax2.set_title("exploratory · does the answer survive the DEM's own error?",
                      color="#8c9aad", fontsize=9.5, loc="left")
        ax2.tick_params(axis="x", colors="#8c9aad", labelsize=8)
        for s in ax2.spines.values():
            s.set_color("#1d2634")
    fig.text(0.72, 0.93, "Every published south-polar site, screened", color="#eef2f7",
             fontsize=11, fontweight="bold")
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, facecolor="#05090f")
    print(f"wrote {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
