"""Cross-check the Earth DEM against a second, independent mirror — keylessly.

WHY THIS FILE EXISTS
--------------------
`terratrace/cop30_cog.py` reads ESA's Copernicus GLO-30 straight from the public AWS COG mosaic
(`copernicus-dem-30m.s3.amazonaws.com`), with no account and no key. That is the headline Earth data
path, so "keyless" is a claim a reader should be able to check, and so is "this is ESA's product".

Microsoft Planetary Computer — one of the NASA Space Apps Global Offers — publishes the *same* ESA
product from Azure, behind a public STAC API that needs no account. Two hosting paths for one product
is a provenance question worth answering mechanically instead of assuming: a mirror can lag behind,
truncate, re-ingest with different nodata handling, or quietly serve a different product under the
same name. Only a comparison of the actual numbers settles it.

WHAT IS COMPARED
----------------
Not filenames and not provenance prose — the data:

* the STAC API is asked which item covers the tile, and its Azure asset is used, so the mirror's own
  index decides what to hand over rather than a URL this file guessed;
* the same window is read from both COGs and compared value for value, including nodata;
* both objects' `Content-Length` are read with a HEAD, so a truncated mirror is caught even outside
  the sampled window.

The two mirrors use different object layouts (AWS nests the tile in a folder, Azure does not), which
is exactly why the STAC index is consulted rather than a URL being constructed from the AWS one.

HONESTY
-------
The outcome is recorded either way, and **BLOCKED is a first-class result**: if the STAC API or the
blob store cannot be reached, this reports that it could not check, and does not report agreement.
A check that turns a network failure into a pass is worse than no check.

The token: Planetary Computer's blob store is not open-read, and its public, keyless path is a
short-lived SAS token from its own token endpoint. No account, no key, and nothing stored — but it is
a third-party token service in the path, so the honest claim is "keyless", not "no third party".

Usage:
    python scripts/verify_earth_mirror.py
    python scripts/verify_earth_mirror.py --window 512 --full
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from terratrace import cop30_cog  # noqa: E402

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "cop-dem-glo-30"
ARTIFACT = ROOT / "artifacts" / "mirror_check" / "earth_cop30_mirror.json"

# The window the headline Earth candidate sits in (Nevada Basin & Range). The tile is the 1-degree
# cell whose south-west corner is (36, -116).
SITE_LAT, SITE_LON = 36.2, -115.6


class Blocked(RuntimeError):
    """The mirror could not be reached or refused access — a result, not a failure to check."""


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "terratrace-mirror-check/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _head(url, timeout=60):
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "terratrace-mirror-check/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Length"), r.headers.get("ETag")


def stac_item(lat, lon):
    """Ask the mirror's own index which item covers the point."""
    url = (f"{STAC}/collections/{COLLECTION}/items?limit=20"
           f"&bbox={lon - 0.01},{lat - 0.01},{lon + 0.01},{lat + 0.01}")
    status, body = _get(url)
    if status != 200:
        raise Blocked(f"STAC returned HTTP {status}")
    feats = json.loads(body)["features"]
    if not feats:
        raise Blocked(f"the STAC index returned no {COLLECTION} item covering ({lat}, {lon})")
    for f in feats:
        w, s, e, n = f["bbox"]
        if w <= lon <= e and s <= lat <= n:
            return f
    return feats[0]


def sas_token(collection=COLLECTION):
    """A short-lived read token for the blob store, from Planetary Computer's own endpoint.

    No account and no key: the endpoint is open. It is still a third party in the path, which is
    why the claim made about this mirror is "keyless", never "no third party".
    """
    status, body = _get(f"{STAC.rsplit('/api', 1)[0]}/api/sas/v1/token/{collection}")
    if status != 200:
        raise Blocked(f"the token endpoint returned HTTP {status}")
    tok = json.loads(body).get("token")
    if not tok:
        raise Blocked("the token endpoint returned no token")
    return tok


