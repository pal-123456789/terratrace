"""Lunar panel v2 — the CORRECTED exploratory reanalysis on an exact common grid.

This replaces the comparison method of `lunar_sites_demo.py` (v1) without touching its artifact.
The defect v1 shipped is in `terratrace/common_grid.py`'s module docstring with the measurements;
the protocol frozen before this run is `config/lunar_panel_v2.yml` and `docs/LUNAR-PROTOCOL-v2.md`.

What changes: BOTH bodies are warped from their native source straight into an exact destination
grid in the body's local azimuthal-equidistant CRS, at a fixed 9000 m footprint, with area-weighted
resampling. So a 500 m cell is 500 m of ground on the Moon and on Earth, the footprint is identical
on both sides, and nothing is silently resized.

What does NOT change, deliberately: the three declared axes, the seven candidates, the six sites,
and the Pareto decision rule. Changing those at the same time would confound a correction with a
new analysis.

Output: `artifacts/lunar_sites_v2/lunar_sites_v2.json`.

Status: CORRECTED EXPLORATORY REANALYSIS. Same data, already examined in v1. This is not
independent confirmation and not a new pre-registration, and the artifact says so in its own
provenance block.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from terratrace import common_grid as cg, decision, evidence, features, reproject  # noqa: E402

MOON = ROOT / "data" / "moon"
EARTH = ROOT / "data" / "earth"
OUT = ROOT / "artifacts" / "lunar_sites_v2" / "lunar_sites_v2.json"

FOOTPRINT_M = cg.DEFAULT_FOOTPRINT_M
SUPPORTS = [500.0, 750.0, 1000.0]
AXES = ["mean_slope_deg", "mean_relief3_m", "elev_std_m"]

SITES = [("Site01", "Connecting ridge"), ("Site04", "Shackleton rim"),
         ("Site07", "Peak near Shackleton"), ("Site11", "de Gerlache rim"),
         ("Site20", "Leibnitz beta plateau"), ("Site23", "Malapert massif")]

CANDIDATES = [
    ("earth_nullarbor", "Australia", "nullarbor_cop30.tif", 129.0, -30.3),
    ("earth_llano_estacado", "USA", "llano_estacado_cop30.tif", -102.0, 33.0),
    ("earth_deccan_traps", "India", "deccan_traps_cop30.tif", 76.0, 20.0),
    ("earth_snake_river_plain", "USA", "snake_river_plain_cop30.tif", -114.05, 43.05),
    ("earth_harrat_khaybar", "Saudi Arabia", "harrat_khaybar_cop30.tif", 40.0, 25.5),
    ("earth_odadahraun", "Iceland", "odadahraun_cop30.tif", -16.54, 65.23),
    ("earth_nevada_basin", "USA", "nevada_basin_cop30.tif", -115.6, 36.2),
]

EARTH_POSTING_M = 30.0
V1_ARTIFACT = ROOT / "artifacts" / "lunar_sites" / "lunar_sites_exploratory.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def axes_of(z, dx):
    """The three declared axes, NaN-safe. Unchanged from v1 so the correction is isolated."""
    slope = features.slope_deg(z, dx, dx)
    relief = features.relief(z, window=3, alpha=0.0)
    finite = np.isfinite(z)
    return {"mean_slope_deg": float(np.nanmean(slope)),
            "mean_relief3_m": float(np.nanmean(relief)),
            "elev_std_m": float(np.nanstd(z[finite]))}


def distances(axes, ref):
    """Fractional distance to the reference per axis: the engine's own Pareto input. Unchanged."""
    out = {}
    for uid, a in axes.items():
        if uid == ref:
            continue
        out[uid] = [abs(a[k] - axes[ref][k]) / abs(axes[ref][k]) if axes[ref][k] else float("nan")
                    for k in AXES]
    return out


def moon_centre(path):
    """The window centre in the MOON's own geographic CRS.

    Not EPSG:4326: that is Earth's datum and PROJ correctly refuses to transform between two
    different bodies' ellipsoids. The site centre has to be expressed on the same body.
    """
    import rasterio
    from rasterio.warp import transform as warp_transform
    with rasterio.open(path) as ds:
        b = ds.bounds
        lon, lat = warp_transform(ds.crs, reproject.geographic_crs("moon"),
                                  [(b[0] + b[2]) / 2], [(b[1] + b[3]) / 2])
        return float(lat[0]), float(lon[0])


def rankdata(v):
    """Average ranks, for Spearman without pulling in scipy."""
    v = np.asarray(v, dtype=float)
    order = v.argsort()
    ranks = np.empty(len(v), dtype=float)
    ranks[order] = np.arange(1, len(v) + 1, dtype=float)
    # average ties
    _, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    if (counts > 1).any():
        for i, c in enumerate(counts):
            if c > 1:
                idx = np.where(inv == i)[0]
                ranks[idx] = ranks[idx].mean()
    return ranks


