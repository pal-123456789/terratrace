"""Surface-normal orientation-tensor fabric (Woodcock 1977) -- the eigen-SHAPE
of the distribution of facet orientations.

Woodcock, N. H. (1977). Specification of fabric shapes using an eigenvalue
method. Geological Society of America Bulletin, 88(9), 1231-1236.

Each grid cell carries a unit surface normal
``n = (-dz/dx, -dz/dy, 1) / |(-dz/dx, -dz/dy, 1)|`` with ``dz/dx`` and ``dz/dy``
from :func:`numpy.gradient` at spacing ``dx``. Treating the normals as
orientation axes, Woodcock summarises their distribution with the normalised
*orientation tensor* (the orientation / moment matrix)

    T = (1 / N) * sum_i  n_i n_i^T            (3x3, symmetric, trace 1)

whose eigenvalues ``lambda1 >= lambda2 >= lambda3 >= 0`` (normalised to sum 1)
describe the SHAPE of the orientation cloud, independent of its mean direction:

  * a tight CLUSTER (point fabric) has ``lambda1 ~ 1`` and ``lambda2, lambda3 ~
    0`` -- the normals are nearly parallel (e.g. a planar facet, however steep);
  * a GIRDLE has ``lambda1 ~ lambda2 >> lambda3`` -- the normals spread within a
    plane (e.g. a 1-D corrugation, whose normals all lie in one vertical plane);
  * an ISOTROPIC cloud has ``lambda1 ~ lambda2 ~ lambda3 ~ 1/3`` -- no preferred
    orientation.

Woodcock's two scalars place a fabric on this continuum:

    woodcock_K = ln(lambda1 / lambda2) / ln(lambda2 / lambda3)    # shape
    woodcock_C = ln(lambda1 / lambda3)                            # strength

``K > 1`` is a cluster / point fabric, ``K < 1`` a girdle, ``K = 1`` the neutral
line; ``C`` grows with the strength of the preferred orientation (``C -> 0`` for
a perfectly isotropic cloud, large for a strong cluster or a tight girdle). A
companion ``isotropy = 3 * lambda3`` in ``[0, 1]`` reads ``1`` for perfectly
isotropic normals and ``0`` when the smallest eigenvalue vanishes (any cluster,
or an ideal 1-D girdle whose normals lie exactly in one plane).

This is DISTINCT from the surface-normal *dispersion* roughness in
:mod:`terratrace.normal_roughness`: that measures the MAGNITUDE of the spread of
the normals (``1 - R``, how far from parallel), whereas this measures the SHAPE
of the spread (cluster vs girdle vs isotropic) through the orientation-tensor
eigenvalues. Two surfaces can share a dispersion yet differ in fabric shape --
e.g. an isotropic bumpy field and a 1-D corrugation can disperse the normals
equally while one is a cap and the other a girdle.

Degenerate eigenvalues are guarded with a small floor (``eps``) so the logs
never raise; where a Woodcock ratio is genuinely undefined (``lambda2 ~
lambda3`` so ``ln(lambda2 / lambda3) ~ 0``) ``woodcock_K`` is ``nan``.

Units: ``dx`` is the (isotropic) grid spacing in metres; the eigenvalues,
``woodcock_K``, ``woodcock_C`` and ``isotropy`` are all dimensionless. Pure
NumPy, vectorised, NaN-safe (a cell whose normal is undefined -- a NaN elevation
or a gradient neighbour of one -- is dropped before the tensor is formed) and
deterministic -- no SciPy, no network, no disk.

Scientific boundary / claim firewall: this is a purely GEOMETRIC eigen-analysis
of the surface-normal orientation distribution (Woodcock 1977); it summarises
how clustered vs girdled the facet orientations of the sampled height field are.
It is a map-scale morphology descriptor only -- NOT a process, geologic-origin,
traversability, trafficability, hazard, slope-stability or mission-readiness
claim on Mars, the Moon, Mercury, Ceres, Earth or any other body.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "orientation_tensor",
    "fabric_signature",
]

_EPS = 1e-12


def orientation_tensor(z, dx=1.0):
    """Normalised surface-normal orientation tensor ``T`` of elevation ``z``.

    With gradients ``dz/dx`` and ``dz/dy`` from :func:`numpy.gradient` at spacing
    ``dx`` (metres, isotropic), each cell's unit normal is
    ``n = (-dz/dx, -dz/dy, 1) / |(-dz/dx, -dz/dy, 1)|`` (so ``nz > 0``; the normal
    points up). Over the FINITE normals the function forms Woodcock's (1977)
    orientation tensor ``T = (1 / N) * sum_i n_i n_i^T`` -- a symmetric 3x3
    array with unit trace (each ``n`` is a unit vector, so ``trace(n n^T) = 1``).

    Returns the ``(3, 3)`` float64 array ``T``. NaN-safe: cells whose normal is
    undefined (a NaN elevation, or a cell adjacent to one after the gradient) are
    excluded from the sum; if NO cell has a finite normal (e.g. an all-NaN grid)
    the tensor is all-``nan``. Raises :class:`ValueError` for a non-2-D ``z`` or a
    non-positive / non-finite ``dx``.
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
        nx = (-gx / norm).ravel()
        ny = (-gy / norm).ravel()
        nz = (1.0 / norm).ravel()

    finite = np.isfinite(nx) & np.isfinite(ny) & np.isfinite(nz)
    comps = np.stack([nx[finite], ny[finite], nz[finite]], axis=0)  # (3, N)
    n = comps.shape[1]
    if n == 0:
        return np.full((3, 3), np.nan, dtype=float)
    t = (comps @ comps.T) / float(n)
    return 0.5 * (t + t.T)          # symmetrise against round-off


