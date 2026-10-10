"""Map-scale terrain morphology features.

Every feature declares its physical window and returns values whose scale
is interpretable. None of these features estimates mechanical roughness,
rock-scale obstacles, traction, or rover behaviour.
"""
from __future__ import annotations

import warnings

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def slope_deg(z, dx=1.0, dy=1.0):
    """Local slope magnitude in degrees from a projected elevation grid.

    For a plane z = a*x + b*y the result is arctan(sqrt(a^2+b^2)).
    """
    if dx <= 0 or dy <= 0:
        raise ValueError("dx and dy must be positive metres")
    gy, gx = np.gradient(np.asarray(z, dtype=float), dy, dx)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def _windows(z, window):
    if window % 2 == 0:
        raise ValueError("window must be odd")
    return sliding_window_view(np.asarray(z, dtype=float), (window, window))


def relief(z, window=3, alpha=0.0):
    """Local relief = upper minus lower quantile within each window.

    alpha is the tail fraction; alpha=0 gives max-min, alpha=0.05 gives a
    robust 5th-95th percentile relief. Returns the per-window relief map.

    Fast paths preserve EXACT results: with no NaNs the all-finite min/max
    (alpha=0) or a single two-quantile call (alpha>0) replace the much slower
    per-element ``nanquantile`` (q=1 is the max, q=0 the min, and ``quantile``
    equals ``nanquantile`` on finite data), so the output is unchanged.
    """
    if not 0.0 <= alpha < 0.5:
        raise ValueError("alpha must be in [0, 0.5)")
    if min(np.asarray(z).shape) < window:
        return np.array([np.nan])      # AOI too small for this window
    w = _windows(z, window)
    flat = w.reshape(w.shape[0], w.shape[1], -1)
    has_nan = bool(np.isnan(flat).any())
    if alpha == 0.0:
        if has_nan:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                return np.nanmax(flat, axis=-1) - np.nanmin(flat, axis=-1)
        return flat.max(axis=-1) - flat.min(axis=-1)
    if has_nan:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            hi = np.nanquantile(flat, 1.0 - alpha, axis=-1)
            lo = np.nanquantile(flat, alpha, axis=-1)
        return hi - lo
    lo, hi = np.quantile(flat, [alpha, 1.0 - alpha], axis=-1)
    return hi - lo


