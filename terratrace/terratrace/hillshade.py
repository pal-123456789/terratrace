"""Shaded-relief (hillshade) rendering as a self-contained PNG data URI.

This module is a *visualisation aid only*. It produces a map-scale
shaded-relief greyscale image of an elevation grid so a terrain preview can
be embedded inline (as a base64 PNG data URI) in the self-contained HTML
report/viewer with no external assets. The shading encodes nothing beyond
illuminated surface orientation: it makes no quantitative, mechanical, or
trafficability claim about the terrain.

The PNG encoder is pure Python standard library (``zlib`` / ``struct`` /
``base64``); there is no PIL or other third-party image dependency, so the
output is fully self-contained and byte-for-byte deterministic.
"""
from __future__ import annotations

import base64
import struct
import zlib

import numpy as np

__all__ = [
    "hillshade",
    "to_png_bytes",
    "to_data_uri",
    "hillshade_data_uri",
    "form_map_png_datauri",
    "scalar_png_datauri",
]


def hillshade(z, dx=1.0, dy=1.0, azimuth_deg=315.0, altitude_deg=45.0):
    """Standard Horn shaded relief of a DEM, as a 2-D ``uint8`` image.

    Gradients are taken with :func:`numpy.gradient` using the pixel sizes
    ``dy, dx`` (rows then columns), giving ``gy = dz/dy`` and ``gx = dz/dx``.
    The surface slope and aspect are

        slope  = arctan(hypot(gx, gy))
        aspect = arctan2(gy, -gx)

    and the illumination (sun azimuth ``az`` and altitude ``alt`` in radians,
    converted from the degree arguments) gives

        shaded = sin(alt)*cos(slope) + cos(alt)*sin(slope)*cos(az - aspect)

    The result is clamped to ``[0, 1]`` and scaled to ``0..255``. NaN cells
    (nodata) render as 0 (black). The returned array has the same shape as
    ``z`` and dtype ``uint8``.
    """
    z = np.asarray(z, dtype=float)
    gy, gx = np.gradient(z, dy, dx)

    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(gy, -gx)

    az = np.radians(azimuth_deg)
    alt = np.radians(altitude_deg)

    shaded = (np.sin(alt) * np.cos(slope)
              + np.cos(alt) * np.sin(slope) * np.cos(az - aspect))

    # NaN (nodata) and any non-finite cell -> black; then clamp to [0, 1].
    shaded = np.where(np.isfinite(shaded), shaded, 0.0)
    shaded = np.clip(shaded, 0.0, 1.0)
    return np.rint(255.0 * shaded).astype(np.uint8)


def to_png_bytes(gray):
    """Encode a 2-D ``uint8`` array as a valid 8-bit greyscale PNG (stdlib).

    Builds the stream by hand: the PNG signature, an IHDR chunk (width,
    height, bit depth 8, colour type 0 greyscale, all other fields 0), a
    single IDAT chunk holding the zlib-compressed scanlines (each row
    prefixed with filter byte 0x00), and an empty IEND chunk. Every chunk is
    ``length(4) + type(4) + data + CRC32(type+data)(4)`` with big-endian
    integers, matching the PNG specification.
    """
    arr = np.ascontiguousarray(np.asarray(gray, dtype=np.uint8))
    if arr.ndim != 2:
        raise ValueError("gray must be a 2-D array")
    height, width = arr.shape

    # Filtered raw image data: one 0x00 filter byte in front of each scanline.
    raw = bytearray()
    for row in arr:
        raw.append(0)
        raw.extend(row.tobytes())
    compressed = zlib.compress(bytes(raw), 9)

    def _chunk(tag, data):
        payload = tag + data
        return (struct.pack(">I", len(data)) + payload
                + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF))

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (signature
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", compressed)
            + _chunk(b"IEND", b""))


def to_data_uri(gray):
    """Return ``gray`` as a ``data:image/png;base64,...`` URI (stdlib only)."""
    return "data:image/png;base64," + base64.b64encode(to_png_bytes(gray)).decode("ascii")


def hillshade_data_uri(z, dx=1.0, dy=1.0, azimuth_deg=315.0,
                       altitude_deg=45.0, max_size=256):
    """Hillshade ``z`` and return it as an inline PNG data URI.

    To keep the embedded image small, ``z`` is optionally downsampled by
    simple integer striding so its longest side is ``<= max_size``; the pixel
    sizes are scaled by the same stride so the shading stays faithful. The
    downsampled grid is then hillshaded and encoded as a PNG data URI.
    """
    z = np.asarray(z, dtype=float)
    rows, cols = z.shape
    longest = max(rows, cols)
    step = max(1, int(np.ceil(longest / float(max_size)))) if max_size else 1
    if step > 1:
        z = z[::step, ::step]
        dx = dx * step
        dy = dy * step
    gray = hillshade(z, dx=dx, dy=dy, azimuth_deg=azimuth_deg,
                     altitude_deg=altitude_deg)
    return to_data_uri(gray)


