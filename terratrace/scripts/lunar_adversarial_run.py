"""Run the lunar panel's adversarial stress test on the real DEMs.

The perturbation space and the pass/fail rule are declared in `config/lunar_adversarial_v1.yml`,
committed BEFORE this script was run; `terratrace/lunar_adversarial.py` holds the decision half and
this script holds the data half. The panel definition -- sites, candidates, coordinates, axes -- is
imported from `scripts/lunar_sites_v2.py` rather than repeated, so the stress test cannot drift
away from the panel it is attacking.

The BASELINE is re-derived from the real data and checked against the committed v2 artifact before
anything else runs. A stress test against the wrong baseline is worse than no stress test.

Run in slices (the sandbox caps one shell call at ~178 s and the whole battery is longer):

    python scripts/lunar_adversarial_run.py --families footprint,resampling
    python scripts/lunar_adversarial_run.py --families candidate_dropout,pool_change
    python scripts/lunar_adversarial_run.py --merge

Output: `artifacts/lunar_adversarial/lunar_adversarial.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import lunar_sites_v2 as v2                                            # noqa: E402
from terratrace import common_grid as cg, lunar_adversarial as la, reproject  # noqa: E402

OUT_DIR = ROOT / "artifacts" / "lunar_adversarial"
PARTS = OUT_DIR / "parts"
CACHE = OUT_DIR / "cache"
OUT = OUT_DIR / "lunar_adversarial.json"
V2_ARTIFACT = ROOT / "artifacts" / "lunar_sites_v2" / "lunar_sites_v2.json"
CONFIG = ROOT / "config" / "lunar_adversarial_v1.yml"
MIN_VALID_FRACTION = 0.5

ADDED = {"earth_andean_volcano": {"file": "andean_volcano_cop30.tif", "lon": -78.45, "lat": -0.05,
                                  "label": "Equatorial Andean volcanic terrain (Ecuador)"}}

# The v2 panel's candidate pool, fixed before v2 ran. An added unit joins ONLY when a spec names it
# in `add_units`; otherwise it would silently be part of the baseline and the baseline would not be
# the panel under attack.
BASE_CANDIDATES = [uid for uid, _where, _f, _lon, _lat in v2.CANDIDATES]


# --------------------------------------------------------------------------- #
# Data access, with a disk cache keyed by the read specification              #
# --------------------------------------------------------------------------- #
def _read_key(path, lat, lon, body, support, n, resampling, posting):
    blob = f"{path}|{lat!r}|{lon!r}|{body}|{support!r}|{n}|{resampling}|{posting!r}"
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def read_cached(path, lat, lon, body, support, n, resampling, posting):
    """One destination-grid read, memoised on disk.

    The cache exists so a perturbation that changes only the DECISION (dropping an axis or a
    candidate, perturbing the arrays) does not re-warp the DEMs -- and so the ~30-perturbation
    battery fits in the shell-call budget. It caches the READ only, never the derived numbers, so a
    mask or a perturbation is always applied to the true source array.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    key = _read_key(path, lat, lon, body, support, n, resampling, posting)
    f = CACHE / f"{key}.npy"
    if f.exists():
        return np.load(f)
    z, _rec = cg.read_exact(path, lat, lon, body, support, n, resampling=resampling,
                            source_posting_m=posting)
    np.save(f, z)
    return z


def shift_centre(lat, lon, body, support_m, n_cells, dx_m, dy_m):
    """Move the window centre by (east, north) GROUND metres and return the new (lat, lon).

    The shift is expressed in the body's local azimuthal-equidistant frame -- the same frame the
    destination grid is built in -- so the identical number of ground metres is applied on the Moon
    and on Earth. Shifting in degrees, or in source pixels, would move the two sides by different
    amounts and break the very equality the v2 correction established.
    """
    if dx_m == 0.0 and dy_m == 0.0:
        return lat, lon
    from rasterio.warp import transform as _transform
    crs, _coeffs, _half = cg.destination_grid(lat, lon, body, support_m, n_cells)
    lon2, lat2 = _transform(crs, reproject.geographic_crs(body), [dx_m], [dy_m])
    return float(lat2[0]), float(lon2[0])


