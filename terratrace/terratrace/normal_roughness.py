"""Surface roughness from the dispersion of surface-normal vectors (the
*vector strength* of the unit normals), after Hobson (1972) and McKean &
Roering (2004).

Hobson, R. D. (1972). Surface roughness in topography: quantitative approach.
In R. J. Chorley (Ed.), Spatial Analysis in Geomorphology (pp. 221-245).
Methuen, London.

McKean, J., & Roering, J. (2004). Objective landslide detection and surface
morphology mapping using high-resolution airborne laser altimetry.
Geomorphology, 57(3-4), 331-351.

Each grid cell carries a unit surface normal
``n = (-dz/dx, -dz/dy, 1) / |(-dz/dx, -dz/dy, 1)|`` with ``dz/dx`` and ``dz/dy``
from ``np.gradient`` at spacing ``dx``. In a square moving window the
*resultant vector strength* is the magnitude of the mean normal,
``R = |(mean nx, mean ny, mean nz)|`` in ``[0, 1]``: ``R = 1`` when every
normal in the window is parallel (a locally planar patch, however steep) and
``R < 1`` as the normals disperse in direction. Hobson's roughness is
``1 - R`` in ``[0, 1]`` -- ``0`` for a perfectly planar window, larger as the
surface becomes rougher. Because it measures the SPREAD of orientations rather
than the mean slope, it is -- unlike a slope statistic -- decoupled from a
uniform regional tilt: a steep but perfectly smooth inclined plane scores
``0``.

The per-component window means are formed with a box filter built on a
summed-area table (cumulative sums), not a per-cell Python loop, so a 256x256
grid is well under a second. Windows are CLIPPED at the grid border (only cells
that exist contribute) and the measure is NaN-safe: a cell whose normal is
undefined (a NaN elevation, or a cell adjacent to one after the gradient) is
dropped from the window mean, and a window containing no valid cell is ``nan``.

Units: ``dx`` is the (isotropic) grid spacing in metres; the roughness is a
dimensionless vector-strength deficit in ``[0, 1]``. Pure NumPy, vectorised,
deterministic -- no SciPy, no network.

Scientific boundary / claim firewall: this is a map-scale *morphology /
roughness* descriptor of the sampled elevation grid only. It is NOT a
traversability, trafficability, hazard, slope-stability, geologic-origin, or
mission-readiness claim, and nothing here estimates rover behaviour or
rock-scale obstacles.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "surface_normals",
    "normal_roughness",
    "normal_roughness_signature",
]


def _box_sum(a, window):
    """Clipped moving-window sum via a summed-area table (SAT); no per-cell loop.

    For every cell returns the sum of ``a`` over the square window of odd side
    ``window`` centred on it, CLIPPED to the grid at the borders so only cells
    that exist contribute. ``a`` must be finite -- put ``0`` where a cell must
    not count. Output has the same shape as ``a``.
    """
    a = np.asarray(a, dtype=float)
    rows, cols = a.shape
    r = window // 2
    integ = np.zeros((rows + 1, cols + 1), dtype=float)
    integ[1:, 1:] = np.cumsum(np.cumsum(a, axis=0), axis=1)
    i = np.arange(rows)
    j = np.arange(cols)
    i0 = np.clip(i - r, 0, rows)[:, None]
    i1 = np.clip(i + r + 1, 0, rows)[:, None]
    j0 = np.clip(j - r, 0, cols)[None, :]
    j1 = np.clip(j + r + 1, 0, cols)[None, :]
    return integ[i1, j1] - integ[i0, j1] - integ[i1, j0] + integ[i0, j0]


def surface_normals(z, dx=1.0):
    """Unit surface-normal component arrays ``(nx, ny, nz)`` of elevation ``z``.

    With gradients ``dz/dx`` and ``dz/dy`` from :func:`numpy.gradient` at spacing
    ``dx`` (metres, isotropic), the un-normalised normal is
    ``(-dz/dx, -dz/dy, 1)`` and each component is divided by its length, so
    ``nx**2 + ny**2 + nz**2 == 1`` on every finite cell and ``nz > 0`` (the
    normal points up). ``nx``, ``ny``, ``nz`` are float64 arrays shaped like
    ``z``. NaN-safe: where ``z`` is NaN (or a cell is adjacent to one, so its
    gradient is undefined) all three components are ``nan``.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    dx = float(dx)
    if not np.isfinite(dx) or dx <= 0.0:
        raise ValueError("dx must be a positive, finite grid spacing in metres")
    gy, gx = np.gradient(z, dx, dx)
    with np.errstate(invalid="ignore", divide="ignore"):
        norm = np.sqrt(gx * gx + gy * gy + 1.0)
        nx = -gx / norm
        ny = -gy / norm
        nz = 1.0 / norm
    return nx, ny, nz


def normal_roughness(z, dx=1.0, window=5):
    """Per-cell surface-normal roughness ``1 - R`` in ``[0, 1]`` (Hobson 1972).

    Builds the unit normals with :func:`surface_normals`, then over the square
    moving window of odd side ``window`` forms the resultant vector strength
    ``R = |(mean nx, mean ny, mean nz)|`` (component means via a summed-area box
    filter, windows clipped at the border) and returns ``1 - R``: ``0`` on a
    perfectly planar window, rising toward ``1`` as the normals disperse. The
    result is a float64 array shaped like ``z`` in ``[0, 1]``. NaN-safe: invalid
    cells are dropped from each window mean, and a window with no valid cell is
    ``nan``. ``window`` must be a positive odd integer.
    """
    w = int(window)
    if w != window or w < 1 or w % 2 == 0:
        raise ValueError("window must be a positive odd integer")
    nx, ny, nz = surface_normals(z, dx)
    valid = np.isfinite(nx) & np.isfinite(ny) & np.isfinite(nz)
    sx = _box_sum(np.where(valid, nx, 0.0), w)
    sy = _box_sum(np.where(valid, ny, 0.0), w)
    sz = _box_sum(np.where(valid, nz, 0.0), w)
    count = _box_sum(valid.astype(float), w)
    out = np.full(nx.shape, np.nan, dtype=float)
    good = count > 0.0
    c = count[good]
    mx = sx[good] / c
    my = sy[good] / c
    mz = sz[good] / c
    resultant = np.sqrt(mx * mx + my * my + mz * mz)
    out[good] = 1.0 - np.clip(resultant, 0.0, 1.0)
    return np.clip(out, 0.0, 1.0)


def normal_roughness_signature(z, dx=1.0, window=5):
    """Compact, JSON-serialisable summary of the normal-roughness map.

    Returns plain Python floats computed over the FINITE cells of
    :func:`normal_roughness`::

        {"roughness_mean":   float,   # mean 1 - R
         "roughness_median": float,   # median 1 - R
         "roughness_p90":    float}   # 90th percentile (the rough tail)

    All three are dimensionless vector-strength deficits in ``[0, 1]``. If no
    valid cell exists (e.g. an all-NaN grid) every value is ``nan``. Carries the
    module's claim firewall: map-scale morphology / roughness only -- not a
    traversability, hazard, geologic, or mission claim.
    """
    r = normal_roughness(z, dx=dx, window=window)
    finite = r[np.isfinite(r)]
    if finite.size == 0:
        nan = float("nan")
        return {"roughness_mean": nan, "roughness_median": nan, "roughness_p90": nan}
    return {
        "roughness_mean": float(np.mean(finite)),
        "roughness_median": float(np.median(finite)),
        "roughness_p90": float(np.percentile(finite, 90.0)),
    }