def ruggedness(z, window=3, dx=1.0, dy=1.0):
    """Detrended topographic ruggedness: RMS of residuals after removing a
    local best-fit plane within each window. A perfect plane returns ~0.
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    if min(np.asarray(z).shape) < window:
        return np.array([[np.nan]])    # AOI too small for this window
    w = _windows(z, window)
    nrow, ncol = w.shape[0], w.shape[1]
    # Local coordinates centred on the window, in metres.
    jj, ii = np.meshgrid(np.arange(window), np.arange(window))
    xx = (jj - window // 2) * dx
    yy = (ii - window // 2) * dy
    A = np.column_stack([xx.ravel(), yy.ravel(), np.ones(window * window)])
    pinv = np.linalg.pinv(A)
    out = np.full((nrow, ncol), np.nan)
    for r in range(nrow):
        block = w[r].reshape(ncol, -1)  # (ncol, window*window)
        if np.isnan(block).any():
            for c in range(ncol):
                vals = block[c]
                if np.isnan(vals).any():
                    continue
                coeffs = pinv @ vals
                resid = vals - A @ coeffs
                out[r, c] = np.sqrt(np.mean(resid ** 2))
            continue
        coeffs = (pinv @ block.T)          # (3, ncol)
        resid = block.T - A @ coeffs       # (window*window, ncol)
        out[r] = np.sqrt(np.mean(resid ** 2, axis=0))
    return out


def low_slope_connectivity(slope, threshold_deg, valid_mask=None):
    """Fraction of valid cells in the largest 4-connected component whose
    slope is at or below the threshold. A map-scale corridor statistic, not
    a route guarantee.
    """
    slope = np.asarray(slope, dtype=float)
    if valid_mask is None:
        valid_mask = ~np.isnan(slope)
    passable = valid_mask & (slope <= threshold_deg)
    n_valid = int(valid_mask.sum())
    if n_valid == 0:
        return 0.0, 0
    largest = _largest_component(passable)
    return largest / n_valid, largest


def _largest_component(mask):
    seen = np.zeros_like(mask, dtype=bool)
    rows, cols = mask.shape
    best = 0
    for sr in range(rows):
        for sc in range(cols):
            if not mask[sr, sc] or seen[sr, sc]:
                continue
            size = 0
            stack = [(sr, sc)]
            seen[sr, sc] = True
            while stack:
                r, c = stack.pop()
                size += 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and mask[nr, nc] and not seen[nr, nc]:
                        seen[nr, nc] = True
                        stack.append((nr, nc))
            best = max(best, size)
    return best


def aspect_dispersion(z, dx=1.0, dy=1.0):
    """Gradient-magnitude-weighted circular variance of terrain aspect in [0, 1].

    0 = a single dominant downslope direction (e.g. a planar slope) or flat
    ground; values near 1 mean aspect is near-isotropic. Weighting by slope
    magnitude prevents near-flat pixels (whose gradient direction is numerical
    noise) from inflating the dispersion.
    """
    if dx <= 0 or dy <= 0:
        raise ValueError("dx and dy must be positive metres")
    gy, gx = np.gradient(np.asarray(z, dtype=float), dy, dx)
    mag = np.hypot(gx, gy)
    aspect = np.arctan2(gy, gx)
    finite = np.isfinite(aspect) & np.isfinite(mag)
    if finite.sum() == 0:
        return float("nan")
    w = mag[finite]
    wsum = float(w.sum())
    if wsum <= 1e-12:          # perfectly flat: no directional information
        return 0.0
    a = aspect[finite]
    r = np.hypot(np.sum(w * np.cos(a)), np.sum(w * np.sin(a))) / wsum
    return float(1.0 - r)


def hypsometric_integral(z, alpha=0.01):
    """Elevation-relief ratio (mean - lo) / (hi - lo) in [0, 1].

    An approximation to the hypsometric integral. lo/hi use robust quantiles
    (default 1st/99th percentile) rather than single-pixel min/max, so one MOLA
    spike or filled void does not distort it. NaN if the surface is flat.
    """
    v = np.asarray(z, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    lo = float(np.percentile(v, alpha * 100.0))
    hi = float(np.percentile(v, (1.0 - alpha) * 100.0))
    if hi - lo < 1e-12:
        return float("nan")
    return float(min(1.0, max(0.0, (float(np.mean(v)) - lo) / (hi - lo))))


def tpi_dispersion(z, window=5):
    """Dispersion (std) of the Topographic Position Index: each cell's height
    minus its local window mean. 0 on a plane or flat ground; larger where
    ridges/valleys make cells sit above/below their surroundings. A map-scale
    landform-organisation descriptor; not a mechanical property.
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    za = np.asarray(z, dtype=float)
    if min(za.shape) < window:
        return float("nan")
    w = _windows(za, window)
    flat = w.reshape(w.shape[0], w.shape[1], -1)
    k = window // 2
    center = za[k:za.shape[0] - k, k:za.shape[1] - k]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean = np.nanmean(flat, axis=-1)
    tpi = center - mean
    tpi = tpi[np.isfinite(tpi)]
    return float(np.std(tpi)) if tpi.size else float("nan")


def _zt_coeffs(z, L):
    """Zevenbergen & Thorne (1987) local quadratic coefficients on a 3x3 window.

    Returns interior arrays (D, E, F, G, H) for the surface
    z = D x^2 + E y^2 + F xy + G x + H y + ...  fitted at each node with node
    spacing L. D,E are the second x/y derivatives /2; G,H the first derivatives.
    NaNs propagate naturally (any NaN neighbour -> NaN coefficient).
    """
    z = np.asarray(z, dtype=float)
    z1, z2, z3 = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    z4, z5, z6 = z[1:-1, :-2], z[1:-1, 1:-1], z[1:-1, 2:]
    z7, z8, z9 = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    D = ((z4 + z6) / 2.0 - z5) / (L * L)
    E = ((z2 + z8) / 2.0 - z5) / (L * L)
    F = (-z1 + z3 + z7 - z9) / (4.0 * L * L)
    G = (-z4 + z6) / (2.0 * L)
    H = (z2 - z8) / (2.0 * L)
    return D, E, F, G, H


def profile_curvature(z, dx=1.0):
    """Curvature in the slope direction (Zevenbergen-Thorne), per interior cell.

    Convex-up profiles are negative, concave positive (ZT convention). Zero on a
    plane; constant -2a on a paraboloid z=a(x^2+y^2). Undefined where the surface
    is locally flat (slope ~ 0) -> returned as 0 there."""
    if min(np.asarray(z).shape) < 3:
        return np.array([[np.nan]])
    D, E, F, G, H = _zt_coeffs(z, dx)
    denom = G * G + H * H
    with np.errstate(invalid="ignore", divide="ignore"):
        kp = -2.0 * (D * G * G + E * H * H + F * G * H) / denom
    return np.where(denom > 1e-12, kp, 0.0)


