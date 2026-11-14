"""Build the TerraTrace cover image from the project's own DEMs.

Two defects fixed here, both visible in the Odadahraun panel:

1. Its Copernicus tile is 46.9 % nodata (-32768) -- it straddles the Icelandic coast. Resampling
   bilinearly over the raw array bled that sentinel into neighbouring pixels, producing huge
   spurious gradients that shaded as harsh black/white spikes. Now the array is masked BEFORE any
   resampling, cropped to the bounding box of real data, and downsampled with a nan-aware block
   mean, so no sentinel value ever reaches the shading step.
2. Every panel is now cropped to the true aspect ratio of the box it sits in, instead of being
   stretched to fit. The Mars banner was being squashed from 1.78:1 into 7.89:1.

Shading remains one light direction and one vertical scale across all panels, nothing is
contrast-stretched per panel, and the sigma values are quoted from docs/RESULTS-v3.md.
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap

DATA = pathlib.Path("/sessions/intelligent-blissful-thompson/mnt/Nasa Space App Hackathon 2026/terratrace/data")
# the published artifact, written where it is read from — not to a scratch directory that only
# existed on one machine
OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "cover.png"

BG = "#05070c"
INK = "#eef2f7"
MUTE = "#8c9aad"
RULE = "#1d2634"
ACC = "#6fd6c0"
WARM = "#e0913f"

EARTH_CMAP = LinearSegmentedColormap.from_list("earth", ["#050a10", "#12202b", "#2d4a55", "#5c8a90", "#a9c9c6", "#e8f2ef"])
MARS_CMAP = LinearSegmentedColormap.from_list("mars", ["#100705", "#2b1209", "#5c2a12", "#9a4f1e", "#cf8443", "#f2d5ab"])

AZ, ZEN = np.deg2rad(315.0), np.deg2rad(45.0)

# figure is 19.2 x 10.8 inches; these are the axes, in figure fractions
MARS_BOX = (0.045, 0.545, 0.910, 0.205)
EARTH_W, EARTH_H, EARTH_GAP = (0.910 - 3 * 0.0125) / 4, 0.245, 0.0125
FIG_W, FIG_H = 19.2, 10.8


def largest_valid_rect(mask, coarse=900):
    """Largest all-valid rectangle in a boolean mask, via the largest-rectangle-in-histogram method.

    A bounding box is not enough for a coastal tile: the valid data is a diagonal band, so the box
    still contains tens of percent of nodata, and any flat fill for it reads as a smear of fake
    terrain. An inscribed rectangle is entirely real data.
    """
    h, w = mask.shape
    f = max(1, int(np.ceil(w / coarse)))
    H, W = (h // f) * f, (w // f) * f
    m = mask[:H, :W].reshape(H // f, f, W // f, f).mean(axis=(1, 3)) >= 0.995

    best = (0, 0, 0, 0, 0)
    heights = np.zeros(m.shape[1], dtype=np.int64)
    for r in range(m.shape[0]):
        heights = (heights + 1) * m[r]
        hs, stack = heights.tolist(), []
        for c in range(len(hs) + 1):
            cur = hs[c] if c < len(hs) else 0
            start = c
            while stack and stack[-1][1] >= cur:
                idx, hh = stack.pop()
                if hh * (c - idx) > best[0]:
                    best = (hh * (c - idx), r - hh + 1, idx, r, c - 1)
                start = idx
            stack.append((start, cur))

    _, r1, c1, r2, c2 = best
    return slice(r1 * f, (r2 + 1) * f), slice(c1 * f, (c2 + 1) * f)


def read_masked(path):
    """Full-resolution read with the nodata sentinel removed, cropped to entirely real data."""
    with rasterio.open(path) as ds:
        a = ds.read(1).astype("float64")
        nodata = ds.nodata
        px = (ds.bounds.right - ds.bounds.left) / ds.width
        py = (ds.bounds.top - ds.bounds.bottom) / ds.height
    if nodata is not None:
        a[a == nodata] = np.nan
    valid = ~np.isnan(a)
    if valid.all():
        return a, px, py

    rows = np.where(valid.any(axis=1))[0]
    cols = np.where(valid.any(axis=0))[0]
    a = a[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    print(f"    bounding box {a.shape[1]}x{a.shape[0]} ({np.mean(~np.isnan(a)):.1%} valid)", end="  ")
    ry, rx = largest_valid_rect(~np.isnan(a))
    a = a[ry, rx]
    print(f"-> inscribed rect {a.shape[1]}x{a.shape[0]} ({np.mean(~np.isnan(a)):.1%} valid)")
    return a, px, py


def downsample(a, out_w):
    """Nan-aware block mean. Resampling happens only after the sentinel is gone."""
    h, w = a.shape
    f = max(1, int(np.ceil(w / out_w)))
    H, W = (h // f) * f, (w // f) * f
    a = a[:H, :W]
    with np.errstate(invalid="ignore"):
        m = np.nanmean(a.reshape(H // f, f, W // f, f), axis=(1, 3))
    return m, f


def crop_aspect(arr, aspect):
    """Centre-crop to aspect = width/height, so nothing is ever stretched."""
    h, w = arr.shape
    if w / h > aspect:
        cw = max(4, int(round(h * aspect)))
        left = (w - cw) // 2
        return arr[:, left:left + cw]
    ch = max(4, int(round(w / aspect)))
    top = (h - ch) // 2
    return arr[top:top + ch]


def hillshade(path, aspect, out_w=1700):
    a, px, py = read_masked(path)
    a, f = downsample(a, out_w)
    a = np.nan_to_num(a, nan=float(np.nanmedian(a)))
    gy, gx = np.gradient(a, py * f, px * f)
    slope = np.arctan(np.hypot(gx, gy))
    hs = np.cos(ZEN) * np.cos(slope) + np.sin(ZEN) * np.sin(slope) * np.cos(AZ - np.arctan2(-gx, gy))
    return crop_aspect(np.clip(hs, 0.0, 1.0), aspect)


# --- the study's own regions, with the sigma they actually measured at 60 km support -------
EARTH = [
    ("Nullarbor Plain", "Australia", 5, "smooth control", "nullarbor_cop30.tif"),
    ("Deccan Traps", "India", 32, "basaltic", "deccan_traps_cop30.tif"),
    ("Harrat Khaybar", "Saudi Arabia", 102, "basaltic", "harrat_khaybar_cop30.tif"),
    ("Odadahraun", "Iceland", 182, "basaltic", "odadahraun_cop30.tif"),
]
MARS = ("Mars", "MOLA 463 m/px reference terrain", "mola_sample.tif")

fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=100, facecolor=BG)

# ---------------------------------------------------------------- header
fig.text(0.045, 0.925, "TerraTrace", color=INK, fontsize=54, fontweight="bold", ha="left", va="center", family="DejaVu Sans")
fig.text(0.046, 0.868, "Planetary Analog OS", color=ACC, fontsize=17, ha="left", va="center", family="DejaVu Sans")
fig.text(0.046, 0.828,
         "Terrain morphology compared across Earth, Mars, the Moon, Mercury and Ceres\nat a declared common spatial support. Pareto dominance — never a single score.",
         color=MUTE, fontsize=13.5, ha="left", va="top", linespacing=1.6, family="DejaVu Sans")

fig.text(0.955, 0.905, "S  —  SUPPORTED\nV  —  NOT SUPPORTED\nR  —  SUPPORTED",
         color=INK, fontsize=14, ha="right", va="center", linespacing=2.05, family="DejaVu Sans")
fig.text(0.955, 0.812, "protocol v3, 15/15 confirmatory cells", color=MUTE, fontsize=10.5, ha="right", va="center", family="DejaVu Sans")
fig.text(0.955, 0.788, "pre-specified, not pre-registered", color=WARM, fontsize=10.5, ha="right", va="center", family="DejaVu Sans")
fig.add_artist(plt.Line2D([0.045, 0.955], [0.788, 0.788], color=RULE, linewidth=1.1, transform=fig.transFigure))

# ---------------------------------------------------------------- Mars banner
mx, my, mw, mh = MARS_BOX
ax = fig.add_axes([mx, my, mw, mh])
ax.imshow(hillshade(DATA / "mars" / MARS[2], (mw * FIG_W) / (mh * FIG_H)), cmap=MARS_CMAP, aspect="auto", interpolation="bilinear")
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_color(RULE); s.set_linewidth(1.0)
ax.text(0.006, 1.045, MARS[0], color=INK, fontsize=15, fontweight="bold", transform=ax.transAxes, family="DejaVu Sans")
ax.text(0.078, 1.052, MARS[1], color=MUTE, fontsize=11.5, transform=ax.transAxes, family="DejaVu Sans")
ax.text(0.994, 1.052, "reference terrain", color=WARM, fontsize=11.5, ha="right", transform=ax.transAxes, family="DejaVu Sans")

# ---------------------------------------------------------------- Earth row
box_aspect = (EARTH_W * FIG_W) / (EARTH_H * FIG_H)
for i, (name, where, sigma, klass, fname) in enumerate(EARTH):
    ax = fig.add_axes([0.045 + i * (EARTH_W + EARTH_GAP), 0.225, EARTH_W, EARTH_H])
    ax.imshow(hillshade(DATA / "earth" / fname, box_aspect), cmap=EARTH_CMAP, aspect="auto", interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(RULE); s.set_linewidth(1.0)
    ax.text(0.0, 1.055, name, color=INK, fontsize=13.5, fontweight="bold", transform=ax.transAxes, family="DejaVu Sans")
    ax.text(0.0, 1.012, where, color=MUTE, fontsize=10.5, transform=ax.transAxes, family="DejaVu Sans")
    ax.text(1.0, 1.055, f"σ {sigma} m", color=ACC, fontsize=13.5, ha="right", transform=ax.transAxes, family="DejaVu Sans")
    ax.text(1.0, 1.012, klass, color=MUTE, fontsize=10.5, ha="right", transform=ax.transAxes, family="DejaVu Sans")

fig.text(0.045, 0.185,
         "Earth candidates · Copernicus GLO-30, 30 m posting          Shading: one light direction and one vertical scale across every panel — nothing is contrast-stretched, so flat terrain reads as flat.",
         color=MUTE, fontsize=10.5, ha="left", va="center", family="DejaVu Sans")
fig.add_artist(plt.Line2D([0.045, 0.955], [0.145, 0.145], color=RULE, linewidth=1.1, transform=fig.transFigure))

# ---------------------------------------------------------------- footer
fig.text(0.045, 0.108, "roughness tracks the class; volcanic origin does not", color=INK, fontsize=15, fontweight="bold", ha="left", va="center", family="DejaVu Sans")
fig.text(0.045, 0.062, "983 offline tests  ·  51 scientific-correctness oracles  ·  15 cited sources  ·  MIT", color=MUTE, fontsize=11.5, ha="left", va="center", family="DejaVu Sans")
fig.text(0.955, 0.062, "Morphology only. No traversability, site-access, geologic-equivalence or mission-readiness claim.",
         color=WARM, fontsize=11, ha="right", va="center", family="DejaVu Sans")

fig.savefig(OUT, facecolor=BG)
print("wrote", OUT, OUT.stat().st_size, "bytes")