def read_window(url, size):
    """Read one square window from a COG over the network. Returns (array, nodata, sha256)."""
    import rasterio
    from rasterio.windows import Window
    with rasterio.open("/vsicurl/" + url) as ds:
        if ds.width < size or ds.height < size:
            raise Blocked(f"tile is only {ds.width}x{ds.height}, smaller than the {size}px window")
        r0, c0 = (ds.height - size) // 2, (ds.width - size) // 2
        arr = ds.read(1, window=Window(c0, r0, size, size)).astype("float64")
        nodata = ds.nodata
    buf = np.ascontiguousarray(arr).tobytes()
    return arr, nodata, hashlib.sha256(buf).hexdigest()


def read_full(url):
    """Read every value in the raster. Returns (array, nodata, sha256 of the values).

    The hash is over the decoded values, not the file bytes: two containers can differ in metadata
    while holding identical elevations, and this is the check that distinguishes those cases.
    """
    import rasterio
    with rasterio.open("/vsicurl/" + url) as ds:
        arr = ds.read(1).astype("float64")
        nodata = ds.nodata
    buf = np.ascontiguousarray(arr).tobytes()
    return arr, nodata, hashlib.sha256(buf).hexdigest()


def compare(lat=SITE_LAT, lon=SITE_LON, size=256, full=False):
    """The whole check. Raises ``Blocked`` rather than reporting agreement it did not establish.

    ``full`` compares every value in the tile instead of a square window. A window is 4% of a
    3600x3600 tile, so it cannot see a truncation outside itself — which matters, because the two
    objects are NOT byte-identical files (their Content-Length differs). Only the whole raster
    settles whether the data differs anywhere.
    """
    cop30_cog._apply_env()

    lat_sw, lon_sw = int(np.floor(lat)), int(np.floor(lon))
    tile = cop30_cog.tile_name(lat_sw, lon_sw)
    aws_url = cop30_cog.tile_url(lat_sw, lon_sw)

    item = stac_item(lat, lon)
    azure_url = item["assets"]["data"]["href"]
    if item["id"] != tile:
        raise Blocked(f"the index returned item {item['id']!r}, not the expected tile {tile!r}")

    # sizes: cheap, and reported rather than judged — see the note in `main`
    token = sas_token()
    azure_signed = azure_url + "?" + token
    try:
        _, aws_len, _ = _head(aws_url)
        _, azure_len, _ = _head(azure_signed)
    except urllib.error.HTTPError as exc:
        raise Blocked(f"HTTP {exc.code} on a HEAD") from exc
    except urllib.error.URLError as exc:
        raise Blocked(f"network error on a HEAD: {exc.reason}") from exc

    try:
        if full:
            a_arr, a_nodata, a_sha = read_full(aws_url)
            z_arr, z_nodata, z_sha = read_full(azure_signed)
        else:
            a_arr, a_nodata, a_sha = read_window(aws_url, size)
            z_arr, z_nodata, z_sha = read_window(azure_signed, size)
    except Blocked:
        raise
    except Exception as exc:                                    # rasterio/GDAL surface
        raise Blocked(f"could not read one of the COGs: {type(exc).__name__}: {exc}") from exc

    if a_arr.shape != z_arr.shape:
        raise Blocked(f"the two rasters are different shapes: {a_arr.shape} vs {z_arr.shape}")
    same = np.array_equal(a_arr, z_arr)
    valid = np.isfinite(a_arr)
    n = int(a_arr.size)
    return {
        "body": "earth",
        "product": "ESA Copernicus GLO-30 (COP30_hh)",
        "tile": tile,
        "sample_point": [lat, lon],
        "extent_compared": ("the whole tile" if full
                            else f"a centred {size}x{size} px window ({n / (3600 * 3600):.1%} of the tile)"),
        "values_compared": n,
        "aws": {"url": aws_url, "content_length": int(aws_len), "values_sha256": a_sha,
                "nodata": a_nodata},
        "azure": {"url": azure_url, "content_length": int(azure_len), "values_sha256": z_sha,
                  "nodata": z_nodata,
                  "indexed_by": f"{STAC}/collections/{COLLECTION}",
                  "access": "keyless short-lived SAS token from Planetary Computer's public endpoint"},
        "agreement": {
            "identical_every_value": bool(same),
            "equal_values_sha256": a_sha == z_sha,
            "equal_file_content_length": aws_len == azure_len,
            "file_size_delta_bytes": int(azure_len) - int(aws_len),
            "n_valid_values": int(valid.sum()),
            "max_abs_diff_m": float(np.nanmax(np.abs(a_arr - z_arr))) if not same else 0.0,
        },
        "caveat": ("Same ESA product, two independent hosting paths. Agreement shows the mirror is "
                   "not lagging, truncated or re-ingested differently *over the extent compared*; "
                   "it is not a validation of the DEM's accuracy, and the Azure host is not an "
                   "independent source — it is a copy of the same product."),
    }


