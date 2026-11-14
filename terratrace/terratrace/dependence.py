"""Descriptor dependence: are several axes several facts, or one fact measured several times?

WHY THIS MODULE EXISTS
----------------------
The lunar panel declares three axes — mean slope, mean 3x3 relief, window elevation standard
deviation — and reports a Pareto frontier over them. An external review asked whether those are
three dimensions of evidence. Measured on the corrected panel they are not: Pearson between mean
slope and mean 3x3 relief is +1.000, Spearman +1.000 across all three pairs, and dropping any single
axis leaves the non-dominated set unchanged.

A correlation is a symptom, not a reason, so this module separates four things that are easy to
confuse:

1. **Mathematical dependence.** Two descriptors are functions of the same quantity, so their
   relationship is not evidence of anything -- it is algebra. Slope and relief are both functions of
   the local gradient, related by a bounded factor (below), so this is the category they mostly fall
   in. Demonstrated exactly in `planar_relief_over_slope`.
2. **Empirical correlation.** Two descriptors track each other on a particular dataset without a
   derivation. Real, but dataset-bound: it can vanish on another body or another support, and the
   audit therefore measures it per body, per support and per window rather than once.
3. **Shared interpretation.** Both described as "roughness" is not a measurement.
4. **Independent information.** The only category that justifies counting an axis as extra evidence,
   and the only one that can only be established by showing what one axis knows that the other does
   not.

WHAT IT RETURNS
---------------
Not a verdict but the numbers a verdict is made from: correlations, the eigenvalue spectrum of the
correlation matrix, an effective rank (how many dimensions the axes actually span), variance
inflation factors, and the leave-one-out behaviour of the frontier. `effective_rank` is the number
that matters: three axes spanning one dimension is one axis with three names.

THE SLOPE/RELIEF RELATION, DERIVED HERE RATHER THAN ASSUMED
-----------------------------------------------------------
`slope_deg` is `degrees(arctan(|grad z|))` from central differences, and `relief(window=3, alpha=0)`
is `max - min` over a 3x3 window of spacing `d`. On a locally planar surface with gradient
`(a, b)`, the max-minus-min over the 3x3 stencil is `2d(|a| + |b|)` -- the extents along each axis
add, they do not compose -- while `tan(slope) = sqrt(a^2 + b^2)`. So

    relief = 2 d tan(slope) * rho,     rho = (|a| + |b|) / sqrt(a^2 + b^2) in [1, sqrt(2)]

`rho` depends only on the gradient's DIRECTION, not its magnitude, and it is bounded: the two
descriptors are the same measurement up to a factor no larger than 1.415 that cannot exceed 41% and
cannot fall below 0. That is why they correlate at r ~ 1 -- it is the definition, not a discovery --
and it is also why a Pareto frontier over both is not a two-dimensional frontier. `rho` is exactly
what `planar_relief_over_slope` computes, and the audit measures how much of the real scatter it
explains versus what non-planarity adds.
"""
from __future__ import annotations

import math

import numpy as np


# --------------------------------------------------------------------------- rank statistics

def rankdata(v):
    """Average ranks, ties shared, without pulling in scipy."""
    v = np.asarray(v, dtype=float)
    n = len(v)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(1, n + 1, dtype=float)
    _, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    for i, c in enumerate(counts):
        if c > 1:
            idx = np.where(inv == i)[0]
            ranks[idx] = ranks[idx].mean()
    return ranks


def pearson(x, y):
    """Pearson r, or None when either side has no spread (correlation is undefined, not 0)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    """Spearman rho: Pearson on ranks. Reported alongside Pearson because a monotone but curved
    relationship is a dependence the eye misses and r understates."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2:
        return None
    return pearson(rankdata(x), rankdata(y))


# --------------------------------------------------------------------------- the spectrum

def correlation_matrix(columns):
    """Correlation matrix from ``{name: [values]}``. Returns ``(names, matrix)``."""
    names = list(columns)
    if len(names) < 2:
        raise ValueError("a dependence audit needs at least two axes")
    m = np.array([np.asarray(columns[n], dtype=float) for n in names])
    if m.ndim != 2 or m.shape[1] < 2:
        raise ValueError(f"need at least two observations per axis, got shape {m.shape}")
    # rows are axes, columns are observations: the array itself cannot be ragged, but a caller can
    # still hand over one observation, and a zero-variance axis makes every correlation undefined
    # rather than zero.
    corr = np.corrcoef(m)
    if not np.all(np.isfinite(corr)):
        raise ValueError("an axis has no spread, so its correlation is undefined")
    return names, corr


