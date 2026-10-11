"""Directional terrain-fabric (anisotropy) analyzer via the directional
structure function.

Many landscapes carry a *fabric*: a preferred horizontal direction imposed by
parallel ridges, dunes, yardangs, wind streaks, flutes, or tectonic grain. This
module measures that fabric from a bare elevation grid using a difference-based
(structure-function) roughness evaluated along a fan of azimuths, and summarises
it as a single orientation plus an anisotropy strength.

The idea: for a given azimuth ``theta`` and pixel separation ``lag`` we compare
every cell with the cell ``lag`` steps away along ``theta`` and take the RMS of
their elevation difference -- the directional roughness

    R(theta) = sqrt( nanmean( (z - z_shifted_along_theta)^2 ) ).

A lineated terrain of parallel ridges changes little ALONG a crest but a lot
ACROSS the crests, so ``R`` is LOW along the ridge strike and HIGH perpendicular
to it. We therefore report:

* ``orientation_deg`` -- the azimuth of MINIMUM directional roughness. This is
  the fabric / lineation strike: the ridges (or dunes, flutes, grain) run this
  way.
* ``strength`` -- ``(Rmax - Rmin) / (Rmax + Rmin)`` over the azimuthal roughness
  values, in ``[0, 1]``. ``0`` is isotropic (no preferred direction); values
  approaching ``1`` mean a strongly lineated, one-directional fabric.
* ``isotropy`` -- ``Rmin / Rmax`` in ``[0, 1]`` (``1`` = isotropic). It is the
  simple complement of the fabric contrast.

Azimuth convention (fixed and explicit):

* ``0 degrees`` points along ``+x`` = EAST = increasing COLUMN index ``j``.
* ``90 degrees`` points along ``+y`` = NORTH = increasing ROW index ``i``.
* The integer pixel offset for azimuth ``theta`` is
  ``(di, dj) = (round(lag*sin theta), round(lag*cos theta))`` where ``dj`` steps
  columns (x) and ``di`` steps rows (y).
* Because the roughness is a *difference* statistic, ``theta`` and
  ``theta + 180`` give the same pair set, so azimuths are binned over
  ``[0, 180)`` only.

Default lag and the actual integer offsets: the default ``lag=3`` is chosen so
the ``n_dirs=8`` azimuths ``[0, 22.5, 45, 67.5, 90, 112.5, 135, 157.5]`` map to
eight DISTINCT integer offsets ``(di, dj)``::

      0.0 deg -> ( 0,  3)      90.0 deg -> ( 3,  0)
     22.5 deg -> ( 1,  3)     112.5 deg -> ( 3, -1)
     45.0 deg -> ( 2,  2)     135.0 deg -> ( 2, -2)
     67.5 deg -> ( 3,  1)     157.5 deg -> ( 1, -3)

(``lag=2`` is also fully distinct; ``lag=1`` is NOT -- several azimuths collapse
onto the same offset -- so a lag of at least 2 is required to resolve eight
directions.)

Units: the structure-function roughness is in the SAME units as ``z``
(elevation); it is an RMS elevation difference, not a slope, so it is NOT scaled
by the grid spacing. ``dx`` is accepted on the public functions for signature
symmetry with the rest of the engine but does not enter the computation.

Implementation notes:

* Pure NumPy, no SciPy. Each azimuth is evaluated with whole-array slicing (the
  overlap window is sliced, never wrapped); the only loop is over the handful of
  azimuths, so a 96x96 call runs in well under a second.
* NaN-safe. Nodata cells are ``np.nan``; a pair with a NaN on either side is
  dropped from that azimuth's mean. If an azimuth has no valid pair at all its
  roughness is ``nan`` and that azimuth is excluded from the strength /
  orientation reduction. Adding a constant to ``z`` leaves every elevation
  difference unchanged, so the fabric is invariant to vertical datum offset.

Scientific boundary / claim firewall: anisotropy here is a map-scale
*morphology* descriptor of the sampled elevation grid only -- it reports the
directional structure (fabric) of the surface. It is NOT a traversability,
trafficability, hazard, route, slope-stability, geologic-origin, or
mission-readiness claim, and nothing here estimates rover behaviour or
rock-scale obstacles.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "directional_roughness",
    "anisotropy",
    "anisotropy_signature",
]


def _azimuth_offsets(n_dirs, lag):
    """Azimuths over ``[0, 180)`` and their integer ``(di, dj)`` pixel offsets.

    Returns ``(az_deg, di, dj)`` where ``az_deg`` is a float64 array of the
    ``n_dirs`` bin azimuths in degrees, ``di`` is the row (y) step and ``dj`` the
    column (x) step for each azimuth, following the module's convention
    ``(di, dj) = (round(lag*sin theta), round(lag*cos theta))``.
    """
    n = int(n_dirs)
    if n < 1:
        raise ValueError("n_dirs must be a positive integer")
    k = int(lag)
    if k < 1:
        raise ValueError("lag must be a positive integer number of cells")
    az_deg = np.linspace(0.0, 180.0, n, endpoint=False)
    theta = np.radians(az_deg)
    di = np.round(k * np.sin(theta)).astype(int)
    dj = np.round(k * np.cos(theta)).astype(int)
    return az_deg, di, dj


def _overlap_pair(z, di, dj):
    """Aligned ``(a, b)`` sub-arrays with ``a = z[i, j]`` and
    ``b = z[i + di, j + dj]`` over the valid overlap (sliced, never wrapped).

    Works for either sign of ``di`` / ``dj``; the returned views are empty when
    the shift exceeds the grid in some dimension.
    """
    rows, cols = z.shape
    if di >= 0:
        a_r, b_r = slice(0, rows - di), slice(di, rows)
    else:
        a_r, b_r = slice(-di, rows), slice(0, rows + di)
    if dj >= 0:
        a_c, b_c = slice(0, cols - dj), slice(dj, cols)
    else:
        a_c, b_c = slice(-dj, cols), slice(0, cols + dj)
    return z[a_r, a_c], z[b_r, b_c]


def _rms_diff(z, di, dj):
    """RMS elevation difference between ``z`` and itself shifted by
    ``(di, dj)``, over finite overlap pairs only.

    Returns a Python float, or ``nan`` when the offset is degenerate ``(0, 0)``
    or the overlap holds no finite pair.
    """
    if di == 0 and dj == 0:
        return float("nan")
    a, b = _overlap_pair(z, di, dj)
    if a.size == 0:
        return float("nan")
    sq = (a - b) ** 2
    if not np.isfinite(sq).any():
        return float("nan")
    return float(np.sqrt(np.nanmean(sq)))


def directional_roughness(z, dx=1.0, n_dirs=8, lag=3):
    """Structure-function roughness of ``z`` along each azimuth in ``[0, 180)``.

    For each of ``n_dirs`` azimuths ``theta`` (binned over ``[0, 180)``) the
    integer offset ``(di, dj) = (round(lag*sin theta), round(lag*cos theta))`` is
    formed -- ``dj`` steps columns (x/east), ``di`` steps rows (y/north) -- and
    the directional roughness ``sqrt(nanmean((z - z_shifted)^2))`` is computed
    over the sliced (non-wrapped) overlap, ignoring pairs with a NaN on either
    side.

    Parameters
    ----------
    z : 2-D array of elevations (NaN = nodata).
    dx : grid spacing; accepted for API symmetry only -- the roughness is an RMS
        elevation difference in ``z``'s own units and is NOT scaled by ``dx``.
    n_dirs : number of azimuth bins over ``[0, 180)``.
    lag : pixel separation; the default ``3`` gives eight distinct offsets.

    Returns
    -------
    (azimuths_deg, roughness) : two 1-D float64 ``ndarray`` of length ``n_dirs``.
        ``azimuths_deg`` lies in ``[0, 180)``; ``roughness`` holds the RMS
        elevation difference per azimuth (``nan`` for an azimuth with no finite
        pair).
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    az_deg, di, dj = _azimuth_offsets(n_dirs, lag)
    rough = np.array([_rms_diff(z, int(a), int(b)) for a, b in zip(di, dj)],
                     dtype=float)
    return az_deg, rough