def correlations(rows):
    """Pearson and Spearman over the compared units, so three axes are not read as three facts."""
    m = np.asarray(rows, dtype=float)
    out = {}
    for i, a in enumerate(AXES):
        for b in AXES[i + 1:]:
            j = AXES.index(b)
            x, y = m[:, i], m[:, j]
            if np.std(x) == 0 or np.std(y) == 0:
                out[f"{a}|{b}"] = {"pearson": None, "spearman": None, "note": "degenerate, no spread"}
                continue
            pear = float(np.corrcoef(x, y)[0, 1])
            spear = float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
            out[f"{a}|{b}"] = {"pearson": pear, "spearman": spear}
    return out


def leave_one_axis_out(dist):
    """Which units stay non-dominated when each axis is dropped: is one axis doing all the work?"""
    out = {}
    for drop in AXES:
        keep = [i for i, a in enumerate(AXES) if a != drop]
        sub = {u: [d[i] for i in keep] for u, d in dist.items()}
        out[f"without_{drop}"] = sorted(decision.non_dominated(sub))
    return out


def main():
    cells = {s: cg.plan(FOOTPRINT_M, s) for s in SUPPORTS}
    print(f"exact common grid: footprint {FOOTPRINT_M:.0f} m, supports {SUPPORTS}")
    print(f"  cells per side: " + ", ".join(f"{int(s)}m->{cells[s]}x{cells[s]}" for s in SUPPORTS))

    # ---- Earth candidates: exact grid straight from the native Copernicus source
    earth_axes, earth_records = {}, {}
    for target in SUPPORTS:
        n = cells[target]
        per, recs = {}, {}
        for uid, where, fname, lon, lat in CANDIDATES:
            z, rec = cg.read_exact(EARTH / fname, lat, lon, "earth", target, n,
                                   source_posting_m=EARTH_POSTING_M)
            cg.resolution_gate(rec, label=f"{uid} @ {target:.0f} m")
            per[uid] = axes_of(z, target)
            recs[uid] = rec
        earth_axes[target], earth_records[target] = per, recs

    results = {
        "provenance": {
            "status": "CORRECTED EXPLORATORY REANALYSIS",
            "not": "not independent confirmation, and not a new pre-registration: the same data "
                   "was examined in v1 before this correction existed",
            "supersedes_method_of": "artifacts/lunar_sites/lunar_sites_exploratory.json (v1, "
                                    "preserved unchanged as the record of what was computed)",
            "protocol": "config/lunar_panel_v2.yml, docs/LUNAR-PROTOCOL-v2.md",
            "footprint_m": FOOTPRINT_M,
            "supports_m": SUPPORTS,
            "cells_per_side": {str(int(s)): cells[s] for s in SUPPORTS},
            "axes": AXES,
            "decision": "decision.non_dominated (Pareto on fractional axial distance; no composite)",
            "grid": "both bodies warped from the native source into an exact destination grid in "
                    "the body's local azimuthal-equidistant CRS, area-weighted resampling",
            "masks": "none",
            "mars_excluded_because": "MOLA effective floor 1389 m exceeds every support tested",
            "uncertainty_input": "author-published perturbed DEM clones; Site01 only",
        },
        "scales": {}, "ensemble": {}, "grid_records": {}, "analysis": {},
    }

    # ---- every site, every support, on the exact grid
    for target in SUPPORTS:
        key = f"{int(target)}m"
        n = cells[target]
        results["scales"][key] = {}
        recs_this = dict(earth_records[target])
        for sid, sname in SITES:
            surf = MOON / f"{sid}_surf.tif"
            if not surf.exists():
                print(f"  {sid}: absent, skipped")
                continue
            lat, lon = moon_centre(surf)
            z, rec = cg.read_exact(surf, lat, lon, "moon", target, n)
            cg.resolution_gate(rec, label=f"LUNAR_{sid} @ {target:.0f} m")
            recs_this[f"LUNAR_{sid}"] = rec
            vecs = {f"LUNAR_{sid}": axes_of(z, target)}
            vecs.update(earth_axes[target])
            dist = distances(vecs, f"LUNAR_{sid}")
            results["scales"][key][sid] = {
                "support_m": rec["support_m_achieved"][0],
                "cells": rec["cells"],
                "footprint_m": rec["footprint_m"][0],
                "valid_fraction": rec["valid_fraction"],
                "grid": {"source_crs": rec["source_crs"], "destination_crs": rec["destination_crs"],
                         "resampling": rec["resampling"],
                         "source_posting_m": rec["source_posting_m"],
                         "source_floor_m": rec["source_floor_m"]},
                "reference_axes": vecs[f"LUNAR_{sid}"],
                "axis_distance_fraction": dist,
                "layer1": sorted(decision.non_dominated(dist)),
                "leave_one_axis_out": leave_one_axis_out(dist),
                "axis_correlations": correlations([[vecs[u][a] for a in AXES] for u in vecs]),
            }
        # The gate runs over EVERY unit of this comparison at once, on the actual records, so a
        # comparison that is not on equal ground cannot silently reach a ranking.
        cg.assert_comparable(recs_this, label=f"all units @ {target:.0f} m")
        results["grid_records"][key] = dict(recs_this)
        print(f"  {key}: {len(results['scales'][key])} sites compared on {n}x{n} cells of "
              f"{target:.0f} m = {n * target:.0f} m")

    # ---- error ensemble: Site01's own clones, on the exact grid
    clone_dir = MOON / "clones"
    clones = sorted(clone_dir.glob("Site01_*.tif")) if clone_dir.exists() else []
    if clones:
        surf = MOON / "Site01_surf.tif"
        lat, lon = moon_centre(surf)
        ens = {"n_draws": len(clones), "site": "Site01",
               "draws_available_at_source": 100,
               "honest_label": f"{len(clones)} sampled realisations of the 100 published for "
                               f"Site01 only — not a complete ensemble and not six sites",
               "scales": {}}
        for target in SUPPORTS:
            key = f"{int(target)}m"
            n = cells[target]
            point = results["scales"][key]["Site01"]
            counts, set_counts, ref_axes = {}, {}, []
            for c in clones:
                zc, _rec = cg.read_exact(c, lat, lon, "moon", target, n)
                vecs = {"LUNAR_Site01": axes_of(zc, target)}
                vecs.update(earth_axes[target])
                l1 = sorted(decision.non_dominated(distances(vecs, "LUNAR_Site01")))
                set_counts[tuple(l1)] = set_counts.get(tuple(l1), 0) + 1
                for u in l1:
                    counts[u] = counts.get(u, 0) + 1
                ref_axes.append(vecs["LUNAR_Site01"])
            point_set = tuple(sorted(point["layer1"]))
            ens["scales"][key] = {
                "n_realisations": len(clones),
                "point_estimate_layer1": sorted(point_set),
                "exact_set_match_count": int(set_counts.get(point_set, 0)),
                "exact_set_match_fraction": set_counts.get(point_set, 0) / len(clones),
                "candidate_layer1_count": {k: int(v) for k, v in sorted(counts.items())},
                "candidate_layer1_frequency": {k: v / len(clones) for k, v in sorted(counts.items())},
                "layer1_set_counts": {"+".join(k) if k else "(none)": v
                                      for k, v in sorted(set_counts.items())},
                "distinct_layer1_sets": len(set_counts),
                "reference_axis_range": {a: [min(r[a] for r in ref_axes),
                                             max(r[a] for r in ref_axes)] for a in AXES},
            }
        results["ensemble"] = ens
        problems = evidence.check_ensemble_counts(ens)
        if problems:
            raise SystemExit("the ensemble record is internally inconsistent, refusing to publish:"
                             "\n  " + "\n  ".join(problems))
        print(f"  ensemble: {len(clones)} of 100 published realisations, Site01 only")
        print("  ensemble self-check: counts, frequencies and set counts agree")

    # ---- the declared falsifier, evaluated and reported rather than assumed
    survivors, per_support = set(), {}
    for key, per_site in results["scales"].items():
        sets = [tuple(b["layer1"]) for b in per_site.values()]
        per_support[key] = sorted({u for s in sets for u in s})
        survivors.update(per_support[key])
    results["analysis"]["survivors_by_support"] = per_support
    results["analysis"]["survivor_union"] = sorted(survivors)
    results["analysis"]["v1_headline_survives"] = (
        all(s == ["earth_nevada_basin"] for s in per_support.values()))
    if V1_ARTIFACT.exists():
        v1 = json.loads(V1_ARTIFACT.read_text(encoding="utf-8"))
        results["analysis"]["v1_headline"] = "earth_nevada_basin sole non-dominated at every support"
        results["analysis"]["v1_file_sha256"] = sha256(V1_ARTIFACT)
        results["analysis"]["v1_unchanged"] = True
        del v1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")

    # ---- report
    for key, per_site in results["scales"].items():
        print(f"\nsupport {key} — {list(per_site.values())[0]['cells']} cells of "
              f"{list(per_site.values())[0]['support_m']:.0f} m "
              f"= {list(per_site.values())[0]['footprint_m']:.0f} m on every unit")
        for sid, _ in SITES:
            b = per_site.get(sid)
            if not b:
                continue
            r = b["reference_axes"]
            print(f"   {sid:7s} slope {r['mean_slope_deg']:7.3f}  relief {r['mean_relief3_m']:8.2f}"
                  f"  std {r['elev_std_m']:8.2f}  -> {b['layer1']}")
    print(f"\nsurvivors by support: {per_support}")
    print(f"v1 headline ('earth_nevada_basin' alone at every support) survives: "
          f"{results['analysis']['v1_headline_survives']}")
    if results["ensemble"]:
        for key, b in results["ensemble"]["scales"].items():
            print(f"  ensemble {key}: exact-set match {b['exact_set_match_count']}/"
                  f"{b['n_realisations']}, {b['distinct_layer1_sets']} distinct set(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
