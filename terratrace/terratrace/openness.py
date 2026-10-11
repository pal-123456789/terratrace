"""Topographic openness (Yokoyama, Shirasawa & Pike, 2002).

Topographic openness measures how "exposed" or "enclosed" a location is on a
surface by looking along lines of sight in a set of azimuth directions. For
each cell a ray is cast outward along each of eight azimuths (the four
cardinals + four diagonals), stepping ``1..radius`` cells. Along a ray the
engine records the steepest *upward* elevation angle (``beta_up``) and the
steepest *downward* depression angle (``beta_down``). The per-direction
**zenith** angle is ``90 - beta_up`` and the per-direction **nadir** angle is
``90 - beta_down`` (equivalently ``90 + min_along_ray(angle)``), both in
degrees.

* **Positive openness** = mean over the eight directions of the zenith angle.
  It is HIGH on convex / exposed features (peaks, ridges, spur crests) and can
  exceed 90 degrees at a peak (where every sight line goes downward, so
  ``beta_up`` is negative). It is LOW inside pits and closed depressions.
* **Negative openness** = mean over the eight directions of the nadir angle.
  It is the mirror: HIGH in pits, valleys and channels, LOW on peaks.

On a perfectly flat surface both openness values equal exactly 90 degrees. On
a uniform planar tilt both are ~90 as well, because the up angle in one
direction is cancelled by the down angle in the opposite direction when the
eight directions are averaged.

Implementation notes:

* Pure NumPy. The eight rays are evaluated with whole-array shifts (the grid
  is NaN-padded by ``radius`` and shifted windows are sliced out); there are
  no per-cell Python loops over the grid, so a 96x96 call runs in well under a
  second.
* NaN-safe. Nodata cells are ``np.nan``; ``np.fmax`` / ``np.fmin`` skip NaN
  samples, so NaN padding at the array edge simply truncates a ray. If a
  direction has no valid sample for a cell it is dropped from that cell's mean
  (the mean is taken over the valid directions only); if a cell has no valid
  direction at all its openness is set to 90.0 degrees.

Scientific boundary / claim firewall: openness is a map-scale *morphology and
visualisation* descriptor. It is NOT a traversability, trafficability, hazard,
or mission-readiness measure, and nothing here estimates rover behaviour,
rock-scale obstacles, or geological equivalence.

Reference:
    Yokoyama, R., Shirasawa, M., Pike, R.J. (2002). Visualizing topography by
    openness: a new application of image processing to DEMs. Photogrammetric
    Engineering & Remote Sensing 68(3), 257-265.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "positive_openness",
    "negative_openness",
    "openness",
    "openness_signature",
]

_SQRT2 = np.sqrt(2.0)

# The eight Yokoyama azimuths as integer (row, col) unit steps plus a flag for
# whether the step is diagonal (so its horizontal spacing is dx*sqrt(2)).
# Rows increase downward, columns increase to the right.
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
    """Only Yokoyama's eight azimuths are implemented.

    The ``n_dirs`` argument is kept on the public functions for forward
    compatibility and signature stability, but any value other than 8 is
    rejected rather than silently approximated.
    """
    if int(n_dirs) != 8:
        raise ValueError(
            "only n_dirs=8 (the four cardinal + four diagonal azimuths) "
            "is implemented"
        )


def _dir_mean(stack):
    """Mean over the direction axis, ignoring NaN (invalid) directions.

    ``stack`` has shape ``(n_dirs, rows, cols)`` holding a per-direction angle
    (zenith or nadir) with ``np.nan`` where that direction had no valid sample
    for the cell. The result is the mean over the *valid* directions only; a
    cell with zero valid directions falls back to 90.0 degrees.
    """
    valid = np.isfinite(stack)
    count = valid.sum(axis=0)
    total = np.nansum(stack, axis=0)              # NaN directions count as 0
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = total / count
    return np.where(count > 0, mean, 90.0).astype(np.float64)


def _openness_fields(z, dx=1.0, radius=10):
    """Core engine: return ``(positive, negative)`` openness fields in degrees.

    Both outputs are ``float64`` arrays with the same shape as ``z``.
    """
    z0 = np.asarray(z, dtype=np.float64)
    if z0.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    r = int(radius)
    if r < 1:
        raise ValueError("radius must be a positive integer number of cells")
    if dx <= 0:
        raise ValueError("dx must be a positive grid spacing in metres")

    rows, cols = z0.shape
    # NaN-pad by `radius` on every side so a shifted window never runs off the
    # real data; padded (nodata) samples are skipped by fmax / fmin below.
    padded = np.pad(z0, r, mode="constant", constant_values=np.nan)

    zenith_dirs = []
    nadir_dirs = []
    for di, dj, diagonal in _DIRECTIONS:
        # Steepest upward angle and smallest signed angle seen along this ray.
        beta_up = np.full((rows, cols), np.nan)   # max over ray of angle
        min_angle = np.full((rows, cols), np.nan)  # min over ray of angle
        spacing = dx * (_SQRT2 if diagonal else 1.0)
        for k in range(1, r + 1):
            rs = r + k * di
            cs = r + k * dj
            neighbour = padded[rs:rs + rows, cs:cs + cols]
            # Elevation angle of the neighbour as seen from the centre cell.
            angle = np.degrees(np.arctan2(neighbour - z0, k * spacing))
            beta_up = np.fmax(beta_up, angle)      # ignores NaN samples
            min_angle = np.fmin(min_angle, angle)  # ignores NaN samples
        # zenith = 90 - beta_up ; nadir = 90 - beta_down = 90 + min(angle).
        zenith_dirs.append(90.0 - beta_up)
        nadir_dirs.append(90.0 + min_angle)

    positive = _dir_mean(np.stack(zenith_dirs, axis=0))
    negative = _dir_mean(np.stack(nadir_dirs, axis=0))
    return positive, negative


def positive_openness(z, dx=1.0, radius=10, n_dirs=8):
    """Positive (sky / exposure) openness in degrees, same shape as ``z``.

    High on convex, exposed features (peaks, ridges) -- can exceed 90 at a
    peak -- and low in pits. See the module docstring for the full definition.
    """
    _check_n_dirs(n_dirs)
    return _openness_fields(z, dx=dx, radius=radius)[0]


def negative_openness(z, dx=1.0, radius=10, n_dirs=8):
    """Negative (ground / enclosure) openness in degrees, same shape as ``z``.

    The mirror of positive openness: high in pits, valleys and channels, low
    on peaks and ridges.
    """
    _check_n_dirs(n_dirs)
    return _openness_fields(z, dx=dx, radius=radius)[1]


def openness(z, dx=1.0, radius=10):
    """Both openness fields as ``{"positive": arr, "negative": arr}``.

    Each value is a ``float64`` array in degrees with the same shape as ``z``.
    """
    positive, negative = _openness_fields(z, dx=dx, radius=radius)
    return {"positive": positive, "negative": negative}


def openness_signature(z, dx=1.0, radius=10):
    """NaN-robust scalar summary of a tile's openness, as plain Python floats.

    Returns the median and the 10th / 90th percentiles of both the positive
    and the negative openness fields::

        {positive_median, negative_median,
         positive_p10, positive_p90, negative_p10, negative_p90}

    All values are plain ``float`` so the signature is JSON-serialisable. It
    carries the same claim firewall as the module: map-scale morphology only.
    """
    fields = openness(z, dx=dx, radius=radius)
    positive = fields["positive"]
    negative = fields["negative"]
    return {
        "positive_median": float(np.nanmedian(positive)),
        "negative_median": float(np.nanmedian(negative)),
        "positive_p10": float(np.nanpercentile(positive, 10.0)),
        "positive_p90": float(np.nanpercentile(positive, 90.0)),
        "negative_p10": float(np.nanpercentile(negative, 10.0)),
        "negative_p90": float(np.nanpercentile(negative, 90.0)),
    }
