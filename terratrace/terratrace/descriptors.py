"""Full geomorphometric descriptor bank for a single elevation tile.

This module is a *non-destructive aggregation layer* over
:mod:`terratrace.features`. It does NOT change the study pipeline or any
decision the engine makes: it is a read-only analysis surface -- the
"give me all the geomorphometry of this tile" API for analysts and for a
future, richer decision mode. It assembles the engine's map-valued and
scalar features into one JSON-serialisable dict, summarising every
map-valued feature down to distribution statistics (mean / std / p10 /
p50 / p90) so the whole bank is a flat bag of numbers.

Claim firewall (inherited from the feature layer): every number here is a
map-scale morphology descriptor. None of them estimates traversability,
mechanical roughness, traction, rock-scale obstacles, or rover / mission
behaviour. Summarising a map to five quantiles adds no such claim.
"""
from __future__ import annotations

import numpy as np

from . import features

_SUMMARY_KEYS = ("mean", "std", "p10", "p50", "p90")


def summarize_map(arr):
    """Summarise a (possibly map-valued) array to distribution statistics.

    Returns ``{mean, std, p10, p50, p90}`` as plain Python floats, computed
    over the FINITE values only (NaN / inf aware). If there are no finite
    values the five keys are all ``float('nan')``. The input is never
    mutated.
    """
    v = np.asarray(arr, dtype=float).ravel()
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {k: float("nan") for k in _SUMMARY_KEYS}
    p10, p50, p90 = np.percentile(v, [10.0, 50.0, 90.0])
    return {
        "mean": float(np.mean(v)),
        "std": float(np.std(v)),
        "p10": float(p10),
        "p50": float(p50),
        "p90": float(p90),
    }


def descriptor_bank(z, dx=1.0, window=5):
    """Compute the full map-scale morphology descriptor bank for one tile.

    Map-valued features (slope, relief, ruggedness, the three curvatures and
    vector ruggedness) are summarised with :func:`summarize_map`; the rest are
    scalar descriptors. ``structure_function``'s float lag keys are turned into
    strings so the whole bank is JSON-serialisable -- every value is a plain
    float or a dict of plain floats.

    ``dx`` is the (square) pixel size in metres and ``window`` the odd window
    used by the window-based features (relief / ruggedness / tpi); vector
    ruggedness keeps its own 3x3 window by construction.

    These are map-scale morphology descriptors only. No traversability,
    mechanical, or mission claim is implied by any value in the bank.
    """
    z = np.asarray(z, dtype=float)
    return {
        # --- map-valued features, summarised to distribution statistics ---
        "slope": summarize_map(features.slope_deg(z, dx, dx)),
        "relief": summarize_map(features.relief(z, window=window, alpha=0.0)),
        "ruggedness": summarize_map(features.ruggedness(z, window=window, dx=dx, dy=dx)),
        "profile_curvature": summarize_map(features.profile_curvature(z, dx=dx)),
        "plan_curvature": summarize_map(features.plan_curvature(z, dx=dx)),
        "mean_curvature": summarize_map(features.mean_curvature(z, dx=dx)),
        "vector_ruggedness": summarize_map(features.vector_ruggedness(z, window=3, dx=dx, dy=dx)),
        # --- scalar descriptors ---
        "aspect_dispersion": float(features.aspect_dispersion(z, dx=dx, dy=dx)),
        "hypsometric_integral": float(features.hypsometric_integral(z)),
        "tpi_dispersion": float(features.tpi_dispersion(z, window=window)),
        "hurst_exponent": float(features.hurst_exponent(z, dx=dx)),
        # --- roughness-vs-scale curve, string-keyed for JSON ---
        "structure_function": {
            str(lag): float(rms)
            for lag, rms in features.structure_function(z, dx=dx).items()
        },
        # --- added analysis-layer descriptors (append-only; NOT used by the
        #     study decision -- a read-only extension of the bank) ---
        "surface_area_ratio": summarize_map(features.surface_area_ratio(z, dx, dx)),
        "terrain_ruggedness_index": summarize_map(
            features.terrain_ruggedness_index(z, window=window)),
        "landform_fraction": features.landform_fraction(z, window=window),
    }


# Fixed field order for :func:`bank_vector`; documented so callers can rely
# on positional meaning for quick tile-to-tile comparison.
BANK_VECTOR_FIELDS = (
    "slope.p50",
    "ruggedness.p50",
    "mean_curvature.std",
    "vector_ruggedness.p50",
    "aspect_dispersion",
    "hypsometric_integral",
    "hurst_exponent",
)


def bank_vector(z, dx=1.0, window=5):
    """Return the headline scalars of :func:`descriptor_bank` as an ordered tuple.

    The field order is fixed by :data:`BANK_VECTOR_FIELDS`:
    ``(slope p50, ruggedness p50, mean_curvature std, vector_ruggedness p50,
    aspect_dispersion, hypsometric_integral, hurst_exponent)``. It is a
    deterministic, plain-float convenience for quick tile-to-tile comparison and
    carries the same claim firewall as the bank: map-scale morphology only.
    """
    bank = descriptor_bank(z, dx=dx, window=window)
    return (
        bank["slope"]["p50"],
        bank["ruggedness"]["p50"],
        bank["mean_curvature"]["std"],
        bank["vector_ruggedness"]["p50"],
        bank["aspect_dispersion"],
        bank["hypsometric_integral"],
        bank["hurst_exponent"],
    )
