"""Sky-View Factor (Zakšek, Oštir & Kokalj, 2011).

The sky-view factor (SVF) is the fraction of the overlying sky hemisphere that
is visible from a point -- the part of the sky dome NOT occluded by the
surrounding relief. It is computed here from the same horizon-angle scan as
positive topographic openness (Yokoyama et al., 2002): for each cell and each
of eight azimuths (the four cardinals + four diagonals) a ray is cast outward
``1..max_radius`` cells and the steepest upward horizon elevation angle on that
ray is recorded,

    gamma_d = max_r atan( (z_neighbour - z_cell) / horizontal_distance ),

clamped to ``>= 0`` because the sky cannot be occluded below the local
horizontal. The horizontal distance is ``r*dx`` along a cardinal azimuth and
``r*dx*sqrt(2)`` along a diagonal one (the true diagonal spacing). Under the
standard isotropic-sky discretisation the sky-view factor is

    SVF = 1 - mean_d( sin(gamma_d) )            in [0, 1].

SVF is 1.0 on perfectly flat / open ground (every horizon angle is 0), is < 1
wherever surrounding terrain rises above the horizontal (valleys and pits --
lower for deeper, steeper enclosure), and is ~1 at or near an isolated peak
(nothing rises above the apex).

Pure NumPy, deterministic and NaN-safe. The eight rays are evaluated with
whole-array shifts (the grid is NaN-padded by ``max_radius`` and shifted
windows are sliced out), so there are no per-cell Python loops. ``np.fmax``
skips NaN samples, so edge padding simply truncates a ray and border cells
average over their valid azimuths only; a NaN *input* cell has no valid azimuth
and propagates NaN.

Scientific boundary / claim firewall: the sky-view factor computed here is a
purely GEOMETRIC visible-sky fraction derived from horizon elevation angles --
closely related to positive topographic openness (Yokoyama 2002) but
normalised to ``[0, 1]`` as the hemispherical sky fraction in the sense of
Zakšek (2011). It is a map-scale morphology / visualisation descriptor only. It
is NOT an insolation, radiation-budget, thermal, illumination / daylighting-
engineering, energy, or mission claim; nothing here estimates sunlight,
temperature, time-varying shadowing, rover behaviour, or geological equivalence
on Mars, the Moon, Mercury, Ceres, Earth or any other body.

References:
    Zakšek, K., Oštir, K., Kokalj, Ž. (2011). Sky-view factor as a relief
    visualization technique. Remote Sensing 3(2), 398-415.
    Yokoyama, R., Shirasawa, M., Pike, R.J. (2002). Visualizing topography by
    openness. Photogrammetric Engineering & Remote Sensing 68(3), 257-265.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "svf_field",
    "svf_signature",
]

_SQRT2 = np.sqrt(2.0)

# The eight azimuths as integer (row, col) unit steps plus a diagonal flag
# (diagonal steps have horizontal spacing dx*sqrt(2)). Rows increase downward,
# columns increase to the right -- identical to the openness scan.
_DIRECTIONS = (
    (-1, 0, False),   # N
    (1, 0, False),    # S
    (0, -1, False),   # W
    (0, 1, False),    # E
    (-1, -1, True),   # NW
    (-1, 1, True),    # NE
    (1, -1, True),    # SW
    (1, 1, True),     # SE
)


def _check_n_dirs(n_dirs):
    """Only the eight cardinal + diagonal azimuths are implemented.

    ``n_dirs`` is kept on the public signature for forward compatibility, but
    any value other than 8 is rejected rather than silently approximated.
    """
    if int(n_dirs) != 8:
        raise ValueError(
            "only n_dirs=8 (the four cardinal + four diagonal azimuths) "
            "is implemented"
        )


def svf_field(z, dx=1.0, n_dirs=8, max_radius=10):
    """Sky-view factor field in ``[0, 1]``, same shape as ``z``.

    For each cell and each of the eight azimuths the steepest upward horizon
    elevation angle over ``r = 1..max_radius`` is found (clamped to ``>= 0``);
    the field is ``SVF = 1 - mean_d(sin(gamma_d))``. It is 1.0 on flat / open
    ground, < 1 in valleys and pits, and ~1 at an isolated peak.

    Pure NumPy, deterministic and NaN-safe: off-grid samples are NaN-padded and
    skipped, border cells average over their valid azimuths, and a NaN input
    cell propagates NaN. See the module docstring for the full definition and
    claim firewall (a purely geometric visible-sky fraction only).
    """
    _check_n_dirs(n_dirs)
    z0 = np.asarray(z, dtype=np.float64)
    if z0.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    r_max = int(max_radius)
    if r_max < 1:
        raise ValueError("max_radius must be a positive integer number of cells")
    if dx <= 0:
        raise ValueError("dx must be a positive grid spacing in metres")

    rows, cols = z0.shape
    # NaN-pad by `max_radius` so a shifted window never runs off the real data;
    # padded (nodata) samples are skipped by fmax below.
    padded = np.pad(z0, r_max, mode="constant", constant_values=np.nan)

    sin_dirs = []
    for di, dj, diagonal in _DIRECTIONS:
        gamma = np.full((rows, cols), np.nan)    # steepest horizon angle on ray
        spacing = dx * (_SQRT2 if diagonal else 1.0)
        for k in range(1, r_max + 1):
            rs = r_max + k * di
            cs = r_max + k * dj
            neighbour = padded[rs:rs + rows, cs:cs + cols]
            # Elevation angle of the neighbour above the centre cell; the
            # positive second argument makes arctan2 equal atan(dz / distance).
            angle = np.arctan2(neighbour - z0, k * spacing)
            gamma = np.fmax(gamma, angle)         # NaN-aware max over the ray
        # The sky is not occluded below the local horizontal -> clamp to >= 0;
        # np.maximum keeps NaN for azimuths that had no valid sample at all.
        gamma = np.maximum(gamma, 0.0)
        sin_dirs.append(np.sin(gamma))

    stack = np.stack(sin_dirs, axis=0)            # (8, rows, cols); NaN=invalid
    valid = np.isfinite(stack)
    count = valid.sum(axis=0).astype(np.float64)
    total = np.nansum(stack, axis=0)              # NaN azimuths contribute 0
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_sin = total / count                  # 0/0 -> NaN where no valid dir
    return (1.0 - mean_sin).astype(np.float64)


def svf_signature(z, dx=1.0):
    """NaN-robust scalar summary of a tile's sky-view factor, as plain floats.

    Computes :func:`svf_field` with the default eight azimuths / ``max_radius``
    and reduces over the FINITE cells to::

        {"svf_mean", "svf_median", "svf_p10", "svf_p90", "svf_min"}

    Every value is a plain ``float`` (``nan`` when no cell is finite) so the
    signature is JSON-serialisable and deterministic. It carries the module's
    claim firewall: a purely geometric visible-sky fraction, not an insolation,
    thermal, illumination, or mission measure.
    """
    nan = float("nan")
    field = svf_field(z, dx=dx)
    finite = field[np.isfinite(field)]
    if finite.size == 0:
        return {"svf_mean": nan, "svf_median": nan,
                "svf_p10": nan, "svf_p90": nan, "svf_min": nan}
    return {
        "svf_mean": float(np.mean(finite)),
        "svf_median": float(np.median(finite)),
        "svf_p10": float(np.percentile(finite, 10.0)),
        "svf_p90": float(np.percentile(finite, 90.0)),
        "svf_min": float(np.min(finite)),
    }