# --------------------------------------------------------------------------- #
# One specification -> one panel evaluation                                   #
# --------------------------------------------------------------------------- #
def unit_sources():
    """Every unit the stress test can place on the grid: six lunar references, eight candidates."""
    moon, earth = {}, {}
    for sid, sname in v2.SITES:
        f = v2.MOON / f"{sid}_surf.tif"
        if f.exists():
            lat, lon = v2.moon_centre(f)
            moon[f"LUNAR_{sid}"] = {"path": f, "lat": lat, "lon": lon, "body": "moon",
                                    "posting": None, "name": sname}
    for uid, where, fname, lon, lat in v2.CANDIDATES:
        earth[uid] = {"path": v2.EARTH / fname, "lat": lat, "lon": lon, "body": "earth",
                      "posting": v2.EARTH_POSTING_M, "name": where}
    for uid, info in ADDED.items():
        f = v2.EARTH / info["file"]
        if f.exists():
            earth[uid] = {"path": f, "lat": info["lat"], "lon": info["lon"], "body": "earth",
                          "posting": v2.EARTH_POSTING_M, "name": info["label"]}
    return moon, earth


def evaluate_spec(spec, moon, earth, reference_ids):
    """Evaluate one perturbation spec on the real data. Returns the per-cell comparison rows."""
    arrays_by_support, records_by_support = {}, {}
    for support in spec["supports"]:
        n = cg.plan(spec["footprint_m"], support)
        dx, dy = spec["centre_shift_m"]
        arrays, recs = {}, {}
        for uid, src in list(moon.items()) + list(earth.items()):
            lat, lon = shift_centre(src["lat"], src["lon"], src["body"], support, n, dx, dy)
            z = read_cached(str(src["path"]), lat, lon, src["body"], support, n,
                            spec["resampling"], src["posting"])
            z = np.array(z, dtype=float)
            if spec["border_ring"]:
                z = la.apply_border_ring(z, spec["border_ring"])
            if spec["tail_fraction"]:
                z = la.apply_tail_mask(z, spec["tail_fraction"])
            arrays[uid] = z
        if spec["array_perturbation"]:
            arrays = la.perturb_arrays(arrays, spec["array_perturbation"], support, seed=0)
        for uid in spec["drop_units"]:
            arrays.pop(uid, None)
        for uid in spec["add_units"]:
            if uid not in arrays:
                raise KeyError(f"{spec['label']}: unit to add {uid!r} is not available on disk")
        for uid, z in arrays.items():
            rec = {"cells": [n, n], "support_m_requested": float(support),
                   "footprint_m": [n * float(support), n * float(support)], "exact": True,
                   "source_posting_m": 5.0 if uid.startswith("LUNAR_") else v2.EARTH_POSTING_M}
            rec["source_floor_m"] = cg.effective_floor_m("moon" if uid.startswith("LUNAR_")
                                                         else "earth", rec["source_posting_m"])
            cg.resolution_gate(rec, label=f"{spec['label']}/{uid}@{support:.0f}m")
            if not np.isfinite(z).any():
                raise ValueError(f"{spec['label']}/{uid}@{support:.0f}m: no finite cells at all")
            frac = float(np.isfinite(z).mean())
            if frac < MIN_VALID_FRACTION:
                raise ValueError(f"{spec['label']}/{uid}@{support:.0f}m: valid fraction {frac:.3f} "
                                 f"below the declared floor {MIN_VALID_FRACTION}")
            recs[uid] = rec
        cg.assert_comparable(recs, label=f"{spec['label']} @ {support:.0f} m")
        arrays_by_support[f"{support:.0f}"] = arrays
        records_by_support[f"{support:.0f}"] = {u: {"valid_fraction": float(np.isfinite(z).mean()),
                                                   "source_posting_m": recs[u]["source_posting_m"]}
                                               for u, z in arrays.items()}
    panel = {}
    for key, arrays in arrays_by_support.items():
        # The panel's structure, preserved exactly: each lunar site is a REFERENCE compared against
        # the Earth CANDIDATE POOL -- the sites are not mutual candidates, and a unit added by a
        # `pool_change` spec joins only when that spec names it. Feeding all six sites in as one
        # pool makes them compete with each other, and letting the eighth candidate into the
        # baseline would mean the baseline is not the panel under attack. Both mistakes are caught
        # by the baseline reproduction check rather than reported.
        cands = [u for u in BASE_CANDIDATES + list(spec["add_units"]) if u in arrays]
        sub = la.panel_layer1(arrays, float(key), [r for r in reference_ids if r in arrays],
                              cands, axes=spec["axes"])
        for ref, l1 in sub.items():
            panel.setdefault(ref, {})[key] = l1
    return panel, records_by_support


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #
def run_families(families):
    moon, earth = unit_sources()
    reference_ids = sorted(moon)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PARTS.mkdir(parents=True, exist_ok=True)

    base_spec = la.base_spec()
    if any(f == "baseline" for f in families):
        t = time.time()
        panel, recs = evaluate_spec(base_spec, moon, earth, reference_ids)
        committed = json.loads(V2_ARTIFACT.read_text(encoding="utf-8"))
        # The committed artifact keys scales by support ("500m") and each block by site id
        # ("Site01"); this driver keys references by unit id ("LUNAR_Site01"). Read across, do not
        # assume the shapes match.
        want = {f"LUNAR_{sid}": {f"500": committed["scales"]["500m"][sid]["layer1"],
                                 f"750": committed["scales"]["750m"][sid]["layer1"],
                                 f"1000": committed["scales"]["1000m"][sid]["layer1"]}
                for sid, _ in v2.SITES if f"LUNAR_{sid}" in reference_ids}
        # read_cached keys supports as "%.0f"; make the committed side use the same keys
        got = {r: {k: list(v) for k, v in per.items()} for r, per in panel.items()}
        if got != want:
            raise SystemExit(
                "the stress test did NOT reproduce the committed v2 panel, so it would be "
                "attacking the wrong baseline. Refusing to run.\n"
                f"  committed: {json.dumps(want, sort_keys=True)}\n"
                f"  re-derived: {json.dumps(got, sort_keys=True)}")
        (PARTS / "_baseline.json").write_text(json.dumps(
            {"panel": panel, "records": recs, "seconds": time.time() - t,
             "reproduces_v2_artifact": True}, indent=2), encoding="utf-8")
        print(f"baseline RE-DERIVED and identical to {V2_ARTIFACT.name} "
              f"({len(reference_ids)} references x 3 supports), {time.time() - t:.1f}s")
        for r in reference_ids:
            print(f"   {r:12s} " + "  ".join(f"{s}={panel[r][s]}" for s in sorted(panel[r])))
        return 0

    base = json.loads((PARTS / "_baseline.json").read_text(encoding="utf-8"))
    baseline = base["panel"]
    for fam in families:
        specs = [s for s in la.declared_specs() + la.informational_specs() if s["family"] == fam]
        if not specs:
            print(f"  [{fam}] no declared perturbation; skipped")
            continue
        rows = []
        for spec in specs:
            t = time.time()
            panel, recs = evaluate_spec(spec, moon, earth, reference_ids)
            cmp_ = la.compare_to_baseline(baseline, panel, spec.get("support_map"))
            rows.append({"label": spec["label"], "family": spec["family"], "counted": spec["counted"],
                         "n_cells": cmp_["n_cells"], "n_changed": cmp_["n_changed"],
                         "changed": cmp_["changed"], "stable_fraction": cmp_["stable_fraction"],
                         "panel": panel, "records": recs, "seconds": round(time.time() - t, 1)})
            state = "STABLE  " if cmp_["n_changed"] == 0 else f"REVERSES({cmp_['n_changed']})"
            print(f"  {spec['label']:34s} {state:12s} changed {cmp_['n_changed']}/{cmp_['n_cells']}"
                  f"  {rows[-1]['seconds']:6.1f}s")
            for c in cmp_["changed"][:4]:
                print(f"        {c['reference']} @ {c['support']}m: {c['baseline_layer1']} -> "
                      f"{c['perturbed_layer1']}")
        (PARTS / f"{fam}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nwrote parts for {', '.join(families)}")
    return 0


