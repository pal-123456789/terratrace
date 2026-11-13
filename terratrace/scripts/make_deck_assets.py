"""Regenerate the slide-deck terrain panels from the project's OWN DEMs.

The deck's imagery must be the project's real data, and it must be rebuildable by anyone holding
the repository rather than by whoever happened to have a scratch directory. Before this script the
deck generator pointed at `/tmp/deck_assets`, so a clone could not rebuild the deck at all — the
panels existed only on one machine.

Outputs (into `assets/deck/`, which is git-ignored because they are large rasters rendered as PNG;
this script is the reproducible path to them):

    earth_strip.png   a wide strip of Earth candidates, one light direction throughout
    khaybar.png       Harrat Khaybar, square, for the question slide
    mars_panel.png    a Mars MOLA reference window

Every panel is hillshaded with ONE light direction and ONE vertical scale and is never
contrast-stretched, so flat terrain reads as flat and panels stay comparable to each other. That
matters here: the project's whole subject is whether two surfaces are alike, so a per-panel
autostretch would manufacture the resemblance the deck is claiming to measure.

Usage:
    python scripts/make_deck_assets.py            # writes assets/deck/
    python scripts/make_deck_assets.py --out DIR
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt      # noqa: E402
import numpy as np                   # noqa: E402
import rasterio                      # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LightSource   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent      # .../terratrace
REPO = ROOT.parent
DATA = ROOT / "data"
DEFAULT_OUT = REPO / "assets" / "deck"

BG = "#08090c"
EARTH_CMAP = LinearSegmentedColormap.from_list(
    "earth", ["#04121c", "#0b2b3d", "#155e6b", "#3f9a7e", "#93c98a", "#e6e2b8"])
MARS_CMAP = LinearSegmentedColormap.from_list(
    "mars", ["#140a06", "#3d1a0d", "#7a3418", "#b96b30", "#e0a464", "#f3dcb4"])

# the strip, left to right; each is a real candidate window already in the repository
STRIP = ["nullarbor_cop30.tif", "llano_estacado_cop30.tif", "snake_river_plain_cop30.tif",
         "deccan_traps_cop30.tif", "harrat_khaybar_cop30.tif", "odadahraun_cop30.tif",
         "nevada_basin_cop30.tif"]


# --------------------------------------------------------------------- helpers

def largest_valid_rect(mask, coarse=900):
    """Largest all-True axis-aligned rectangle, via largest-rectangle-in-histogram.

    A nodata border is what made the earlier cover panel show black wedges: a plain bbox crop still
    contains nodata when the tile is rotated or clipped. Taking the inscribed valid rectangle means
    every published pixel is real data.
    """
    h, w = mask.shape
    sy, sx = max(h // coarse, 1), max(w // coarse, 1)
    small = mask[: h // sy * sy, : w // sx * sx].reshape(h // sy, sy, w // sx, sx).all(axis=(1, 3))
    heights = np.zeros(small.shape[1], dtype=int)
    best = (0, 0, 0, 0)      # area, x0, y0, x1, y1
    for r in range(small.shape[0]):
        heights = np.where(small[r], heights + 1, 0)
        stack = []
        for c in range(small.shape[1] + 1):
            cur = heights[c] if c < small.shape[1] else 0
            start = c
            while stack and stack[-1][1] >= cur:
                sc, sh = stack.pop()
                area = sh * (c - sc)
                if area > best[0]:
                    best = (area, sc, r - sh + 1, c, r + 1)
                start = sc
            stack.append((start, cur))
    _area, c0, r0, c1, r1 = best
    # lift the coarse rectangle back to full resolution
    return r0 * sy, c0 * sx, r1 * sy, c1 * sx


def read_masked(path, max_px=3000):
    """Read a masked array, taking a bounded centre window from a large raster.

    The global MOLA product in `data/mars/` is 2.1 GB. Reading it whole is the exact mistake this
    project tells everyone else to avoid ("window the global raster, never load it"), and the first
    version of this script made it: the run stalled on the Mars panel and produced nothing. A deck
    panel needs a few thousand pixels, so only a window is ever read.
    """
    with rasterio.open(path) as ds:
        h, w = ds.height, ds.width
        if max(h, w) > max_px:
            n = min(max_px, h, w)
            r0, c0 = (h - n) // 2, (w - n) // 2
            win = rasterio.windows.Window(c0, r0, n, n)
            z = ds.read(1, window=win).astype("float64")
            nodata = ds.nodata
        else:
            z = ds.read(1).astype("float64")
            nodata = ds.nodata
        if nodata is not None:
            z = np.where(z == nodata, np.nan, z)
        return z


def crop_valid(path):
    z = read_masked(path)
    r0, c0, r1, c1 = largest_valid_rect(np.isfinite(z))
    return z[r0:r1, c0:c1]


def downsample(a, out_w):
    """Nan-aware block mean down to `out_w` columns (avoids -32768 bleed from nodata)."""
    h, w = a.shape
    fy = max(int(round(h / (out_w * a.shape[0] / w))), 1) if w else 1
    fx = max(int(round(w / out_w)), 1)
    hh, ww = h // fy * fy, w // fx * fx
    blocks = a[:hh, :ww].reshape(hh // fy, fy, ww // fx, fx)
    with np.errstate(invalid="ignore"):
        return np.nanmean(blocks, axis=(1, 3))


def crop_aspect(arr, aspect):
    """Centre-crop to a target width/height ratio."""
    h, w = arr.shape
    if w / h > aspect:
        nw = int(round(h * aspect))
        c0 = (w - nw) // 2
        return arr[:, c0:c0 + nw]
    nh = int(round(w / aspect))
    r0 = (h - nh) // 2
    return arr[r0:r0 + nh, :]


def shade(z, cmap, out_w=1600):
    z = downsample(z, min(out_w, z.shape[1]))
    ls = LightSource(azdeg=315, altdeg=40)
    return ls.shade(z, cmap=cmap, vert_exag=1.0, dx=1.0, dy=1.0, blend_mode="soft")


def save(fig, out, path):
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    print(f"  wrote {path}  {path.stat().st_size/1e6:.2f} MB")


def imshow_axes(fig, box, rgb):
    ax = fig.add_axes(box)
    ax.imshow(rgb, aspect="auto", interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#1c2534"); s.set_linewidth(1.0)
    return ax


# ----------------------------------------------------------------------- panels

def make_earth_strip(out, aspect, dpi=150):
    fig = plt.figure(figsize=(aspect * 2.2, 2.2), dpi=dpi, facecolor=BG)
    n = len(STRIP)
    gap = 0.004
    each = (1.0 - gap * (n + 1)) / n
    for i, name in enumerate(STRIP):
        path = DATA / "earth" / name
        if not path.exists():
            print(f"  SKIP {name}: not present")
            continue
        panel = crop_aspect(crop_valid(path), (each * fig.get_size_inches()[0])
                            / fig.get_size_inches()[1])
        imshow_axes(fig, [gap + i * (each + gap), 0.0, each, 1.0], shade(panel, EARTH_CMAP, 900))
    save(fig, out, out / "earth_strip.png")


def make_single(src, out_name, out, aspect, cmap, dpi=150, px=4.2):
    path = DATA / "earth" / src if src.endswith("cop30.tif") else DATA / "mars" / src
    if not path.exists():
        print(f"  SKIP {src}: not present at {path}")
        return
    fig = plt.figure(figsize=(px, px / aspect), dpi=dpi, facecolor=BG)
    panel = crop_aspect(crop_valid(path), aspect)
    imshow_axes(fig, [0, 0, 1, 1], shade(panel, cmap, 1400))
    save(fig, out, out / out_name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)

    print(f"deck assets -> {out}")
    make_earth_strip(out, aspect=8.42 / 1.86)
    make_single("harrat_khaybar_cop30.tif", "khaybar.png", out, aspect=1.0, cmap=EARTH_CMAP)
    # mola_sample.tif, not the 2.1 GB global grid: the deck's Mars panel is a reference window,
    # and `read_masked` would window the global raster too, but there is no reason to touch it.
    make_single("mola_sample.tif", "mars_panel.png", out, aspect=3.3 / 2.05, cmap=MARS_CMAP)
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
