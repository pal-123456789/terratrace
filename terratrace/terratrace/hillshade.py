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