def plan_curvature(z, dx=1.0):
    """Curvature across the slope (contour curvature, Zevenbergen-Thorne).

    Zero on a plane; constant +2a on a paraboloid z=a(x^2+y^2). Flat cells -> 0."""
    if min(np.asarray(z).shape) < 3:
        return np.array([[np.nan]])
    D, E, F, G, H = _zt_coeffs(z, dx)
    denom = G * G + H * H
    with np.errstate(invalid="ignore", divide="ignore"):
        kc = 2.0 * (D * H * H + E * G * G - F * G * H) / denom
    return np.where(denom > 1e-12, kc, 0.0)


def mean_curvature(z, dx=1.0):
    """ZT general curvature -2(D+E): defined everywhere (no slope division).

    Zero on any plane; constant -4a on a paraboloid z=a(x^2+y^2); sign flips for a
    dome. A robust, division-free convexity descriptor."""
    if min(np.asarray(z).shape) < 3:
        return np.array([[np.nan]])
    D, E, _, _, _ = _zt_coeffs(z, dx)
    return -2.0 * (D + E)


def vector_ruggedness(z, window=3, dx=1.0, dy=1.0):
    """Vector Ruggedness Measure (Sappington et al., 2007), per interior window.

    Each cell's unit surface normal (-dz/dx, -dz/dy, 1)/|.| is summed over the
    window; VRM = 1 - |resultant|/N. It is 0 for a plane (all normals parallel,
    even if steep) and rises toward 1 as the surface becomes rugged -- a ruggedness
    measure that, unlike slope spread, is decoupled from the mean slope. In [0, 1].
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    za = np.asarray(z, dtype=float)
    if min(za.shape) < window:
        return np.array([[np.nan]])
    gy, gx = np.gradient(za, dy, dx)
    norm = np.sqrt(gx * gx + gy * gy + 1.0)
    nx, ny, nz = -gx / norm, -gy / norm, 1.0 / norm
    n = window * window
    sx = _windows(nx, window).reshape(nx.shape[0] - window + 1, -1, n).sum(axis=-1)
    sy = _windows(ny, window).reshape(ny.shape[0] - window + 1, -1, n).sum(axis=-1)
    sz = _windows(nz, window).reshape(nz.shape[0] - window + 1, -1, n).sum(axis=-1)
    resultant = np.sqrt(sx * sx + sy * sy + sz * sz)
    return 1.0 - resultant / n


def structure_function(z, lags=(1, 2, 4, 8), dx=1.0):
    """RMS elevation difference at each lag (an isotropic structure function).

    Returns {lag_metres: rms_height_difference} using horizontal and vertical
    pixel offsets pooled. For a self-affine surface rms ~ lag^H; it is the raw
    material for a roughness-vs-scale (Hurst) analysis. NaNs are ignored.
    """
    za = np.asarray(z, dtype=float)
    out = {}
    for h in lags:
        h = int(h)
        if h <= 0 or h >= min(za.shape):
            continue
        dxdiff = za[:, h:] - za[:, :-h]
        dydiff = za[h:, :] - za[:-h, :]
        pooled = np.concatenate([dxdiff.ravel(), dydiff.ravel()])
        pooled = pooled[np.isfinite(pooled)]
        if pooled.size:
            out[float(h * dx)] = float(np.sqrt(np.mean(pooled ** 2)))
    return out


def hurst_exponent(z, lags=(1, 2, 4, 8), dx=1.0):
    """Roughness scaling exponent: slope of log(RMS diff) vs log(lag), clamped to
    [0, 1]. H near 0 is rough/white-noise-like, near 1 is smooth/long-correlated.
    A single-number summary of how roughness grows with scale; NaN if undefined.
    """
    sf = structure_function(z, lags=lags, dx=dx)
    pts = [(L, v) for L, v in sf.items() if v > 1e-12 and np.isfinite(v)]
    if len(pts) < 2:
        return float("nan")
    logs = np.log(np.array([p[0] for p in pts]))
    logv = np.log(np.array([p[1] for p in pts]))
    slope = np.polyfit(logs, logv, 1)[0]
    return float(min(1.0, max(0.0, slope)))


# --- added analysis-layer descriptors (append-only; existing features above
#     are untouched: rugosity / TRI / TPI map / landform mix) ------------------

def surface_area_ratio(z, dx=1.0, dy=1.0):
    """Surface-area ratio (rugosity): true 3-D surface area over planimetric area.

    Computed per cell from the local gradient as
    ``sqrt(1 + (dz/dx)^2 + (dz/dy)^2)`` using ``np.gradient`` (same convention
    as :func:`slope_deg`). It is exactly 1.0 on flat ground and, on a tilted
    plane z = a*x + b*y, the positive constant ``sqrt(1 + a^2 + b^2)`` which
    equals ``sec(slope)`` (> 1). Returns the full-resolution map, with NaN
    wherever the gradient is undefined (non-finite neighbours propagate).
    """
    if dx <= 0 or dy <= 0:
        raise ValueError("dx and dy must be positive metres")
    gy, gx = np.gradient(np.asarray(z, dtype=float), dy, dx)
    return np.sqrt(1.0 + gx * gx + gy * gy)


def terrain_ruggedness_index(z, window=3):
    """Terrain Ruggedness Index (Riley et al., 1999), per interior cell.

    ``TRI = sqrt(mean((neighbour - centre)^2))`` over the (window x window)
    neighbourhood -- the RMS elevation difference between a cell and the cells
    around it (the centre's own term is zero). It is 0 on perfectly flat or
    CONSTANT ground and grows with roughness. Unlike detrended
    :func:`ruggedness` it is NOT zero on a tilted plane: neighbours differ from
    the centre there, so a plane yields a positive constant. NaN-aware
    (non-finite neighbours are ignored); returns the interior map, or
    ``np.array([[np.nan]])`` when the AOI is smaller than ``window``.
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    za = np.asarray(z, dtype=float)
    if min(za.shape) < window:
        return np.array([[np.nan]])        # AOI too small for this window
    w = _windows(za, window)
    k = window // 2
    center = w[:, :, k, k][:, :, None, None]
    sq = (w - center) ** 2
    flat = sq.reshape(w.shape[0], w.shape[1], -1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        msd = np.nanmean(flat, axis=-1)
    return np.sqrt(msd)


def tpi_map(z, window=5):
    """Topographic Position Index map: each cell minus its local window mean.

    This is the per-cell field whose dispersion :func:`tpi_dispersion`
    summarises (``tpi_dispersion`` returns the std of this map's finite
    values). It is 0 on a plane or flat ground -- a symmetric window mean
    equals the planar centre value -- and is positive on local highs (ridges)
    and negative in local lows (valleys). NaN-aware via ``nanmean`` over each
    window; returns the interior map, or ``np.array([[np.nan]])`` when the AOI
    is smaller than ``window``.
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    za = np.asarray(z, dtype=float)
    if min(za.shape) < window:
        return np.array([[np.nan]])        # AOI too small for this window
    w = _windows(za, window)
    flat = w.reshape(w.shape[0], w.shape[1], -1)
    k = window // 2
    center = za[k:za.shape[0] - k, k:za.shape[1] - k]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean = np.nanmean(flat, axis=-1)
    return center - mean


def landform_fraction(z, window=5, k=1.0):
    """Landform mix from the TPI map: ridge / valley / flat area fractions.

    Classifies each finite cell of :func:`tpi_map` by its TPI relative to ``k``
    standard deviations ``s`` of that map: ridge (``tpi > k*s``), valley
    (``tpi < -k*s``), otherwise slope/flat (``|tpi| <= k*s``). Returns
    ``{"ridge": f, "valley": f, "flat": f}`` whose fractions sum to 1.0 over the
    finite cells -- a compact landform-organisation descriptor. If there are no
    finite cells or the TPI map is degenerate (``s`` ~ 0, e.g. a plane or flat
    ground) all three fractions are 0.0.
    """
    tpi = np.asarray(tpi_map(z, window=window), dtype=float)
    finite = tpi[np.isfinite(tpi)]
    n = int(finite.size)
    if n == 0:
        return {"ridge": 0.0, "valley": 0.0, "flat": 0.0}
    s = float(np.std(finite))
    if s <= 1e-12:                         # no landform structure (plane/flat)
        return {"ridge": 0.0, "valley": 0.0, "flat": 0.0}
    thr = k * s
    ridge = float(np.count_nonzero(finite > thr)) / n
    valley = float(np.count_nonzero(finite < -thr)) / n
    flat = float(np.count_nonzero(np.abs(finite) <= thr)) / n
    return {"ridge": ridge, "valley": valley, "flat": flat}