def merge():
    base = json.loads((PARTS / "_baseline.json").read_text(encoding="utf-8"))
    rows = []
    for fam in la.FAMILIES:
        f = PARTS / f"{fam}.json"
        if f.exists():
            rows.extend(json.loads(f.read_text(encoding="utf-8")))
    order = {lab: i for i, lab in enumerate(la.declared_labels())}
    rows.sort(key=lambda r: order.get(r["label"], 10_000))
    missing = [lab for lab in la.declared_labels() if lab not in {r["label"] for r in rows}]
    if missing:
        raise SystemExit(f"refusing to merge: no part produced these declared perturbations: {missing}")
    summary = la.stability(rows)
    artifact = {
        "provenance": {
            "status": json.loads(_yaml_scalars(CONFIG))["status"],
            "what": "adversarial stress test on the corrected exploratory lunar panel",
            "not": "not confirmation; not a new pre-registration; the same data was examined in "
                   "v1 and v2 first",
            "config": "config/lunar_adversarial_v1.yml (committed BEFORE the run)",
            "panel": "artifacts/lunar_sites_v2/lunar_sites_v2.json (baseline re-derived and "
                     "verified identical before any perturbation ran)",
            "perturbation_space": "supports, footprint_m, centre_shift_m, resampling, border_ring, "
                                  "tail_fraction, array_perturbation, axes, pool",
            "primary_metric": "perturbation-level: stable only if EVERY site x support cell keeps "
                              "the baseline layer-1 set",
            "excluded": "info_drop_winner:earth_nevada_basin is reported but NOT counted -- "
                        "removing the winner answers a different question",
            "seed": 0,
            "thresholds": la.THRESHOLDS,
            "scope": "map-scale terrain-MORPHOLOGY screening only; a robust verdict is never true "
                     "and upgrades no traversability, geologic-equivalence, site-access or "
                     "mission-readiness claim",
        },
        "baseline": {"layer1": {r: baseline_layer1_for(base["panel"], r)
                                for r in sorted(base["panel"])},
                     "reproduces_v2_artifact": base["reproduces_v2_artifact"],
                     "n_cells": sum(len(v) for v in base["panel"].values())},
        "declared_labels": la.declared_labels(),
        "perturbations": rows,
        "summary": summary,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    print("=" * 78)
    print("LUNAR PANEL -- ADVERSARIAL STRESS TEST")
    print("=" * 78)
    print(f"baseline: layer-1 = {artifact['baseline']['layer1']} over "
          f"{artifact['baseline']['n_cells']} site x support cells")
    print(f"counted perturbations: {summary['n_counted_perturbations']}")
    print(f"stable (every cell unchanged): {summary['n_stable_perturbations']}")
    print(f"perturbation-level stable fraction: {summary['perturbation_stable_fraction']:.3f}")
    print(f"cell-level stable fraction: {summary['cell_stable_fraction']:.3f} "
          f"({summary['n_changed_cells']}/{summary['n_cells']})")
    print(f"VERDICT: {summary['verdict'].upper()}")
    if summary["reversing_perturbations"]:
        print("\nreversing conditions:")
        for lab in summary["reversing_perturbations"]:
            r = next(x for x in rows if x["label"] == lab)
            print(f"  {lab}: {r['n_changed']}/{r['n_cells']} cells changed")
    for info in summary["informational"]:
        print(f"\ninformational (not counted): {info['label']}")
        for ref in sorted(info["resulting_layer1"] or {}):
            print(f"   {ref:12s} -> {info['resulting_layer1'][ref]}")
    print(f"\nwrote {OUT}")
    return 0


def baseline_layer1_for(panel, ref):
    """The baseline layer-1 per support, collapsed to a label when it is the same everywhere."""
    vals = {s: panel[ref][s] for s in sorted(panel[ref])}
    uniq = {tuple(v) for v in vals.values()}
    return list(next(iter(uniq))) if len(uniq) == 1 else vals


def _yaml_scalars(path):
    """Minimal read of the frozen config's `status:` line, so provenance is not hand-copied."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("status:"):
            return json.dumps({"status": line.split(":", 1)[1].strip()})
    return json.dumps({"status": "UNKNOWN"})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", default="",
                    help="comma-separated families (or 'baseline') to run in this slice")
    ap.add_argument("--merge", action="store_true", help="merge parts into the final artifact")
    args = ap.parse_args(argv)
    if args.merge:
        return merge()
    fams = [f.strip() for f in args.families.split(",") if f.strip()]
    if not fams:
        raise SystemExit("give --families (or 'baseline'), or --merge")
    return run_families(fams)


if __name__ == "__main__":
    raise SystemExit(main())
