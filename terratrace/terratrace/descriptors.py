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

from . import (features, openness, geomorphons, spectral, anisotropy,
               kh_roughness, iwahashi_pike, drainage)

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

    Two line-of-sight landform sub-dicts are appended (append-only analysis
    layer, NOT read by any decision): ``"openness"`` -- the
    :func:`terratrace.openness.openness_signature` dict (positive/negative
    openness median and p10/p90, Yokoyama 2002) -- and ``"geomorphons"`` -- the
    :func:`terratrace.geomorphons.geomorphon_signature` dict (``composition``
    fractions over the 10 forms, the normalised 9x9 ``spectrum`` as a nested
    list, and the ``dominant_form`` name; Jasiewicz & Stepinski 2013). Both are
    computed at the bank's ``dx`` and stay JSON-serialisable (plain floats /
    nested lists of floats / a form name).

    Two scale/fabric sub-dicts are appended likewise (append-only analysis
    layer, NOT read by any decision): ``"spectral"`` -- the
    :func:`terratrace.spectral.spectral_signature` dict (log-log
    ``spectral_slope``, ``total_power``, ``roughness_rms``,
    ``peak_wavelength_m`` and the band RMS values
    ``rough_long``/``rough_mid``/``rough_short``; radially-averaged 2-D PSD) --
    and ``"anisotropy"`` -- the
    :func:`terratrace.anisotropy.anisotropy_signature` dict (directional-fabric
    ``strength``, ``orientation_deg``, ``isotropy`` and ``mean_roughness``;
    structure-function fabric). Both are computed at the bank's ``dx`` and are
    flat dicts of plain floats (``nan`` where a descriptor is undefined, e.g. a
    degenerate / perfectly flat tile), so they stay JSON-serialisable.

    A differential-slope baseline-roughness sub-dict is appended likewise
    (append-only analysis layer, NOT read by any decision): ``"kh_roughness"`` --
    the :func:`terratrace.kh_roughness.kh_roughness_signature` dict (the
    ``baseline_roughness_fine`` / ``baseline_roughness_coarse`` medians of the
    absolute differential slope in degrees, the ascending ``profile`` of
    roughness vs baseline, and its ``profile_loglog_slope``). This is a gridded
    adaptation of the Kreslavsky & Head (2000) MOLA kilometre-scale roughness
    metric, computed at the bank's ``dx``; a flat dict of plain floats with a
    float-keyed ``profile`` sub-dict, JSON-serialisable.

    An Iwahashi & Pike (2007) terrain-signature sub-dict is appended likewise
    (append-only analysis layer, NOT read by any decision): ``"iwahashi_pike"`` --
    the :func:`terratrace.iwahashi_pike.iwahashi_pike_signature` dict (the
    three-part geometric-signature tile means ``slope_mean`` / ``convexity_mean``
    / ``texture_mean``, the first-level nested-means ``composition`` over the 8
    classes "0".."7", and the integer ``dominant_class``). This is the
    first-level, 8-class geometric-signature classification of Iwahashi & Pike
    (2007), computed at the bank's ``dx``; a JSON-serialisable dict of plain
    floats + a string-keyed float ``composition`` + an int, complementary to the
    geomorphon landform classifier.

    A surface-dissection texture sub-dict is appended likewise (append-only; NOT
    read by any decision): ``"drainage"`` -- the
    :func:`terratrace.drainage.drainage_signature` dict (``channel_fraction``,
    ``mean_log_acc``, ``max_acc_fraction`` and the ``drainage_density_proxy``)
    from the depression-filled D8 flow-accumulation field (O'Callaghan & Mark
    1984 D8 routing; Barnes et al. 2014 priority-flood fill), computed at the
    bank's ``dx``; a flat dict of plain floats, JSON-serialisable. This is a
    PURELY GEOMETRIC descriptor of how the surface would route a space-filling
    flow -- NOT a claim of water, fluvial, climate, erosion, or mission processes
    on any body.

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
        # --- line-of-sight landform sub-dicts (append-only; NOT used by the
        #     study decision). Openness (Yokoyama 2002) is a flat dict of
        #     floats; the geomorphon signature (Jasiewicz & Stepinski 2013) is
        #     {composition: {name: float}, spectrum: 9x9 nested list of floats,
        #     dominant_form: name}. Both are JSON-serialisable. ---
        "openness": openness.openness_signature(z, dx=dx),
        "geomorphons": geomorphons.geomorphon_signature(z, dx=dx),
        # --- scale/fabric sub-dicts (append-only; NOT used by the study
        #     decision). Spectral = radially-averaged 2-D PSD roughness
        #     signature (slope / band RMS / peak wavelength); anisotropy =
        #     directional structure-function fabric (strength / orientation /
        #     isotropy). Both are flat dicts of plain floats, JSON-serialisable. ---
        "spectral": spectral.spectral_signature(z, dx=dx),
        "anisotropy": anisotropy.anisotropy_signature(z, dx=dx),
        # --- differential-slope baseline roughness sub-dict (append-only; NOT
        #     used by the study decision). Kreslavsky & Head (2000) MOLA
        #     kilometre-scale roughness, gridded to the DEM: fine/coarse baseline
        #     roughness (median |differential slope|, degrees), the ascending
        #     roughness-vs-scale profile (float-metre keys) and its log-log slope.
        #     Flat dict of plain floats + a float-keyed profile dict,
        #     JSON-serialisable. ---
        "kh_roughness": kh_roughness.kh_roughness_signature(z, dx=dx),
        # --- Iwahashi & Pike (2007) three-part geometric signature + first-level
        #     nested-means terrain classification (append-only; NOT used by the
        #     study decision). slope/convexity/texture tile means, the 8-class
        #     composition ("0".."7") and the dominant class; JSON-serialisable,
        #     complementary to the geomorphon landform classifier. ---
        "iwahashi_pike": iwahashi_pike.iwahashi_pike_signature(z, dx=dx),
        # --- surface-dissection texture via depression-filled D8 flow
        #     accumulation (append-only; NOT used by the study decision). The
        #     drainage_signature flat dict of plain floats (channel_fraction,
        #     mean_log_acc, max_acc_fraction, drainage_density_proxy), computed at
        #     the bank's dx. A PURELY GEOMETRIC flow-routing descriptor
        #     (O'Callaghan & Mark 1984 D8; Barnes et al. 2014 priority flood) --
        #     NOT a water, fluvial, climate, hazard, or mission claim. ---
        "drainage": drainage.drainage_signature(z, dx=dx),
    }


