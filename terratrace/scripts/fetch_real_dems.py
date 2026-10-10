#!/usr/bin/env python3
"""Fetch real Earth DEMs for each AOI in the config (run on a networked machine).

Requires: pip install -r requirements-real.txt
Env: OPENTOPO_API_KEY (free key from https://portal.opentopography.org)

Pipeline per run:
  1. PREFLIGHT (no network): validate the config schema + every bbox, pick the
     catalog source that covers each AOI, and print an approximate request size,
     so a malformed or oversized AOI is caught before a byte is downloaded.
  2. FETCH, but IDEMPOTENT: a file already on disk is skipped (fetchcache), so a
     re-run does not re-download gigabytes. Every fetch is recorded in a JSON
     manifest (data/fetch_manifest.json) with size, sha256, and timestamp.
  3. QA: each file is profiled (valid/water/NaN, relief) with the source's known
     nodata sentinels applied first, when rasterio is present.

Flags: --preflight-only (report and exit), --skip-preflight (ignore hard
problems), --force (re-download even if cached), --manifest PATH.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import ingest, preflight, fetchcache, catalog

try:
    from terratrace import profile as demprofile
    from terratrace import masks
except Exception:  # pragma: no cover
    demprofile = None
    masks = None

_DEFAULT_MANIFEST = "data/fetch_manifest.json"


def _source_id_for_unit(unit):
    """Best-effort map a config unit to a catalog source id via its demtype/dataset,
    so we can look up that product's known nodata sentinels. Returns None if unknown."""
    demtype = unit.get("demtype")
    dataset = unit.get("dataset")
    for sid, s in catalog.SOURCES.items():
        acc = s.get("access", {})
        if demtype and acc.get("demtype") == demtype:
            return sid
        if dataset and acc.get("datasetName") == dataset:
            return sid
    return None


def _run_preflight(cfg):
    """Print the preflight report; return True if it is safe to proceed."""
    report = preflight.preflight_config(cfg)
    print(f"[preflight] target common support = {report['target_support_m']:g} m")
    for uid, u in report["units"].items():
        rec = u.get("recommended_source") or {}
        est = u.get("estimates") or {}
        src = rec.get("source_id")
        size = f"~{est['download_mb']:.1f} MB, ~{est['pixels']:,} px" if est else "size n/a"
        print(f"  - {uid}: {'OK ' if u['ok'] else 'FAIL'} source={src} {size}")
        for w in u.get("warnings", []):
            print(f"      ! warning: {w}")
    if report["problems"]:
        print("[preflight] PROBLEMS:")
        for p in report["problems"]:
            print(f"      x {p}")
    return report["ok"]


def _profile_file(path, unit):
    """Best-effort QA of a freshly fetched DEM (skipped if rasterio is absent).

    Applies the source's known nodata sentinels (catalog) before profiling so an
    undeclared void value does not distort the relief/percentile summary.
    """
    if demprofile is None or ingest.rasterio is None:
        return
    try:
        z, posting = ingest.load_dem_array(path)
    except Exception as exc:  # pragma: no cover - depends on the fetched file
        print(f"      ? QA skipped ({type(exc).__name__}: {exc})")
        return
    sid = _source_id_for_unit(unit)
    sentinels = catalog.nodata_sentinels_for(sid) if sid else []
    if sentinels and masks is not None:
        z = masks.apply_masks(z, mask_values=sentinels)
    s = demprofile.summarize(z, posting_m=posting)
    p = s["profile"]
    extra = f" (dropped sentinels {sentinels})" if sentinels else ""
    print(f"      QA: valid={p['valid_fraction']:.2f} water={p['water_fraction']:.2f} "
          f"relief={p['relief']:.1f} m flags={s['flags'] or 'none'} "
          f"{'OK' if s['ok'] else 'REVIEW'}{extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--skip-preflight", action="store_true",
                    help="download even if preflight reports hard problems")
    ap.add_argument("--preflight-only", action="store_true",
                    help="run the preflight report and exit without downloading")
    ap.add_argument("--force", action="store_true",
                    help="re-download even if the output file is already present")
    ap.add_argument("--manifest", default=_DEFAULT_MANIFEST,
                    help=f"fetch manifest path (default {_DEFAULT_MANIFEST})")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    ok = _run_preflight(cfg)
    if args.preflight_only:
        sys.exit(0 if ok else 2)
    if not ok and not args.skip_preflight:
        sys.exit("[preflight] aborting; fix the problems above or pass --skip-preflight.")

    key = os.environ.get("OPENTOPO_API_KEY")
    if not key:
        sys.exit("Set OPENTOPO_API_KEY (free key: https://portal.opentopography.org).")

    ref = cfg["reference"]
    if not os.path.exists(ref["path"]):
        print(f"[!] Mars reference missing: {ref['path']}")
        print("    Download 'Mars MGS MOLA DEM 463m' GeoTIFF from USGS Astrogeology")
        print("    https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m")

    manifest = fetchcache.load_manifest(args.manifest)
    for unit in cfg["earth_units"]:
        bbox = unit["bbox"]  # west, south, east, north
        out = unit["path"]
        need, reason = fetchcache.needs_fetch(out)
        if not need and not args.force:
            print(f"[=] {unit['id']} cached ({reason}): {out} -- skipping")
        else:
            dataset = unit.get("dataset")      # e.g. USGS10m / USGS30m / USGS1m
            if dataset:
                print(f"[*] fetching {unit['id']} 3DEP {dataset} bbox={bbox} -> {out}")
                ingest.fetch_usgs_3dep(bbox, key, out, dataset=dataset)
            else:
                demtype = unit.get("demtype", "COP30")
                print(f"[*] fetching {unit['id']} {demtype} bbox={bbox} -> {out}")
                ingest.fetch_opentopo_global(bbox, key, out, demtype=demtype)
            print(f"    done: {out}")
        # Record provenance (sha256/bytes/time) and QA whether fetched or cached.
        entry = fetchcache.record_entry(unit, path=out, source_id=_source_id_for_unit(unit))
        fetchcache.update_manifest(manifest, entry)
        _profile_file(out, unit)

    fetchcache.save_manifest(args.manifest, manifest)
    print(f"Manifest written: {args.manifest}")
    print("All Earth DEMs present. Next: scripts/run_real_study.py")


if __name__ == "__main__":
    main()
