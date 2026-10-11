"""2-D orthonormal Haar wavelet multiscale-roughness descriptor (pure NumPy).

Decomposes an elevation grid with the orthonormal 2-D (tensor-product) Haar
discrete wavelet transform and summarises how surface-height variance (energy)
is partitioned across dyadic spatial scales -- a compact multiscale roughness
spectrum. Level 1 is the finest scale (2-pixel detail); each successive level
doubles the analysing scale.

Mallat, S. G. (1989). A theory for multiresolution signal decomposition: the
wavelet representation. IEEE Transactions on Pattern Analysis and Machine
Intelligence, 11(7), 674-693.

Method
------
NaN cells are first filled with the finite mean of the grid (0.0 if nothing is
finite) -- the module's documented nodata policy. At each level the array is
cropped to even height/width and split into non-overlapping 2x2 blocks::

    a b          a = top-left,  b = top-right
    c d          c = bottom-left, d = bottom-right

using strided even/odd row and column slices (fully vectorised -- there is no
per-block Python loop). The four ORTHONORMAL Haar coefficients of every block
are::

    A = (a + b + c + d) / 2      approximation (coarser scale, recursed on)
    H = (a - b + c - d) / 2      horizontal detail (left/right contrast)
    V = (a + b - c - d) / 2      vertical   detail (top/bottom contrast)
    D = (a - b - c + d) / 2      diagonal   detail

The 1/2 normalisation makes the 4x4 block transform orthonormal, hence
energy-preserving. The detail energy at a level is
``sum(H**2) + sum(V**2) + sum(D**2)``; the transform then recurses on ``A``
until a dimension drops below 2.

Energy (Parseval) conservation
------------------------------
Because the per-block transform is orthonormal, total energy is conserved: the
sum of every level's detail energy plus the summed square of the final
approximation equals ``sum(z_filled**2)``. This holds EXACTLY (to floating-point
precision) when every level has even dimensions, e.g. power-of-two grids such as
256x256; when a level has an odd dimension its last (odd) row or column carries
no complete 2x2 block and is cropped, so that thin border strip's energy is
excluded at that level -- the standard decimated-DWT behaviour without padding.

Note on the vertical coefficient
--------------------------------
``V`` is the standard tensor-product Haar vertical detail ``(a + b - c - d)/2``,
i.e. (top row) minus (bottom row). This form is required for an orthonormal,
energy-preserving basis: the four coefficient vectors
``{(1,1,1,1), (1,-1,1,-1), (1,1,-1,-1), (1,-1,-1,1)} / 2`` are mutually
orthogonal and unit-norm, so the block transform preserves the sum of squares.

Scientific boundary / claim firewall
-------------------------------------
These are MAP-SCALE MORPHOLOGY / roughness-spectrum descriptors of the sampled
elevation grid ONLY -- how height variance is distributed across spatial scales.
They are NOT a traversability, trafficability, hazard, slope-stability,
geologic-origin, resource, or mission-readiness claim, and say nothing about
rock-scale obstacles below the pixel scale.
"""
from __future__ import annotations

import numpy as np

__all__ = ["haar_transform", "haar_levels", "wavelet_signature"]


def _fill_nan_mean(z):
    """Return a copy of ``z`` with non-finite cells set to the finite mean
    (0.0 if nothing is finite). The documented NaN policy for the whole module."""
    z = np.array(z, dtype=float, copy=True)
    bad = ~np.isfinite(z)
    if bad.any():
        good = z[~bad]
        z[bad] = float(good.mean()) if good.size else 0.0
    return z