def anisotropy(z, dx=1.0, n_dirs=8, lag=3):
    """Directional fabric summary of an elevation grid.

    Evaluates :func:`directional_roughness` and reduces the azimuthal roughness
    to a single fabric. Azimuths whose roughness is ``nan`` (no finite pair) are
    excluded from the reduction.

    Returns a dict::

        {"strength": float,            # (Rmax - Rmin) / (Rmax + Rmin), in [0, 1]
         "orientation_deg": float,     # azimuth of MINIMUM roughness = fabric strike
         "isotropy": float,            # Rmin / Rmax, in [0, 1] (1 = isotropic)
         "roughness_by_azimuth": {deg: val}}   # per-azimuth RMS difference

    ``strength`` is ``0`` for an isotropic surface and approaches ``1`` for a
    strongly lineated one. ``orientation_deg`` is the along-fabric direction
    (ridges / dunes run this way), following the module's azimuth convention
    (0 deg = +x/east, 90 deg = +y/north). A perfectly flat tile (all roughness
    ``0``) is reported as isotropic (``strength=0``, ``isotropy=1``). If NO
    azimuth has a finite pair, all three scalars are ``nan``.
    """
    az_deg, rough = directional_roughness(z, dx=dx, n_dirs=n_dirs, lag=lag)
    by_az = {float(a): float(r) for a, r in zip(az_deg, rough)}

    finite = np.isfinite(rough)
    if not finite.any():
        return {
            "strength": float("nan"),
            "orientation_deg": float("nan"),
            "isotropy": float("nan"),
            "roughness_by_azimuth": by_az,
        }

    az_f = az_deg[finite]
    r_f = rough[finite]
    r_min = float(r_f.min())
    r_max = float(r_f.max())
    orientation = float(az_f[int(np.argmin(r_f))])

    denom = r_max + r_min
    if denom <= 0.0:
        # Every direction is perfectly flat: no fabric is defined, report it as
        # isotropic rather than dividing 0 / 0.
        strength = 0.0
        isotropy = 1.0
    else:
        strength = (r_max - r_min) / denom
        isotropy = r_min / r_max

    return {
        "strength": float(strength),
        "orientation_deg": float(orientation),
        "isotropy": float(isotropy),
        "roughness_by_azimuth": by_az,
    }


def anisotropy_signature(z, dx=1.0):
    """Compact, JSON-serialisable fabric signature as plain Python floats.

    Runs :func:`anisotropy` with the default fan (``n_dirs=8``, ``lag=3``) and
    returns::

        {"strength": float,
         "orientation_deg": float,
         "isotropy": float,
         "mean_roughness": float}   # mean of the finite per-azimuth roughnesses

    Carries the module's claim firewall: map-scale morphology fabric only, not a
    traversability / hazard / geologic claim.
    """
    a = anisotropy(z, dx=dx)
    vals = [v for v in a["roughness_by_azimuth"].values() if np.isfinite(v)]
    mean_roughness = float(np.mean(vals)) if vals else float("nan")
    return {
        "strength": float(a["strength"]),
        "orientation_deg": float(a["orientation_deg"]),
        "isotropy": float(a["isotropy"]),
        "mean_roughness": mean_roughness,
    }
