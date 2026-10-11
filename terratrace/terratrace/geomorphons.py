"""Geomorphon landform classification (pure NumPy, map-scale morphology).

Implements the line-of-sight *geomorphon* method of Jasiewicz & Stepinski
(2013, Geomorphology 182:147-156). For every cell and each of 8 directions a
line of sight is cast outward, stepping ``k = skip+1 .. search`` cells. For a
neighbour at step ``k`` the horizontal distance is ``h = k*dx`` (cardinal
directions) or ``h = k*dx*sqrt(2)`` (diagonals) and the line-of-sight elevation
angle is ``a = degrees(atan2(z_neighbour - z_centre, h))``. Per direction ``d``:

* ``zenith_angle(d) = 90 - max_over_ray(a)``
* ``nadir_angle(d)  = 90 + min_over_ray(a)``

Each direction is reduced to a ternary element with a flatness threshold
``flat_deg`` (degrees, default 1.0):

* ``0``  (flat)            if ``abs(zenith_angle - nadir_angle) <= flat_deg``
* ``+1`` (neighbour LOWER / terrain falls) if ``zenith_angle > nadir_angle``
* ``-1`` (neighbour HIGHER / terrain rises) otherwise

For each cell ``n_plus`` counts the ``+1`` directions and ``n_minus`` the ``-1``
directions over the valid directions (up to 8). Rays truncate at the array
edges -- the grid is padded with NaN by ``search`` and NaN samples are ignored
via ``np.fmax`` / ``np.fmin`` -- and any direction with no valid sample is
dropped. The method is relief-invariant (it depends only on elevation
DIFFERENCES) and is evaluated with vectorised array shifts: there is no per-cell
Python loop over the grid, so a 96x96 call runs in well under a second.

Landform names follow the geomorphon scheme of Jasiewicz & Stepinski (2013). The
ternary line-of-sight signature (n_plus, n_minus) is computed exactly as in that
method; the reduction to the 10 named common forms uses an explicit,
antisymmetric rule validated against canonical synthetic landforms (it is not a
verbatim copy of any particular GIS lookup table).

The 10-class reduction is deliberately antisymmetric: swapping ``n_plus`` <->
``n_minus`` swaps PEAK<->PIT, RIDGE<->VALLEY, SHOULDER<->FOOTSLOPE and
SPUR<->HOLLOW, and fixes FLAT and SLOPE.

Claim firewall: this is MORPHOLOGY classification only -- it names the local
line-of-sight SHAPE of the surface (peak, ridge, slope, valley, pit, ...). It is
NOT traversability, NOT hazard, and NOT geologic-unit identification, and it
asserts nothing about what the ground is made of or whether it can be driven on.
"""
from __future__ import annotations

import numpy as np

FORM_NAMES = ("flat", "peak", "ridge", "shoulder", "spur",
              "slope", "hollow", "footslope", "valley", "pit")

# Integer form code == index into FORM_NAMES (0=flat .. 9=pit).
(_FLAT, _PEAK, _RIDGE, _SHOULDER, _SPUR,
 _SLOPE, _HOLLOW, _FOOTSLOPE, _VALLEY, _PIT) = range(10)

# The 8 line-of-sight directions as (di, dj, is_diagonal), ordered E, NE, N,
# NW, W, SW, S, SE. The order does not affect the result -- the counts are
# direction-order independent -- which is what makes the signature robust to
# whole-grid rotation.
_DIRS = ((0, 1, False), (-1, 1, True), (-1, 0, False), (-1, -1, True),
         (0, -1, False), (1, -1, True), (1, 0, False), (1, 1, True))

_SQRT2 = np.sqrt(2.0)