def fabric_signature(z, dx=1.0):
    """Woodcock (1977) orientation-tensor fabric signature of ``z``.

    Builds the orientation tensor with :func:`orientation_tensor`, takes its
    eigenvalues (clipped to ``>= 0`` and renormalised to sum 1) and returns a
    compact, JSON-serialisable dict of plain Python floats::

        {"eig1":       float,   # lambda1 >= lambda2 >= lambda3, sum == 1
         "eig2":       float,
         "eig3":       float,
         "woodcock_K": float,   # ln(l1/l2) / ln(l2/l3): K>1 cluster, K<1 girdle
         "woodcock_C": float,   # ln(l1/l3): fabric strength (large = strong)
         "isotropy":   float}   # 3*lambda3 in [0, 1]; 1 = perfectly isotropic

    A nearly planar surface -> strong CLUSTER (``eig1 ~ 1``, ``woodcock_C`` large,
    ``isotropy ~ 0``); a directionless bumpy field -> near ISOTROPIC (eigenvalues
    toward ``1/3``, ``isotropy`` high, ``woodcock_C`` small); a 1-D corrugation ->
    GIRDLE (``woodcock_K < 1``, ``eig3 ~ 0``).

    Guards: eigenvalues are floored by ``eps`` before the logs so near-degenerate
    fabrics never raise. ``woodcock_K`` is ``nan`` when ``ln(lambda2/lambda3) ~
    0`` (``lambda2 ~ lambda3``, e.g. a pure cluster, where the shape ratio is
    undefined). If no cell has a finite normal every value is ``nan``. NaN-safe
    and deterministic. Carries the module's claim firewall: a purely geometric
    eigen-analysis of the facet-orientation distribution, NOT a process,
    geologic, traversability, hazard or mission claim on any body.
    """
    nan = float("nan")
    out = {
        "eig1": nan, "eig2": nan, "eig3": nan,
        "woodcock_K": nan, "woodcock_C": nan, "isotropy": nan,
    }

    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if z.ndim != 2 or z.shape[0] < 2 or z.shape[1] < 2 or not np.isfinite(dx) or dx <= 0.0:
        return out                              # degenerate shape/spacing -> nan

    t = orientation_tensor(z, dx=dx)
    if not np.all(np.isfinite(t)):
        return out                              # no finite normals (all-NaN grid)

    w = np.clip(np.linalg.eigvalsh(t), 0.0, None)   # ascending, round-off clipped
    total = float(w.sum())
    if not np.isfinite(total) or total <= 0.0:
        return out
    w = w / total                                   # normalise to sum 1
    l3, l2, l1 = float(w[0]), float(w[1]), float(w[2])   # ascending -> l1>=l2>=l3

    out["eig1"], out["eig2"], out["eig3"] = l1, l2, l3
    out["isotropy"] = float(min(1.0, max(0.0, 3.0 * l3)))

    c1 = max(l1, _EPS)
    c2 = max(l2, _EPS)
    c3 = max(l3, _EPS)
    out["woodcock_C"] = float(np.log(c1 / c3))
    den = float(np.log(c2 / c3))
    if den > _EPS:
        out["woodcock_K"] = float(np.log(c1 / c2) / den)
    # else: lambda2 ~ lambda3 -> shape ratio undefined -> woodcock_K stays nan
    return out
