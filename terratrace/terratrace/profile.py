"""Fast, honest numeric QA / data-health report for a single elevation array.

These diagnostics are HEURISTIC and ADVISORY. They summarise one in-memory
elevation grid (float64, np.nan = nodata) so a caller can gate a freshly
fetched DEM or spot-check array quality *before* feature extraction. They are
descriptive statistics and cheap artefact detectors, not a verdict on terrain,
trafficability, or scientific validity.

The water proxy is deliberately blunt: it assumes sea level is approximately
`water_value` (default 0.0 m) *in the DEM's own vertical datum*. Products that
set open water to exactly 0 m (e.g. Copernicus) are caught, but a DEM on a
shifted datum, or genuine low-lying land near 0 m, will be mislabelled. Treat
`water_fraction` as a contamination hint, never as a water mask of record.

This module does no I/O: it imports neither rasterio nor requests and never
touches the filesystem. The caller already loaded the array (e.g. via
ingest.load_dem_array); profile.py only inspects what it is handed.
"""
from __future__ import annotations

import numpy as np

from . import masks

# Flags that make an array unfit for downstream use. SUSPICIOUS_CONSTANT and
# DEGENERATE_RELIEF are deliberately absent: a genuinely flat playa or salt pan
# looks suspicious yet is valid data, so we surface it without failing it.
_BLOCKING_FLAGS = frozenset({"ALL_NAN", "LOW_VALID_FRACTION", "WATER_CONTAMINATION"})


def profile_dem(z, posting_m=None, water_value=0.0, water_tol=1e-6):
    """Descriptive QA report for one elevation array; see the module docstring.

    Every output is a plain Python int/float/tuple so the dict is JSON-
    serialisable and cheap to compare in tests. nodata (np.nan) is excluded
    from each statistic via one explicit finite mask, so a NaN can never
    silently poison a reduction.
    """
    za = np.asarray(z, dtype="float64")
    finite = np.isfinite(za)                 # single source of truth for "valid"
    n_total = int(za.size)
    n_valid = int(finite.sum())
    valid_fraction = (n_valid / n_total) if n_total else 0.0

    # water_fraction must agree with the rest of the engine. The canonical
    # statistic is masks.zero_fraction (finite cells ~0 m); at the default
    # water_value we CALL it, so the WATER_CONTAMINATION flag below keys off the
    # very number the engine already gates on (zero_fraction > 0.6 -> BLOCKED).
    water_fraction = _water_fraction(za, finite, n_valid, water_value, water_tol)

    out = {
        "shape": tuple(int(d) for d in za.shape),
        "n_total": n_total,
        "n_valid": n_valid,
        "valid_fraction": float(valid_fraction),
        "nan_fraction": float(1.0 - valid_fraction) if n_total else 0.0,
        "water_fraction": float(water_fraction),
        "posting_m": (float(posting_m) if posting_m is not None else None),
    }
    if n_valid == 0:
        # No finite cells: moments/percentiles are undefined -> honest NaN;
        # constant_fraction is 0.0 (there is no modal value to be constant on).
        nan = float("nan")
        out.update(min=nan, max=nan, mean=nan, std=nan,
                   p1=nan, p5=nan, p50=nan, p95=nan, p99=nan,
                   relief=nan, constant_fraction=0.0)
        return out

    v = za[finite]                           # 1-D and guaranteed NaN-free
    p1, p5, p50, p95, p99 = (float(x) for x in np.percentile(v, [1, 5, 50, 95, 99]))
    # Robust relief: the 99th-1st percentile span shrugs off a lone MOLA spike
    # or a single filled void that a raw max-min would exaggerate.
    out.update(
        min=float(v.min()), max=float(v.max()),
        mean=float(v.mean()), std=float(v.std()),
        p1=p1, p5=p5, p50=p50, p95=p95, p99=p99,
        relief=float(p99 - p1),
        constant_fraction=_constant_fraction(v, n_valid, water_tol),
    )
    return out


def _water_fraction(za, finite, n_valid, water_value, water_tol):
    """Fraction of valid cells sitting at the sea-level proxy `water_value`.

    At water_value == 0.0 (sea level is 0 m in the datum, the usual case) we
    defer to masks.zero_fraction, so this is exactly the engine's existing
    water-contamination statistic and threshold. For a shifted datum we match
    its intent but anchor the test at water_value with |v - water_value| <= tol.
    Caveat: the 0.0 path uses NumPy's default isclose tolerance (as masks does);
    water_tol tunes only the non-zero-datum generalisation.
    """
    if water_value == 0.0:
        return masks.zero_fraction(za)       # identical to the engine's gate input
    if n_valid == 0:
        return float("nan")                  # undefined; mirror masks.zero_fraction
    v = za[finite]
    return float(np.count_nonzero(np.abs(v - water_value) <= water_tol)) / n_valid


def _constant_fraction(v, n_valid, water_tol):
    """Fraction of valid cells within `water_tol` of the single most common
    value. A cheap flat / fill-artefact detector: a constant fill (void filler
    or a quantised plateau) makes one value dominate. np.unique groups exact
    values; we then count everything within tol of that mode.
    """
    uniq, counts = np.unique(v, return_counts=True)
    mode = uniq[int(np.argmax(counts))]      # ties -> smallest value (first max)
    return float(np.count_nonzero(np.abs(v - mode) <= water_tol)) / n_valid


def quality_flags(prof, min_valid_fraction=0.5, max_water_fraction=0.6):
    """Advisory QA flags derived from a profile_dem() dict.

    Thresholds are named arguments so a caller can tune them. The return order
    is stable, but callers should test membership rather than position.
    """
    flags = []
    if prof["n_valid"] == 0:
        flags.append("ALL_NAN")
    if prof["valid_fraction"] < min_valid_fraction:
        flags.append("LOW_VALID_FRACTION")
    # Same statistic and threshold the engine uses elsewhere: zero_fraction>0.6.
    wf = prof["water_fraction"]
    if np.isfinite(wf) and wf > max_water_fraction:
        flags.append("WATER_CONTAMINATION")
    if prof["constant_fraction"] >= 0.99:    # nearly one value -> flat/fill-like
        flags.append("SUSPICIOUS_CONSTANT")
    rel = prof["relief"]
    if np.isfinite(rel) and rel < 1e-9:      # finite but ~0 span: no real relief
        flags.append("DEGENERATE_RELIEF")
    return flags


def summarize(z, posting_m=None, water_value=0.0,
              min_valid_fraction=0.5, max_water_fraction=0.6):
    """Profile an array, derive advisory flags, and return a single ok verdict.

    ok is False iff a BLOCKING flag is present (see _BLOCKING_FLAGS). Advisory
    flags alone never fail an array: a flat salt pan can be SUSPICIOUS_CONSTANT
    and DEGENERATE_RELIEF yet still be valid data. Thresholds pass straight
    through so they are tuned in one place.
    """
    prof = profile_dem(z, posting_m=posting_m, water_value=water_value)
    flags = quality_flags(prof, min_valid_fraction=min_valid_fraction,
                           max_water_fraction=max_water_fraction)
    ok = not any(f in _BLOCKING_FLAGS for f in flags)
    return {"profile": prof, "flags": flags, "ok": bool(ok)}