def haar_transform(z):
    """Full forward orthonormal 2-D Haar decomposition.

    Fills NaNs with the finite mean, then repeatedly crops to even dimensions,
    forms the orthonormal 2x2 Haar coefficients ``A, H, V, D`` (see the module
    docstring) via vectorised even/odd slices, records the per-level detail
    energy, and recurses on the approximation ``A`` until a dimension drops below
    2 (finest scale first).

    Returns
    -------
    (levels, final_approx) : ``levels`` is the finest-first list of per-level
        dicts ``{"level": int, "detail_energy": float, "n_coeffs": int}`` and
        ``final_approx`` is the residual approximation array left when no further
        2x2 split is possible. By orthonormality,
        ``sum(detail_energy) + sum(final_approx**2) == sum(z_filled**2)`` exactly
        for even-divisible (e.g. power-of-two) grids. Exposed so callers and
        tests can verify the Parseval budget and reconstruct the pyramid.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("Haar wavelet roughness needs a 2-D elevation grid")
    cur = _fill_nan_mean(z)
    levels = []
    level = 1
    while min(cur.shape) >= 2:
        nr, nc = cur.shape
        cur = cur[:nr - (nr % 2), :nc - (nc % 2)]        # crop to even H/W
        a = cur[0::2, 0::2]
        b = cur[0::2, 1::2]
        cc = cur[1::2, 0::2]
        dd = cur[1::2, 1::2]
        A = 0.5 * (a + b + cc + dd)
        H = 0.5 * (a - b + cc - dd)
        V = 0.5 * (a + b - cc - dd)
        D = 0.5 * (a - b - cc + dd)
        detail_energy = float(np.sum(H * H) + np.sum(V * V) + np.sum(D * D))
        levels.append({"level": int(level),
                       "detail_energy": detail_energy,
                       "n_coeffs": int(3 * A.size)})
        cur = A
        level += 1
    return levels, cur


def haar_levels(z):
    """Per-level detail energy of the orthonormal 2-D Haar transform.

    Returns the finest-first list of dicts
    ``[{"level": int, "detail_energy": float, "n_coeffs": int}, ...]`` -- level 1
    is the finest (2-pixel) scale, ``detail_energy`` is ``sum(H**2+V**2+D**2)`` at
    that level, and ``n_coeffs`` is the number of detail coefficients
    (``3 * n_blocks``). Thin wrapper over :func:`haar_transform`.
    """
    return haar_transform(z)[0]


def _loglog_slope(levels):
    """Least-squares slope of ``log(detail_energy)`` vs ``log(level)`` over the
    levels with finite, strictly-positive energy (``log`` must be defined);
    ``nan`` if fewer than three such usable levels. Base-independent."""
    lv = np.array([d["level"] for d in levels], dtype=float)
    en = np.array([d["detail_energy"] for d in levels], dtype=float)
    good = np.isfinite(lv) & (lv > 0.0) & np.isfinite(en) & (en > 0.0)
    lv, en = lv[good], en[good]
    if lv.size < 3:
        return float("nan")
    return float(np.polyfit(np.log(lv), np.log(en), 1)[0])


def wavelet_signature(z):
    """Compact, JSON-serialisable multiscale Haar roughness signature.

    Runs :func:`haar_transform` and returns plain Python scalars::

        {"energy_by_level": {str(level): fraction_of_total_detail_energy, ...},
         "dominant_level": int,          # level carrying the most detail energy
                                         # (0 when there is no detail energy)
         "total_detail_energy": float,   # summed detail energy over all levels
         "detail_loglog_slope": float}   # LS slope of log(detail) vs log(level);
                                         # NaN if fewer than 3 usable levels

    ``energy_by_level`` fractions sum to 1 when any detail energy exists (every
    level present carries a key; a flat/constant field yields all-zero fractions
    and ``dominant_level == 0``). Carries the module's claim firewall: map-scale
    morphology / roughness spectrum only -- not a traversability, hazard,
    geologic, or mission claim.
    """
    levels, _ = haar_transform(z)
    energies = {d["level"]: d["detail_energy"] for d in levels}
    total = float(sum(energies.values()))
    if total > 0.0:
        energy_by_level = {str(lvl): float(e / total) for lvl, e in energies.items()}
        dominant = int(max(energies, key=lambda k: energies[k]))
    else:
        energy_by_level = {str(lvl): 0.0 for lvl in energies}
        dominant = 0
    return {
        "energy_by_level": energy_by_level,
        "dominant_level": dominant,
        "total_detail_energy": total,
        "detail_loglog_slope": _loglog_slope(levels),
    }
