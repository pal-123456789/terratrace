"""Gliding-box lacunarity of a terrain grid (Plotnick, Gardner & O'Neill 1993).

Plotnick, R.E., Gardner, R.H. & O'Neill, R.V. (1993). Lacunarity indices as
measures of landscape texture. Landscape Ecology 8(3), 201-211.

Lacunarity measures the "gappiness" or clustering of a field: how much the mass
contained in a sliding window of fixed size varies from place to place. A
spatially uniform surface carries nearly the same mass in every window (low
lacunarity); a clumped/gappy surface has windows that are sometimes full and
sometimes nearly empty (high lacunarity). Lacunarity complements fractal
dimension -- two surfaces can share a dimension yet differ in texture.

Method (grayscale gliding box)
------------------------------
Non-finite cells are first filled with the finite mean of the grid (0.0 if
nothing is finite). The grid is then put on a non-negative "mass" footing

    m = z_filled - min(z_filled)        # m >= 0

so a box *mass* sum is a meaningful non-negative quantity (Plotnick et al.'s
grayscale generalisation of the original binary box-counting). An r x r box is
slid over EVERY position with unit step (the "gliding box"); let S be the box
mass sum at each position. The lacunarity at box size r is the normalised second
moment of the box-mass distribution

    Lambda(r) = mean(S^2) / mean(S)^2  =  1 + Var(S) / mean(S)^2.

Hence Lambda(r) >= 1 always; Lambda(r) == 1 for a perfectly uniform field (every
box carries equal mass, Var(S) = 0) and grows as the field becomes more
clustered/gappy. Lambda typically DECREASES toward 1 as r grows, because larger
windows average over the clustering. A relief-free (all-equal) grid has m == 0
everywhere, so every box sum is 0 and Lambda == 1 exactly at every r.

The box sums are computed for all positions at once from a summed-area table
(integral image): P is the zero-padded 2-D cumulative sum of m, and every r x r
box sum is the four-corner combination
``P[i+r, j+r] - P[i, j+r] - P[i+r, j] + P[i, j]`` evaluated as whole-array
slices. There is NO per-position Python loop, so a 256x256 grid is handled in a
few milliseconds. Pure NumPy, NaN-safe, deterministic -- no SciPy, no network.

Scientific boundary / claim firewall
-------------------------------------
Lacunarity here is a MAP-SCALE MORPHOLOGY / texture descriptor of the sampled
elevation grid ONLY -- how box-summed surface mass is distributed in space. It is
NOT a traversability, trafficability, hazard, slope-stability, geologic-origin,
resource, or mission-readiness claim, and says nothing about rock-scale
obstacles below the pixel scale.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "gliding_box_lacunarity",
    "lacunarity_curve",
    "lacunarity_signature",
]


def _mass_field(field):
    """Return the non-negative 2-D ``mass`` grid ``m = z - min(z)``.

    Non-finite cells are filled with the finite mean of ``field`` (0.0 if nothing
    is finite) -- the module's documented nodata policy -- before the minimum is
    subtracted, so ``m >= 0`` everywhere and ``m`` is all-finite. Raises
    ``ValueError`` for a non-2-D input.
    """
    z = np.array(field, dtype=float, copy=True)
    if z.ndim != 2:
        raise ValueError("gliding-box lacunarity needs a 2-D elevation grid")
    bad = ~np.isfinite(z)
    if bad.any():
        good = z[~bad]
        z[bad] = float(good.mean()) if good.size else 0.0
    return z - float(z.min())


def gliding_box_lacunarity(field, r):
    """Gliding-box lacunarity ``Lambda(r)`` of a 2-D field (Plotnick et al. 1993).

    Fills non-finite cells with the finite mean, forms the non-negative mass grid
    ``m = z - min(z)``, slides an ``r x r`` box over EVERY position (unit step),
    and returns ``Lambda(r) = mean(S^2)/mean(S)^2 = 1 + Var(S)/mean(S)^2`` for the
    box-mass sums ``S``. The box sums come from a summed-area table (no
    per-position loop).

    ``r`` is the integer box side, clamped to ``[1, min(H, W)]`` so an over-large
    request never raises (a box bigger than the grid is capped to the grid). The
    return is a plain ``float`` that is always ``>= 1.0``; it is exactly ``1.0``
    for a relief-free grid (zero mass everywhere) or whenever every box carries
    equal mass (``Var(S) == 0``).
    """
    m = _mass_field(field)
    h, w = m.shape
    r = max(1, min(int(r), h, w))
    # Zero-padded integral image: P[i, j] = sum of m[:i, :j], shape (h+1, w+1).
    P = np.zeros((h + 1, w + 1), dtype=float)
    P[1:, 1:] = np.cumsum(np.cumsum(m, axis=0), axis=1)
    # Every r x r box sum via the four-corner rule, all positions at once.
    S = P[r:, r:] - P[:-r, r:] - P[r:, :-r] + P[:-r, :-r]
    mean_s = float(S.mean())
    if mean_s <= 0.0:                       # zero-mass (relief-free) grid
        return 1.0
    var_s = float(S.var())                  # population variance (ddof=0)
    return 1.0 + var_s / (mean_s * mean_s)


def lacunarity_curve(z, boxes=(2, 4, 8, 16)):
    """Lacunarity ``Lambda(r)`` at several box sizes (Plotnick et al. 1993).

    Returns ``{int(r): float Lambda(r)}`` for the requested ``boxes``. Each box
    size is clipped to the grid: sizes below 1 are dropped and any size larger
    than ``min(H, W)`` is capped to ``min(H, W)``; the keys are the resulting
    sorted unique sizes (so on a grid at least as large as ``max(boxes)`` the keys
    are exactly ``boxes``). An empty grid returns ``{}``. Deterministic, NaN-safe.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("gliding-box lacunarity needs a 2-D elevation grid")
    mx = int(min(z.shape))
    if mx < 1:
        return {}
    sizes = sorted({min(int(r), mx) for r in boxes if int(r) >= 1})
    return {int(r): gliding_box_lacunarity(z, r) for r in sizes}


