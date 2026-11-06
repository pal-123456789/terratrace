"""Fetch the Earth candidate tiles for a TerraTrace benchmark config.

Two sources are supported:

``--source cog``
    The **public ESA Copernicus GLO-30 COG mosaic on AWS** -- no API key, no
    account, windowed HTTP range reads (see :mod:`terratrace.cop30_cog`). This
    is the default because it removes the OpenTopography key as a blocker.

``--source opentopo``
    The OpenTopography ``globaldem`` endpoint, which needs ``OPENTOPO_API_KEY``
    in the environment.

The two are the SAME ESA product: the COG mosaic reproduces the OpenTopography
COP30 elevations exactly (max absolute difference 0.0 m over the Craters of the
Moon and Nevada AOI tiles). Use either; they are not independent observations.

Tiles are written to ``data/earth/`` and are skipped if already present, so the
script is idempotent.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terratrace import cop30_cog


def _center_bbox(center_lon_e, center_lat, extent_m, body="earth"):
    """Symmetric lon/lat bbox of side ``extent_m`` about a centre."""
    r_earth = 6371000.0
    r_mars = 3396190.0
    radius = r_mars if body == "mars" else r_earth
    half = extent_m / 2.0
    dlat = math.degrees(half / radius)
    dlon = math.degrees(half / (radius * math.cos(math.radians(center_lat))))
    return (center_lon_e - dlon, center_lat - dlat,
            center_lon_e + dlon, center_lat + dlat)


def fetch_units(cfg, out_dir, source="cog", force=False, api_key=None):
    """Fetch every Earth unit in a config. Returns ``[(id, path, status)]``."""
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for u in cfg.get("units", []):
        uid = u["id"]
        if u.get("body", "earth") != "earth":
            continue
        path = u.get("path") or os.path.join("data", "earth", f"{uid}.tif")
        if not os.path.isabs(path):
            path = os.path.join(out_dir, os.path.basename(path))
        if os.path.exists(path) and not force:
            results.append((uid, path, "cached"))
            continue
        bbox = u.get("bbox")
        if not bbox:
            bbox = _center_bbox(u["center_lon_e"], u["center_lat"],
                                float(u.get("extent_m", 60000.0)))
        if source == "cog":
            cop30_cog.fetch_cop30_cog(bbox, path)
            status = "fetched (public ESA COG, no API key)"
        else:
            from terratrace import ingest
            if not api_key:
                raise SystemExit("--source opentopo needs OPENTOPO_API_KEY in the environment")
            ingest.fetch_copernicus_glo30(bbox, api_key, path)
            status = "fetched (OpenTopography globaldem)"
        results.append((uid, path, status))
        print(f"[fetch] {uid}: {status} -> {path}", flush=True)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, help="benchmark YAML/JSON config")
    ap.add_argument("--out-dir", default=os.path.join("data", "earth"))
    ap.add_argument("--source", choices=("cog", "opentopo"), default="cog")
    ap.add_argument("--force", action="store_true", help="re-fetch tiles that exist")
    args = ap.parse_args(argv)

    cfg = _load_config(args.config)
    key = os.environ.get("OPENTOPO_API_KEY")
    results = fetch_units(cfg, args.out_dir, source=args.source,
                          force=args.force, api_key=key)
    print(f"[fetch] {len(results)} Earth unit(s) ready")
    return 0


def _load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith((".yml", ".yaml")):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("PyYAML is needed to read a YAML config") from exc
        return yaml.safe_load(text)
    import json
    return json.loads(text)


if __name__ == "__main__":
    raise SystemExit(main())