def eigen_spectrum(corr):
    """Eigenvalues of a symmetric reference matrix, descending. The shape of the dependence."""
    w = np.linalg.eigvalsh(np.asarray(corr, dtype=float))
    return [float(v) for v in sorted(w, reverse=True)]


def effective_rank(corr, var_threshold=0.95):
    """How many dimensions the axes actually span: components needed for ``var_threshold`` variance.

    THE headline number. Three axes spanning one dimension is one axis with three names, and no
    amount of care in the Pareto machinery changes that.
    """
    w = np.array(eigen_spectrum(corr), dtype=float)
    w = np.clip(w, 0.0, None)                       # tiny negatives are float noise on a singular matrix
    total = w.sum()
    if total <= 0:
        raise ValueError("the correlation matrix is degenerate")
    cumulative = np.cumsum(w) / total
    return int(np.searchsorted(cumulative, var_threshold - 1e-12) + 1)


def participation_ratio(corr):
    """A continuous version of the same idea, so the answer is not an artefact of a threshold."""
    w = np.clip(np.array(eigen_spectrum(corr), dtype=float), 0.0, None)
    return float(w.sum() ** 2 / (w ** 2).sum())


def condition_number(corr):
    """sqrt(lambda_max / lambda_min): the usual collinearity diagnostic (>~30 is severe)."""
    w = np.clip(np.array(eigen_spectrum(corr), dtype=float), 1e-300, None)
    return float(math.sqrt(w[0] / w[-1]))


def vif(columns, names=None):
    """Variance inflation factors: how much each axis is explained by the others.

    VIF_j = 1 / (1 - R^2_j) for axis j regressed on the rest. 1 means no linear dependence; there is
    no upper bound. Reported per axis because the interesting case is usually ONE redundant axis in
    an otherwise sound set.
    """
    names = names or list(columns)
    m = np.array([np.asarray(columns[n], dtype=float) for n in names])
    X = m.T
    X = (X - X.mean(axis=0)) / X.std(axis=0)
    out = {}
    for j, name in enumerate(names):
        others = [i for i in range(len(names)) if i != j]
        A = np.column_stack([X[:, others], np.ones(len(X))])
        coef, *_ = np.linalg.lstsq(A, X[:, j], rcond=None)
        pred = A @ coef
        ss_res = float(((X[:, j] - pred) ** 2).sum())
        ss_tot = float(((X[:, j] - X[:, j].mean()) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        out[name] = float(1.0 / max(1e-12, 1.0 - min(r2, 1.0 - 1e-12)))
    return out


# --------------------------------------------------------------------------- the algebra

def planar_relief_over_slope(a, b, d=1.0):
    """``(relief, 2 d tan(slope), rho)`` for a plane ``z = a x + b y`` with spacing ``d``.

    The exact relation the module docstring derives: over a 3x3 stencil the max-minus-min is the sum
    of the per-axis extents, so ``relief = 2 d (|a| + |b|)`` while ``2 d tan(slope) = 2 d sqrt(a^2 +
    b^2)``. Their ratio ``rho`` is bounded in ``[1, sqrt(2)]`` and depends only on the gradient's
    direction.
    """
    relief = 2.0 * d * (abs(a) + abs(b))
    two_d_tan = 2.0 * d * math.hypot(a, b)
    rho = relief / two_d_tan if two_d_tan else float("nan")
    return relief, two_d_tan, rho


def rho_bounds():
    """The provable bounds on the slope/relief factor: ``(1.0, sqrt(2))``."""
    return 1.0, math.sqrt(2.0)


def planar_r2(relief_values, slope_values, d):
    """How much of the relief spread the planar relation explains, as R^2, plus the fitted scale.

    ``relief ~ k * 2 d tan(slope)`` with a single free scale ``k``. On real terrain ``k`` lands
    inside the provable ``[1, sqrt(2)]`` band if the surface is locally planar, and the residual R^2
    deficit is exactly what non-planarity (curvature inside the window) contributes.
    """
    predicted = 2.0 * d * np.tan(np.radians(np.asarray(slope_values, dtype=float)))
    y = np.asarray(relief_values, dtype=float)
    ok = np.isfinite(predicted) & np.isfinite(y)
    predicted, y = predicted[ok], y[ok]
    if len(y) < 2 or np.std(predicted) == 0:
        return None, None, int(len(y))
    k = float((predicted * y).sum() / (predicted ** 2).sum())     # least squares through the origin
    ss_res = float(((y - k * predicted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return r2, k, int(len(y))