# Fixed field order for :func:`bank_vector`; documented so callers can rely
# on positional meaning for quick tile-to-tile comparison. The first seven
# entries are frozen; the landform scalars were APPENDED next, and the
# scale/fabric scalars are APPENDED after those -- so every earlier position
# stays stable no matter what is added at the end.
BANK_VECTOR_FIELDS = (
    "slope.p50",
    "ruggedness.p50",
    "mean_curvature.std",
    "vector_ruggedness.p50",
    "aspect_dispersion",
    "hypsometric_integral",
    "hurst_exponent",
    # --- appended landform scalars (openness medians, then the geomorphon
    #     area-fractions of peak / ridge / slope / valley / pit) ---
    "openness.positive_median",
    "openness.negative_median",
    "geomorphons.peak",
    "geomorphons.ridge",
    "geomorphons.slope",
    "geomorphons.valley",
    "geomorphons.pit",
    # --- appended scale/fabric scalars (spectral log-log slope and detrended
    #     RMS roughness, then the directional-fabric anisotropy strength);
    #     APPENDED last so all earlier positions stay frozen ---
    "spectral.spectral_slope",
    "spectral.roughness_rms",
    "anisotropy.strength",
)


def bank_vector(z, dx=1.0, window=5):
    """Return the headline scalars of :func:`descriptor_bank` as an ordered tuple.

    The field order is fixed by :data:`BANK_VECTOR_FIELDS`:
    ``(slope p50, ruggedness p50, mean_curvature std, vector_ruggedness p50,
    aspect_dispersion, hypsometric_integral, hurst_exponent,
    openness positive_median, openness negative_median, the geomorphon
    area-fractions of peak / ridge / slope / valley / pit, and finally the
    spectral log-log slope, the detrended RMS roughness and the anisotropy
    fabric strength)``. The first seven positions are frozen; the seven landform
    scalars were APPENDED next, and the three scale/fabric scalars are APPENDED
    after those, so earlier positions never move. It is a deterministic,
    plain-float convenience for quick tile-to-tile comparison and carries the
    same claim firewall as the bank: map-scale morphology only.
    """
    bank = descriptor_bank(z, dx=dx, window=window)
    comp = bank["geomorphons"]["composition"]
    return (
        bank["slope"]["p50"],
        bank["ruggedness"]["p50"],
        bank["mean_curvature"]["std"],
        bank["vector_ruggedness"]["p50"],
        bank["aspect_dispersion"],
        bank["hypsometric_integral"],
        bank["hurst_exponent"],
        bank["openness"]["positive_median"],
        bank["openness"]["negative_median"],
        comp["peak"],
        comp["ridge"],
        comp["slope"],
        comp["valley"],
        comp["pit"],
        bank["spectral"]["spectral_slope"],
        bank["spectral"]["roughness_rms"],
        bank["anisotropy"]["strength"],
    )
