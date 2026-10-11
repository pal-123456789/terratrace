"""Wood (1996) / Dikau (1989) morphometric curvature-feature classification --
the six-fold peak / pit / ridge / channel / pass / planar surface taxonomy.

Wood, J. (1996). The Geomorphological Characterisation of Digital Elevation
Models. PhD thesis, University of Leicester.
Dikau, R. (1989). The application of a digital relief model to landform
analysis. In: Raper, J. (ed.), Three Dimensional Applications in Geographical
Information Systems. Taylor & Francis, London, 51-77.
Zevenbergen, L.W. & Thorne, C.R. (1987). Quantitative analysis of land surface
topography. Earth Surface Processes and Landforms 12, 47-56.

Every interior cell is labelled one of SIX morphometric feature types from the
SIGN of the two PRINCIPAL curvatures of a locally fitted quadratic surface, after
Wood (1996) (his ``maxic`` / ``minic`` -- the maximum and minimum curvature). The
quadratic is the Zevenbergen-Thorne (1987) 3x3 fit this engine already uses for
``features.profile_curvature`` / ``features.plan_curvature`` / ``mean_curvature``:
from its second-order coefficients D, E, F (for z = D x^2 + E y^2 + F xy + G x +
H y + I) the two principal curvatures, signed CONVEX-UP positive, are

    kappa_mean = -(D + E)                 # = 0.5 * features.mean_curvature(z, dx)
    disc       = hypot(D - E, F)          # half the curvature range (>= 0)
    k1         = kappa_mean + disc        # maximum convexity   (k1 >= k2 always)
    k2         = kappa_mean - disc        # minimum convexity

With a tolerance ``tol`` (see below), the six Wood/Dikau feature classes are a
mutually-exclusive partition of (k1, k2), using k1 >= k2 by construction:

    peak      k2 >  tol                        convex in every direction
    pit       k1 < -tol                        concave in every direction
    pass      k1 >  tol  AND  k2 < -tol        saddle (opposite-sign convexity)
    ridge     k1 >  tol  AND  |k2| <= tol      convex one way, straight across
    channel   |k1| <= tol  AND  k2 < -tol      concave one way, straight across
    planar    |k1| <= tol  AND  |k2| <= tol    no curvature: flat OR inclined plane

Why principal curvatures rather than the raw profile/plan signs: the engine's
``profile_curvature`` / ``plan_curvature`` are SLOPE-REFERENCED (along- and
across-slope) normal curvatures. On this engine they VANISH at the flat apex of a
dome or pit (slope -> 0 there) and take EQUAL signs on a saddle (profile = plan),
so their raw signs invert peak<->pass and cannot separate the three. The
principal curvatures (the eigen-curvatures of the SAME quadratic) are
rotation-invariant and non-degenerate at flat extrema -- exactly what the Wood
feature taxonomy needs. This module therefore reuses the engine primitives it
legitimately can (``features.slope_deg`` for the near-flat / NaN context and
``features.profile_curvature`` / ``features.plan_curvature`` to size the
automatic tolerance) and builds the sign-stable principal curvatures from the
shared Zevenbergen-Thorne quadratic (whose convex-up mean is exactly the engine's
``features.mean_curvature``).

Tolerance. ``tol=None`` (default, auto) uses ``tol = max(0.5 * std, floor)``,
where ``std`` is the standard deviation of the pooled finite curvature values
(the two principal curvatures and the engine's profile/plan curvatures) and
``floor`` is a tiny absolute curvature so an exactly planar grid stays
``planar`` -- i.e. a small multiple of the robust curvature scale of the surface,
exactly as in the sibling descriptor modules. Pass a float to fix ``tol``.

Scientific boundary / claim firewall: this is a purely GEOMETRIC curvature-sign
feature classification (Wood 1996 / Dikau 1989) of the sampled height field. A
feature label ("peak", "ridge", ...) is a descriptive SHAPE of the local surface
and nothing more -- it is NOT a geological-unit, landform-genesis, process,
material, hazard, trafficability, or mission claim on Mars, the Moon, Mercury,
Ceres, Earth or any body. It is distinct from the geomorphon classifier (a
line-of-sight ternary pattern) and the TPI landform classifier (a neighbourhood
slope-position) already in the engine, which describe different, complementary
geometry.

Pure NumPy, NaN-safe (any NaN in a cell's 3x3 stencil -> sentinel -1), vectorised
and deterministic -- no SciPy, no network, no disk.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "CLASS_NAMES",
    "CODE_TO_NAME",
    "principal_curvatures",
    "curvature_class_map",
    "curvature_class_signature",
]

#: Feature-class names in CODE order: index ``i`` is class code ``i`` in the
#: integer map from :func:`curvature_class_map` (sentinel ``-1`` = a NaN / border
#: / degenerate cell, deliberately NOT one of the six feature types).
CLASS_NAMES = ("planar", "peak", "pit", "ridge", "channel", "pass")

N_CLASSES = len(CLASS_NAMES)

#: Map from integer class code ``0..5`` to feature-class name. The sentinel
#: ``-1`` is absent on purpose; use ``CODE_TO_NAME.get(code)`` -> ``None`` for it.
CODE_TO_NAME = {code: name for code, name in enumerate(CLASS_NAMES)}

_PLANAR, _PEAK, _PIT, _RIDGE, _CHANNEL, _PASS = range(N_CLASSES)

_FLOOR = 1e-9        # absolute curvature floor: keeps an exact plane 'planar'

def _zt_second_derivs(z, dx):
    """Zevenbergen-Thorne (1987) 2nd-order coefficients (D, E, F) on interior 3x3
    windows -- the same stencil :func:`terratrace.features.mean_curvature` uses.

    For the local fit ``z = D x^2 + E y^2 + F xy + G x + H y + I`` returns the
    three interior arrays ``(D, E, F)`` shaped ``(rows-2, cols-2)`` at grid
    spacing ``dx``. Any NaN in a cell's 3x3 neighbourhood propagates to NaN, so
    border and nodata cells drop out naturally (NaN-safe, vectorised).
    """
    z = np.asarray(z, dtype=float)
    l2 = float(dx) * float(dx)
    z1, z2, z3 = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    z4, z5, z6 = z[1:-1, :-2], z[1:-1, 1:-1], z[1:-1, 2:]
    z7, z8, z9 = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    d = ((z4 + z6) / 2.0 - z5) / l2
    e = ((z2 + z8) / 2.0 - z5) / l2
    f = (-z1 + z3 + z7 - z9) / (4.0 * l2)
    return d, e, f


def principal_curvatures(z, dx=1.0):
    """Two principal curvatures of the local Zevenbergen-Thorne quadratic.

    Returns ``(k1, k2)``, each a float64 interior array shaped ``(rows-2,
    cols-2)``, signed CONVEX-UP positive, with ``k1 >= k2`` wherever finite::

        k1 = -(D + E) + hypot(D - E, F)      # maximum convexity (Wood 'maxic')
        k2 = -(D + E) - hypot(D - E, F)      # minimum convexity (Wood 'minic')

    Their sum equals ``features.mean_curvature(z, dx)`` (the convex-up mean
    curvature) and both are ``nan`` wherever the 3x3 stencil touches a NaN. For a
    dome ``z = -(x^2+y^2)`` both are ``+2`` (a peak); for a bowl ``z = x^2+y^2``
    both ``-2`` (a pit); for a saddle ``z = x^2-y^2`` they are ``+2`` and ``-2``
    (a pass). Pure NumPy, NaN-safe, deterministic. ``dx`` scales the curvature
    magnitude (units of 1/length); a non-finite or non-positive ``dx``, a non-2-D
    grid, or a grid smaller than 3x3 returns a pair of empty arrays.
    """
    z = np.asarray(z, dtype=float)
    dxf = float(dx)
    if z.ndim != 2 or min(z.shape) < 3 or not np.isfinite(dxf) or dxf <= 0.0:
        empty = np.empty((0, 0), dtype=float)
        return empty, empty.copy()
    d, e, f = _zt_second_derivs(z, dxf)
    kappa_mean = -(d + e)
    disc = np.hypot(d - e, f)
    return kappa_mean + disc, kappa_mean - disc

def _auto_tol(k1, k2, kp, kc):
    """Automatic curvature tolerance ``max(0.5 * std(pool), _FLOOR)``.

    ``pool`` is every finite value among the principal curvatures ``k1, k2`` and
    the engine's profile/plan curvatures ``kp, kc`` -- a robust curvature scale
    for the surface (all four are curvatures in the same 1/length units). An
    exactly planar (zero-curvature) grid gives ``std == 0`` so the tolerance falls
    to the tiny absolute :data:`_FLOOR` and the grid stays ``planar``.
    """
    parts = [np.asarray(a, dtype=float).ravel() for a in (k1, k2, kp, kc)]
    pool = np.concatenate(parts) if parts else np.empty(0, dtype=float)
    pool = pool[np.isfinite(pool)]
    scale = float(np.std(pool)) if pool.size else 0.0
    return max(0.5 * scale, _FLOOR)


def curvature_class_map(z, dx=1.0, tol=None):
    """Wood (1996) six-class morphometric feature map (int8, one code per cell).

    Returns an int8 array shaped like ``z``. Interior cells carry a class code
    ``0..5`` (:data:`CODE_TO_NAME`): ``0=planar, 1=peak, 2=pit, 3=ridge,
    4=channel, 5=pass``. The one-cell border and any cell whose 3x3 curvature
    stencil (or slope) is NaN carry the sentinel ``-1``. Classification is the
    principal-curvature sign rule documented in the module docstring; ``tol`` is
    auto-sized from the surface when ``None`` (:func:`_auto_tol`), else the given
    float. Reuses ``features.slope_deg`` for the near-flat / NaN validity context
    and ``features.profile_curvature`` / ``features.plan_curvature`` to size the
    tolerance. Vectorised, NaN-safe, deterministic.
    """
    from terratrace import features

    z = np.asarray(z, dtype=float)
    out = np.full(np.shape(z), -1, dtype=np.int8)
    dxf = float(dx)
    if z.ndim != 2 or min(z.shape) < 3 or not np.isfinite(dxf) or dxf <= 0.0:
        return out

    k1, k2 = principal_curvatures(z, dx=dxf)
    kp = features.profile_curvature(z, dx=dxf)
    kc = features.plan_curvature(z, dx=dxf)
    slope = features.slope_deg(z, dx=dxf)[1:-1, 1:-1]        # interior slope (deg)

    t = _auto_tol(k1, k2, kp, kc) if tol is None else float(tol)

    finite = np.isfinite(k1) & np.isfinite(k2) & np.isfinite(slope)
    cond = [
        k2 > t,                              # peak    (k1 >= k2 > t)
        k1 < -t,                             # pit     (k2 <= k1 < -t)
        (k1 > t) & (k2 < -t),                # pass    (saddle)
        (k1 > t) & (np.abs(k2) <= t),        # ridge
        (np.abs(k1) <= t) & (k2 < -t),       # channel
    ]
    choice = [_PEAK, _PIT, _PASS, _RIDGE, _CHANNEL]
    codes = np.select(cond, choice, default=_PLANAR)
    out[1:-1, 1:-1] = np.where(finite, codes, -1).astype(np.int8)
    return out

def curvature_class_signature(z, dx=1.0, tol=None):
    """Compact, JSON-serialisable Wood (1996) curvature-feature signature.

    Classifies ``z`` with :func:`curvature_class_map` and returns::

        {"composition": {name: fraction for every name in CLASS_NAMES},
         "dominant_class": name}

    ``composition`` is the area fraction of each of the six feature classes over
    the CLASSIFIED (non ``-1``) cells and sums to ~1 (all zeros for an all-NaN or
    too-small grid). ``dominant_class`` is the class with the largest fraction,
    ties broken toward the lower :data:`CLASS_NAMES` index (``"planar"`` for an
    empty grid). Deterministic and NaN-safe. Carries the module's claim firewall:
    a purely geometric curvature-sign SHAPE classification, not a geological,
    process, hazard, or mission claim on any body.
    """
    codes = curvature_class_map(z, dx=dx, tol=tol)
    valid = codes >= 0
    total = int(np.count_nonzero(valid))
    if total:
        counts = np.bincount(codes[valid].astype(np.int64), minlength=N_CLASSES)
    else:
        counts = np.zeros(N_CLASSES, dtype=np.int64)
    composition = {CLASS_NAMES[c]: (float(counts[c]) / total if total else 0.0)
                   for c in range(N_CLASSES)}
    dominant = max(range(N_CLASSES), key=lambda c: composition[CLASS_NAMES[c]])
    return {"composition": composition, "dominant_class": CLASS_NAMES[dominant]}




