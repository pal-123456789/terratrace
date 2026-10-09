"""Pre-processing masks for real DEMs.

Real elevation products carry sentinels that contaminate morphology:
Copernicus sets open water to 0 m, and many products use large negative
or specific nodata values. These masks convert such pixels to NaN *before*
reprojection and feature extraction, so flat ocean does not masquerade as
terrain. They are opt-in and blunt — prefer land-only AOIs where possible.
"""
from __future__ import annotations

import numpy as np


def apply_masks(z, mask_below=None, mask_values=None, mask_above=None):
    """Return a float copy of z with masked pixels set to NaN.

    mask_below : set values strictly below this (metres) to NaN.
    mask_above : set values strictly above this (metres) to NaN.
    mask_values: iterable of exact sentinel values to drop (np.isclose).
    """
    out = np.asarray(z, dtype="float64").copy()
    if mask_below is not None:
        out[out < mask_below] = np.nan
    if mask_above is not None:
        out[out > mask_above] = np.nan
    if mask_values:
        for v in mask_values:
            out[np.isclose(out, v, equal_nan=False)] = np.nan
    return out


def zero_fraction(z):
    """Fraction of finite pixels that are ~0 m (a water-contamination hint)."""
    v = np.asarray(z, dtype="float64")
    finite = np.isfinite(v)
    n = int(finite.sum())
    if n == 0:
        return float("nan")
    return float(np.isclose(v[finite], 0.0).sum()) / n