def _loglog_slope(curve):
    """LS slope of ``log(Lambda)`` vs ``log(r)`` over the curve's points.

    Uses only points with finite ``r > 0`` and finite ``Lambda > 0`` (the log must
    be defined; ``Lambda >= 1`` always qualifies). Returns ``nan`` if fewer than
    three usable points. Base-independent. A uniform field (all ``Lambda == 1``)
    gives ``log Lambda == 0`` at every r, hence slope ``0.0``.
    """
    rs = np.array(sorted(curve), dtype=float)
    lam = np.array([curve[int(r)] for r in rs], dtype=float)
    good = np.isfinite(rs) & (rs > 0.0) & np.isfinite(lam) & (lam > 0.0)
    rs, lam = rs[good], lam[good]
    if rs.size < 3:
        return float("nan")
    return float(np.polyfit(np.log(rs), np.log(lam), 1)[0])

def lacunarity_signature(z):
    """Compact, JSON-serialisable lacunarity signature of ``z`` (Plotnick 1993).

    Reduces the default lacunarity curve (box sizes 2, 4, 8, 16, clipped to the
    grid) to plain Python floats::

        {"lacunarity_r2":           float,  # Lambda at r = 2 (NaN if r=2 unfit)
         "lacunarity_mean":         float,  # mean Lambda over the curve
         "lacunarity_loglog_slope": float}  # LS slope of log Lambda vs log r;
                                            # NaN if fewer than 3 curve points

    Lacunarity usually falls with box size, so the slope is typically <= 0 (0 for
    a uniform field, where every Lambda == 1). Deterministic. Carries the module's
    claim firewall: map-scale texture morphology only -- not a traversability,
    hazard, geologic, or mission claim.
    """
    curve = lacunarity_curve(z)
    if curve:
        mean_lam = float(np.mean([curve[k] for k in curve]))
    else:
        mean_lam = float("nan")
    return {
        "lacunarity_r2": float(curve.get(2, float("nan"))),
        "lacunarity_mean": mean_lam,
        "lacunarity_loglog_slope": _loglog_slope(curve),
    }