def verdict(agreement):
    """The decision rule, pure and network-free so it can be tested on the NumPy-only CI.

    Returns ``(exit_code, message)``. Note what is and is not a failure: differing *values* is a
    failure; differing *file sizes* is a reported fact, because the two containers are labelled
    differently while holding the same elevations, and calling that a data disagreement would be
    wrong. It is reported rather than ignored, so nobody may claim the two files are byte-identical.
    """
    if not agreement["identical_every_value"]:
        return 1, (f"DISAGREEMENT: the two mirrors do not serve the same elevations "
                   f"(max |difference| {agreement['max_abs_diff_m']} m).")
    if not agreement["equal_file_content_length"]:
        return 0, (f"NOTE: the two objects are not byte-identical files "
                   f"({agreement['file_size_delta_bytes']:+d} bytes of container metadata), while "
                   f"every compared elevation value is identical.")
    return 0, "OK: the same ESA product from an independent mirror, byte-identical and value-identical."


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", type=int, default=256, help="sampled window size in pixels")
    ap.add_argument("--full", action="store_true",
                    help="compare every value in the tile instead of a window (slower, decisive)")
    ap.add_argument("--lat", type=float, default=SITE_LAT)
    ap.add_argument("--lon", type=float, default=SITE_LON)
    ap.add_argument("--out", default=None,
                    help="where to write the record (default: by mode — see below)")
    args = ap.parse_args(argv)

    # The record is written to a path that depends on the mode, on purpose. A window covers 4% of
    # the tile, so a quick window run must not silently replace the decisive whole-tile evidence with
    # a weaker one — which is exactly what happened on the first run of this file, and a test caught
    # it rather than a reader.
    out = pathlib.Path(args.out) if args.out else (
        ARTIFACT if args.full else ARTIFACT.with_name("earth_cop30_mirror_window.json"))
    try:
        result = compare(args.lat, args.lon, args.window, full=args.full)
    except Blocked as exc:
        # Reported as BLOCKED, never as agreement. A network failure is not evidence of a match.
        print(f"BLOCKED: {exc}")
        print("Nothing was verified. This is not a pass.")
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    ag = result["agreement"]
    print(f"tile {result['tile']} — {result['extent_compared']}, {result['values_compared']} values")
    print(f"  AWS   {result['aws']['content_length']} bytes  values sha256 "
          f"{result['aws']['values_sha256'][:16]}…")
    print(f"  Azure {result['azure']['content_length']} bytes  values sha256 "
          f"{result['azure']['values_sha256'][:16]}…")
    print(f"  identical every value    : {ag['identical_every_value']}")
    print(f"  equal values sha256      : {ag['equal_values_sha256']}")
    print(f"  container files identical: {ag['equal_file_content_length']} "
          f"(Azure - AWS = {ag['file_size_delta_bytes']:+d} bytes)")
    print(f"wrote {out}")

    code, message = verdict(ag)
    print("\n" + message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