# ---------------------------------------------------------------------------
# Categorical / scalar-field encoders for the opt-in landform capability.
#
# These render an integer landform-code map or a float scalar field (e.g.
# topographic openness in degrees) as a self-contained PNG data URI. Like the
# hillshade above they are *visualisation aids only* and assert nothing about
# traversability, mechanics, or mission readiness. Pure stdlib + numpy.
# ---------------------------------------------------------------------------

# Qualitative palette for geomorphon form codes; index == FORM_NAMES index in
# terratrace.geomorphons (0 flat .. 9 pit). Chosen as 10 clearly distinct hues
# (a convex-up warm -> cool concave-down ramp): heights are warm, channels/pits
# are cool. Code -1 (unclassified) or any NaN entry renders mid-grey.
_FORM_COLORS = (
    (200, 200, 200),  # 0 flat      light grey
    (178, 24, 43),    # 1 peak      dark red
    (239, 101, 72),   # 2 ridge     orange-red
    (253, 174, 97),   # 3 shoulder  orange
    (254, 224, 139),  # 4 spur      pale gold
    (120, 198, 121),  # 5 slope     green
    (120, 198, 190),  # 6 hollow    teal
    (116, 169, 207),  # 7 footslope light blue
    (43, 110, 185),   # 8 valley    blue
    (40, 36, 130),    # 9 pit       indigo
)
_NODATA_RGB = (128, 128, 128)  # code -1 / NaN -> mid-grey


def _rgb_to_png_bytes(rgb):
    """Encode an ``(H, W, 3)`` uint8 array as a 24-bit truecolour PNG (stdlib).

    The byte framing is identical to :func:`to_png_bytes` -- signature, IHDR, a
    single zlib-compressed IDAT of filter-0 scanlines, empty IEND -- except the
    IHDR colour type is 2 (truecolour RGB) and each scanline carries three bytes
    per pixel. A distinct writer is needed because :func:`to_png_bytes` is 8-bit
    greyscale (colour type 0) and is deliberately left unchanged.
    """
    arr = np.ascontiguousarray(np.asarray(rgb, dtype=np.uint8))
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("rgb must be an (H, W, 3) array")
    height, width = arr.shape[:2]

    raw = bytearray()
    for row in arr:
        raw.append(0)
        raw.extend(row.tobytes())
    compressed = zlib.compress(bytes(raw), 9)

    def _chunk(tag, data):
        payload = tag + data
        return (struct.pack(">I", len(data)) + payload
                + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF))

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (signature
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", compressed)
            + _chunk(b"IEND", b""))


def form_map_png_datauri(code_map):
    """Categorical landform-code map -> ``data:image/png;base64,...`` RGB PNG.

    ``code_map`` is an integer array of geomorphon form codes where 0..9 index
    ``terratrace.geomorphons.FORM_NAMES`` (0 flat .. 9 pit) and -1 marks an
    unclassified cell. Each code 0..9 is painted its fixed qualitative colour
    from ``_FORM_COLORS``; -1 (or any out-of-range code, or a NaN entry in a
    float array) is rendered mid-grey ``(128, 128, 128)``. Visualisation only.
    """
    codes = np.asarray(code_map)
    finite = (np.isfinite(codes) if codes.dtype.kind == "f"
              else np.ones(codes.shape, dtype=bool))
    idx = np.where(finite, codes, -1).astype(np.int64)
    if idx.ndim != 2:
        raise ValueError("code_map must be a 2-D array")

    rgb = np.empty((idx.shape[0], idx.shape[1], 3), dtype=np.uint8)
    rgb[...] = _NODATA_RGB
    for code, colour in enumerate(_FORM_COLORS):
        rgb[idx == code] = colour
    return ("data:image/png;base64,"
            + base64.b64encode(_rgb_to_png_bytes(rgb)).decode("ascii"))


def scalar_png_datauri(arr, vmin=None, vmax=None):
    """Float scalar field -> greyscale ``data:image/png;base64,...`` PNG.

    The field (e.g. positive openness in degrees) is linearly stretched from
    ``vmin..vmax`` onto ``0..255``; a ``None`` bound is filled from the NaN-aware
    2nd / 98th percentile of the finite data (a robust stretch). NaN (nodata)
    cells render mid-grey (128). A degenerate range falls back to a span of 1.
    Reuses the module's greyscale PNG writer via :func:`to_data_uri`
    unchanged. Visualisation only.
    """
    a = np.asarray(arr, dtype=float)
    if a.ndim != 2:
        raise ValueError("arr must be a 2-D array")
    finite = np.isfinite(a)
    if vmin is None or vmax is None:
        if finite.any():
            lo, hi = np.percentile(a[finite], [2.0, 98.0])
        else:
            lo, hi = 0.0, 1.0
        vmin = lo if vmin is None else vmin
        vmax = hi if vmax is None else vmax
    span = float(vmax) - float(vmin)
    if not np.isfinite(span) or span <= 0.0:
        span = 1.0
    scaled = np.clip((a - float(vmin)) / span, 0.0, 1.0)
    gray = np.where(finite, np.rint(255.0 * scaled), 128.0).astype(np.uint8)
    return to_data_uri(gray)
