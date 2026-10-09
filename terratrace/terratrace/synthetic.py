"""Synthetic terrain generators.

These generators produce deterministic elevation fields with known
analytic properties so the engine can be validated without any
challenge-specific or networked data. Using synthetic surfaces keeps the
reference engine competition-compliant (no pre-event challenge artifacts)
and fully reproducible.
"""
from __future__ import annotations

import numpy as np


def plane(shape, slope_x=0.0, slope_y=0.0, dx=1.0, dy=1.0, intercept=0.0):
    """Return an inclined plane z = slope_x*x + slope_y*y + intercept.

    slope_x / slope_y are rise-over-run gradients in elevation units per
    metre. dx / dy are pixel sizes in metres.
    """
    rows, cols = shape
    xs = np.arange(cols) * dx
    ys = np.arange(rows) * dy
    gx, gy = np.meshgrid(xs, ys)
    return slope_x * gx + slope_y * gy + intercept


def constant(shape, value=0.0):
    return np.full(shape, float(value))


def ramp_x(shape, rise_per_pixel=1.0):
    """Elevation increases by a fixed amount per column (x direction)."""
    rows, cols = shape
    row = np.arange(cols) * rise_per_pixel
    return np.tile(row, (rows, 1)).astype(float)


def gaussian_hill(shape, amplitude=10.0, sigma=3.0, dx=1.0, dy=1.0):
    rows, cols = shape
    cy, cx = (rows - 1) / 2.0, (cols - 1) / 2.0
    ys = (np.arange(rows) - cy) * dy
    xs = (np.arange(cols) - cx) * dx
    gx, gy = np.meshgrid(xs, ys)
    return amplitude * np.exp(-(gx ** 2 + gy ** 2) / (2.0 * sigma ** 2))


def rough_field(shape, amplitude=1.0, seed=0):
    """Deterministic pseudo-random roughness (seeded)."""
    rng = np.random.default_rng(seed)
    return amplitude * rng.standard_normal(shape)


def with_nodata_wedge(z, fraction=0.25, nodata=np.nan):
    """Insert a triangular nodata wedge into the top-left of the field."""
    out = z.astype(float).copy()
    rows, cols = out.shape
    for i in range(rows):
        limit = int((1.0 - i / rows) * cols * fraction * 2)
        out[i, :max(limit, 0)] = nodata
    return out
