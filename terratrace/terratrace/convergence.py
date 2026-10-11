"""Koethe & Lehmeier (1996) / Kiss (2004) convergence index -- aspect-field
convergence vs divergence of a surface.

Koethe, R. & Lehmeier, F. (1996). SARA -- System zur Automatischen
Relief-Analyse. Benutzerhandbuch. Dept. of Geography, University of Goettingen.
Kiss, R. (2004). Determination of drainage network in digital elevation models,
utilities and limitations. Journal of Hungarian Geomathematics 2, 17-29.

The convergence index measures how the ASPECT vectors of the eight neighbours of
a cell point relative to that cell. Aspect is the compass direction a surface
faces -- the azimuth of steepest DESCENT, i.e. the direction of ``-grad z``. For
a centre cell this module takes each of its 8 neighbours, measures the angle
(0..180 deg) between that neighbour's aspect direction and the direction pointing
FROM the neighbour back TOWARD the centre, averages the eight angles and
subtracts 90:

    CI = mean_i( angle_i ) - 90      angle_i = <aspect(nbr_i), nbr_i -> centre>

so CI is bounded to ``[-90, +90]`` degrees. When the surrounding aspects point
AWAY from the centre (a peak or ridge -- the aspects diverge) the angles are
large and CI > 0; when they point TOWARD the centre (a pit or valley -- the
aspects converge) the angles are small and CI < 0; a planar patch with a single
uniform aspect averages to exactly 90 and gives CI ~ 0.

SIGN CONVENTION (used throughout, matching the standard geomorphometric
definition of Koethe & Lehmeier / Kiss):

    CI > 0  ->  DIVERGENT   (peak / ridge / dome; aspects fan outward)
    CI < 0  ->  CONVERGENT  (pit / valley / hollow; aspects point inward)
    CI ~ 0  ->  PLANAR      (uniform aspect)

Computation. ``gy, gx = np.gradient(z, dx, dx)`` gives the surface gradient; the
unit aspect vector is ``(-gx, -gy)`` normalised (undefined -> NaN on flat cells
where ``|grad z| == 0``). The eight neighbour aspects are gathered by NaN-padded
shifts of that field; for a neighbour at grid offset ``(off_x, off_y)`` the unit
vector pointing back to the centre is ``(-off_x, -off_y)``, and the inter-vector
angle is ``degrees(arccos(clip(dot, -1, 1)))``. A cell is NaN unless it is an
interior cell with all eight neighbour aspects finite, so the one-cell border
ring and any cell touching nodata (or a flat, aspect-less neighbour) are NaN.
Pure NumPy, NaN-safe, deterministic -- no SciPy, no network, no disk, never
raises.

Scientific boundary / claim firewall: this is a purely GEOMETRIC measure of the
convergence/divergence of the aspect field of the sampled height grid, bounded in
degrees and complementary to plan curvature. It is NOT a claim of flow, running
water, drainage, erosion, sediment transport, hazard, trafficability, or any
surface/hydrological/mission process on Mars, the Moon, Mercury, Ceres, Earth or
any other body. "Convergence" and "divergence" are used in their abstract
grid-geometry (vector-field) sense only.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "convergence_field",
    "convergence_signature",
]

# 8-neighbour offsets as (row, col) == (di, dj); off_x = dj, off_y = di.
_OFFSETS = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)


def _aspect_unit_field(z, dx):
    """Unit aspect (steepest-descent) vector field of ``z``.

    Returns ``(ax, ay)`` float64 arrays shaped like ``z`` holding the x (column)
    and y (row) components of the unit vector ``(-gx, -gy)/|grad z|`` from
    ``np.gradient(z, dx, dx)``. Flat cells (``|grad z| == 0``) and NaN-
    contaminated cells carry NaN in both components, so they contribute no
    direction to the convergence average.
    """
    gy, gx = np.gradient(z, dx, dx)
    with np.errstate(invalid="ignore", divide="ignore"):
        norm = np.hypot(gx, gy)
        ax = -gx / norm
        ay = -gy / norm
    flat = ~(norm > 0.0)                 # True on zero-gradient or non-finite cells
    ax[flat] = np.nan
    ay[flat] = np.nan
    return ax, ay


def convergence_field(z, dx=1.0):
    """Convergence-index field of ``z`` in degrees, range ``[-90, +90]``.

    For every interior cell the eight neighbour aspect vectors are compared with
    the directions pointing back to that cell; the mean of the eight angles minus
    90 is the cell's convergence index (see the module docstring). Positive =
    DIVERGENT (peak/ridge), negative = CONVERGENT (pit/valley), ~0 = planar.

    Returns a float64 array shaped like ``z``. A cell is NaN unless it is an
    interior cell whose eight neighbours all have a finite aspect, so the
    one-cell border ring and any cell touching nodata (NaN) or a flat,
    aspect-less neighbour are NaN. Pure NumPy, deterministic, never raises:
    non-2-D, degenerate (fewer than 3 rows/cols) or ``dx <= 0`` inputs yield an
    all-NaN array shaped like ``z``.
    """
    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if z.ndim != 2 or z.shape[0] < 3 or z.shape[1] < 3 or dx <= 0.0:
        return np.full(z.shape, np.nan, dtype=float)

    ax, ay = _aspect_unit_field(z, dx)
    h, w = z.shape
    axp = np.pad(ax, 1, mode="constant", constant_values=np.nan)
    ayp = np.pad(ay, 1, mode="constant", constant_values=np.nan)

    angles = np.empty((len(_OFFSETS), h, w), dtype=float)
    for k, (di, dj) in enumerate(_OFFSETS):
        inv = 1.0 / np.hypot(float(dj), float(di))
        ux = -float(dj) * inv            # x-component of neighbour -> centre unit vec
        uy = -float(di) * inv            # y-component of neighbour -> centre unit vec
        ax_sh = axp[1 + di:1 + di + h, 1 + dj:1 + dj + w]
        ay_sh = ayp[1 + di:1 + di + h, 1 + dj:1 + dj + w]
        dot = ax_sh * ux + ay_sh * uy
        with np.errstate(invalid="ignore"):
            angles[k] = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))

    # Mean of the eight neighbour angles minus 90. A plain mean propagates NaN:
    # any off-grid (NaN-padded border) or nodata/flat neighbour makes the cell
    # NaN, so the border ring and NaN-contaminated cells drop out as required.
    ci = np.mean(angles, axis=0) - 90.0
    ci[0, :] = np.nan
    ci[-1, :] = np.nan
    ci[:, 0] = np.nan
    ci[:, -1] = np.nan
    return ci


def convergence_signature(z, dx=1.0):
    """Flat, JSON-serialisable summary of the convergence-index field of ``z``.

    Builds :func:`convergence_field`, drops non-finite cells (border, nodata,
    flat) and summarises the remaining finite convergence indices::

        {"convergence_mean":   float,  # mean CI over finite cells (deg)
         "convergence_median": float,  # median CI (deg)
         "convergence_std":    float,  # population std of CI (deg)
         "convergent_fraction": float, # fraction of finite cells with CI < 0
         "divergent_fraction":  float} # fraction of finite cells with CI > 0

    A divergent surface (peak/ridge-like) gives ``convergence_mean > 0`` and
    ``divergent_fraction > convergent_fraction``; a convergent surface
    (pit/valley-like) gives the mirror image. With no finite cells the three
    moments are ``nan`` and both fractions ``0.0`` (nan/0-safe). All values are
    plain Python floats; deterministic and NaN-safe. Carries the module's claim
    firewall: a purely geometric aspect-field convergence measure, not a flow,
    water, erosion, hazard or mission claim on any body.
    """
    nan = float("nan")
    out = {
        "convergence_mean": nan,
        "convergence_median": nan,
        "convergence_std": nan,
        "convergent_fraction": 0.0,
        "divergent_fraction": 0.0,
    }

    field = convergence_field(z, dx=dx)
    vals = field[np.isfinite(field)]
    n = int(vals.size)
    if n == 0:
        return out

    out["convergence_mean"] = float(vals.mean())
    out["convergence_median"] = float(np.median(vals))
    out["convergence_std"] = float(vals.std())
    out["convergent_fraction"] = float(np.count_nonzero(vals < 0.0) / n)
    out["divergent_fraction"] = float(np.count_nonzero(vals > 0.0) / n)
    return out
