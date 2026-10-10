#!/usr/bin/env python3
"""Fetch real Earth DEMs for each AOI in the config (run on a networked machine).

Requires: pip install -r requirements-real.txt
Env: OPENTOPO_API_KEY (free key from https://portal.opentopography.org)

A fail-fast PREFLIGHT runs first (no network): it validates every bbox, picks the
catalog source that actually covers each AOI, and prints an approximate size for
each request so a malformed or oversized AOI is caught before a single byte is
downloaded. Use --skip-preflight to bypass, --preflight-only to just report.
After each download the file is given a quick QA profile when rasterio is present.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import ingest, preflight

try:
    from terratrace import profile as demprofile
except Exception:  # pragma: no cover
    demprofile = None


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
        for p in u.get("problems", []):
            print(f"      x problem: {p}")
    if report["problems"]:
        print("[preflight] HARD PROBLEMS found:")
        for p in report["problems"]:
            print(f"    x {p}")
    return report["ok"]


def _profile_file(path):
    """Best-effort QA of a freshly fetched DEM (skipped if rasterio is absent)."""
    if demprofile is None or ingest.rasterio is None:
        return
    try:
        z, posting = ingest.load_dem_array(path)
    except Exception as exc:  # pragma: no cover - depends on the fetched file
        print(f"      ? QA skipped ({type(exc).__name__}: {exc})")
        return
    s = demprofile.summarize(z, posting_m=posting)
    p = s["profile"]
    print(f"      QA: valid={p['valid_fraction']:.2f} water={p['water_fraction']:.2f} "
          f"relief={p['relief']:.1f} m flags={s['flags'] or 'none'} "
          f"{'OK' if s['ok'] else 'REVIEW'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--skip-preflight", action="store_true",
                    help="download even if preflight reports hard problems")
    ap.add_argument("--preflight-only", action="store_true",
                    help="run the preflight report and exit without downloading")
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

    for unit in cfg["earth_units"]:
        bbox = unit["bbox"]  # west, south, east, north
        out = unit["path"]
        dataset = unit.get("dataset")          # e.g. USGS10m / USGS30m / USGS1m
        if dataset:
            print(f"[*] fetching {unit['id']} 3DEP {dataset} bbox={bbox} -> {out}")
            ingest.fetch_usgs_3dep(bbox, key, out, dataset=dataset)
        else:
            demtype = unit.get("demtype", "COP30")
            print(f"[*] fetching {unit['id']} {demtype} bbox={bbox} -> {out}")
            ingest.fetch_opentopo_global(bbox, key, out, demtype=demtype)
        print(f"    done: {out}")
        _profile_file(out)
    print("All Earth DEMs fetched. Next: scripts/run_real_study.py")


if __name__ == "__main__":
    main()