def _scan(z, dx, search, skip, flat_deg):
    """Core vectorised ray scan shared by every public entry point.

    Returns ``(n_plus, n_minus, valid)``: ``n_plus`` / ``n_minus`` are int64
    (R, C) per-cell direction counts and ``valid`` is a boolean (R, C) mask of
    cells that have a finite centre AND at least one direction with a valid
    line-of-sight sample. A NaN-centred cell -- or a finite cell whose every ray
    runs straight off the grid -- is therefore not classified.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    if dx <= 0:
        raise ValueError("dx must be positive metres")
    search = int(search)
    skip = int(skip)
    if search < 1:
        raise ValueError("search must be >= 1")
    if skip < 0:
        raise ValueError("skip must be >= 0")

    rows, cols = z.shape
    pad = search
    padded = np.full((rows + 2 * pad, cols + 2 * pad), np.nan)
    padded[pad:pad + rows, pad:pad + cols] = z

    n_plus = np.zeros((rows, cols), dtype=np.int64)
    n_minus = np.zeros((rows, cols), dtype=np.int64)
    n_valid_dir = np.zeros((rows, cols), dtype=np.int64)
    kstart = skip + 1
    for di, dj, is_diag in _DIRS:
        max_a = np.full((rows, cols), np.nan)
        min_a = np.full((rows, cols), np.nan)
        base_h = dx * (_SQRT2 if is_diag else 1.0)
        for k in range(kstart, search + 1):
            r0 = pad + di * k
            c0 = pad + dj * k
            neighbour = padded[r0:r0 + rows, c0:c0 + cols]
            angle = np.degrees(np.arctan2(neighbour - z, base_h * k))
            # fmax / fmin propagate the finite operand, skipping NaN samples.
            max_a = np.fmax(max_a, angle)
            min_a = np.fmin(min_a, angle)
        # zenith - nadir = (90 - max_a) - (90 + min_a) = -(max_a + min_a).
        diff = (90.0 - max_a) - (90.0 + min_a)
        valid_d = ~np.isnan(diff)
        n_valid_dir += valid_d
        n_plus += valid_d & (diff > flat_deg)
        n_minus += valid_d & (diff < -flat_deg)

    valid = np.isfinite(z) & (n_valid_dir >= 1)
    return n_plus, n_minus, valid


def ternary_counts(z, dx=1.0, search=10, skip=0, flat_deg=1.0):
    """Per-cell ternary direction counts ``(n_plus, n_minus)``.

    Both returned arrays are int ndarrays shaped like ``z``: ``n_plus`` is the
    number of directions in which terrain falls (neighbour lower) and
    ``n_minus`` the number in which it rises (neighbour higher), each over the
    valid directions. NaN-centred cells yield ``(0, 0)`` (no valid direction);
    use :func:`landforms` / :func:`composition` for validity-aware output.
    """
    n_plus, n_minus, _ = _scan(z, dx, search, skip, flat_deg)
    return n_plus, n_minus


def classify_forms(n_plus, n_minus):
    """Vectorised ``(n_plus, n_minus)`` -> int form-code map (FORM_NAMES index).

    Pure boolean-mask assignment -- no Python loop over cells. The mapping is the
    exact antisymmetric 10-class rule documented on the module and returns the
    FORM_NAMES index (0=flat .. 9=pit) for EVERY count pair. Cell validity (NaN
    handling) is layered on by :func:`landforms`, not here.
    """
    p = np.asarray(n_plus)
    m = np.asarray(n_minus)
    code = np.full(np.broadcast(p, m).shape, _FLAT, dtype=np.int64)

    flat = (p <= 1) & (m <= 1)
    down = (~flat) & (m == 0)                 # m == 0, so p >= 2
    up = (~flat) & (p == 0) & (m != 0)        # p == 0, so m >= 2
    both = (~flat) & (p != 0) & (m != 0)      # p >= 1 and m >= 1
    adiff = np.abs(p - m)

    code[down & (p >= 7)] = _PEAK
    code[down & (p >= 4) & (p < 7)] = _RIDGE
    code[down & (p < 4)] = _SHOULDER          # p in 2..3

    code[up & (m >= 7)] = _PIT
    code[up & (m >= 4) & (m < 7)] = _VALLEY
    code[up & (m < 4)] = _FOOTSLOPE           # m in 2..3

    code[both & (adiff <= 1)] = _SLOPE
    code[both & (adiff > 1) & (p > m)] = _SPUR
    code[both & (adiff > 1) & (p < m)] = _HOLLOW
    return code


def classify_form(p, m):
    """Classify a single ``(n_plus, n_minus)`` pair -> form NAME (str).

    Thin scalar wrapper over :func:`classify_forms` so both share one rule.
    """
    code = int(classify_forms(np.array([[int(p)]]), np.array([[int(m)]]))[0, 0])
    return FORM_NAMES[code]
def landforms(z, dx=1.0, search=10, skip=0, flat_deg=1.0):
    """Per-cell geomorphon form-code map (int, same shape as ``z``).

    Each value is the FORM_NAMES index (0=flat .. 9=pit). Cells that cannot be
    classified -- NaN centre, or no valid line-of-sight direction -- are -1.
    """
    n_plus, n_minus, valid = _scan(z, dx, search, skip, flat_deg)
    code = classify_forms(n_plus, n_minus)
    code[~valid] = -1
    return code


def composition(z, dx=1.0, search=10, skip=0, flat_deg=1.0):
    """Area fraction of each landform over the classified (valid) cells.

    Returns ``{form_name: fraction}`` for ALL ten forms (forms that are absent
    map to 0.0), summing to ~1.0. An empty or fully-degenerate grid yields all
    zeros. Being relief-invariant, ``composition(z) == composition(z + c)`` for
    any constant ``c``.
    """
    n_plus, n_minus, valid = _scan(z, dx, search, skip, flat_deg)
    code = classify_forms(n_plus, n_minus)
    codes_valid = code[valid]
    total = int(codes_valid.size)
    if total:
        counts = np.bincount(codes_valid, minlength=len(FORM_NAMES))
    else:
        counts = np.zeros(len(FORM_NAMES), dtype=np.int64)
    return {name: (float(counts[i]) / total if total else 0.0)
            for i, name in enumerate(FORM_NAMES)}


def spectrum(z, dx=1.0, search=10, skip=0, flat_deg=1.0):
    """Normalised 9x9 histogram of ``(n_plus, n_minus)`` over valid cells.

    ``spectrum(...)[p][m]`` is the fraction of classified cells with
    ``n_plus == p`` and ``n_minus == m`` (both range 0..8). The impossible
    region ``p + m > 8`` is forced to 0. Sums to ~1.0 for a non-degenerate
    surface (0 for an empty/degenerate grid).
    """
    n_plus, n_minus, valid = _scan(z, dx, search, skip, flat_deg)
    hist = np.zeros((9, 9), dtype=float)
    pv = n_plus[valid]
    mv = n_minus[valid]
    keep = (pv >= 0) & (pv <= 8) & (mv >= 0) & (mv <= 8) & (pv + mv <= 8)
    np.add.at(hist, (pv[keep], mv[keep]), 1.0)
    total = hist.sum()
    if total > 0:
        hist /= total
    return hist


def geomorphon_signature(z, dx=1.0, search=10, skip=0, flat_deg=1.0):
    """Compact, JSON-friendly summary of a tile's geomorphon structure.

    Returns ``{"composition": {name: fraction}, "spectrum": 9x9 nested list,
    "dominant_form": name}``. ``dominant_form`` is the most common landform over
    the valid cells, with ties broken by FORM_NAMES order; it is ``"flat"`` for
    an empty/degenerate grid.
    """
    comp = composition(z, dx=dx, search=search, skip=skip, flat_deg=flat_deg)
    spec = spectrum(z, dx=dx, search=search, skip=skip, flat_deg=flat_deg)
    counts = [comp[name] for name in FORM_NAMES]
    dominant = FORM_NAMES[int(np.argmax(counts))]
    return {
        "composition": comp,
        "spectrum": spec.tolist(),
        "dominant_form": dominant,
    }



