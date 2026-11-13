"""Resumable chunked downloader for the Goddard PGDA 5 m/pixel LOLA products.

These are ~41 MB single-band GeoTIFFs served over a slow link, which is enough to time out a
naive one-shot fetch. Each run appends a bounded number of bytes using an HTTP Range request, so
an interrupted transfer is resumed rather than restarted, and the completed file is verified by
SHA-256. Run it as many times as it takes.

The SHA-256 of the product used for the exploratory lunar result is recorded in
`docs/LUNAR-DEMONSTRATION.md`, so the file itself is not committed (see `.gitignore`).

Usage:
    python scripts/fetch_lola.py "Site01/Site01_final_adj_5mpp_surf.tif" data/moon/Site01_surf.tif
"""
import hashlib
import pathlib
import sys
import time
import urllib.request

BASE = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/"


def fetch(src, dst, budget_s=120.0, chunk=1 << 20):
    dst = pathlib.Path(dst)
    url = BASE + src
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=45) as r:
        total = int(r.headers["Content-Length"])

    have = dst.stat().st_size if dst.exists() else 0
    if have >= total:
        h = hashlib.sha256(dst.read_bytes()).hexdigest()
        print(f"  COMPLETE {dst.name}  {total/1e6:.1f} MB  sha256 {h}")
        return True

    t0 = time.time()
    with open(dst, "ab") as fh:
        while have < total and time.time() - t0 < budget_s:
            end = min(have + chunk, total) - 1
            rq = urllib.request.Request(url, headers={"Range": f"bytes={have}-{end}"})
            with urllib.request.urlopen(rq, timeout=60) as r:
                data = r.read()
            if not data:
                break
            fh.write(data)
            have += len(data)
        fh.flush()

    pct = 100.0 * have / total
    print(f"  {dst.name}: {have/1e6:.1f}/{total/1e6:.1f} MB ({pct:.0f}%) "
          f"in {time.time()-t0:.0f}s")
    if have >= total:
        print(f"  COMPLETE sha256 {hashlib.sha256(pathlib.Path(dst).read_bytes()).hexdigest()}")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__.strip().split("Usage:")[1].strip())
        raise SystemExit(2)
    src, dst = sys.argv[1], sys.argv[2]
    pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    ok = fetch(src, dst)
    raise SystemExit(0 if ok else 3)
