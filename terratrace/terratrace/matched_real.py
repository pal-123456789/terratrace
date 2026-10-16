"""REAL Mars-Earth matched-footprint experiment -- the confirmatory run.

WHY THIS EXISTS. ``matched_benchmark`` validated the matched-footprint METHOD on a
planted synthetic confound (a rough core inside a smooth apron). This module runs
the SAME method on the REAL cached DEMs (Mars MOLA + Earth Copernicus/USGS), which
is the experiment that answers the project's primary research question: does a
Mars volcanic-plains reference have a genuine Earth morphological analog once the
~15x FOOTPRINT mismatch of the exploratory run is removed?

HOW IT REUSES THE ENGINE. The real cross-body comparison is already solved by
``study.load_real_units`` / ``terratrace.reproject.read_aoi_metric``: each AOI is
warped onto its own local azimuthal-equidistant METRIC grid using the correct body
radius, so slope/relief/etc. are computed in true metres and are comparable across
bodies. This module reuses that SAME warp machinery to obtain per-body metric grids
at (near) native spacing, then hands them to the pure-NumPy ``matched_benchmark``
cells (``crop_center`` -> common ``extent_m`` -> ``study.compare_units`` at a common
support). Nothing about the decision, the Pareto frontier, the states, the
provenance, or the claim firewall is reinvented here.

THE RASTERIO SEAM. The ONLY step that needs rasterio -- reading a windowed DEM crop
and reprojecting it -- is isolated behind :func:`load_metric_grids` (v1) and
:func:`load_panel_grids` (v2). Everything
downstream (:func:`run_from_grids`, :func:`run_panel_from_grids`) is pure NumPy + the
engine and is fully testable
offline by substituting synthetic metric grids (see tests/test_matched_real.py,
which mirrors tests/test_real_study_path.py). The two loaders are therefore
the single part of this experiment that cannot be exercised in the rasterio-free
sandbox; they are exercised by the user's real run on the data machine.

V2 REFERENCE PANEL. :func:`run_real_panel` implements the frozen protocol
docs/BENCHMARK-PROTOCOL-v2.md on config/matched_footprint_v2.yml: every panel
reference is compared against the same candidates (never against another reference)
at the largest untruncated common footprint, at supports at or above every source's
effective resolution, with the comparability gate, the source-resolution control,
absolute adequacy, and the frozen H1-H4 decision rules applied literally.

Scope / claim firewall (inherited, unchanged): map-scale terrain-MORPHOLOGY
screening only -- not a traversability, geologic-equivalence, site-access, or
mission-readiness claim.
"""
from __future__ import annotations

import math

from . import matched_benchmark as mb, gaps

__all__ = [
    "load_metric_grids",
    "run_from_grids",
    "run_real_matched",
    "load_panel_grids",
    "run_panel_from_grids",
    "run_real_panel",
]

# Defaults for the frozen real-run spec (config/matched_footprint.example.yml).
_DEFAULT_LENSES = ("core", "extended", "geomorphic", "landform", "texture", "hydro")
_DEFAULT_MISMATCH_RATIO = 10.0   # reference-extent / candidate-extent for the control


def select_compared_units(units, reference_id):
    """Partition units into the COMPARED set (reference first + candidates) and the
    HELD-OUT references, so a planetary reference is never 'analog-matched' against
    another window of the SAME body (which would trivially dominate every cross-body
    candidate — a contamination that masks the real question). A non-reference unit is
    HELD OUT iff its ``role`` is ``held_out_reference`` OR it shares the reference's
    body and is not explicitly ``role: candidate``. Cross-body candidates are compared
    by default. Pure (no I/O); returns ``(compared_ids, held_out_ids)``.
    """
    by_id = {u["id"]: u for u in units}
    ref = by_id.get(reference_id) or {}
    ref_body = ref.get("body", "mars")
    compared, held_out = [reference_id], []
    for u in units:
        uid = u["id"]
        if uid == reference_id:
            continue
        role = str(u.get("role", "")).lower()
        same_body = u.get("body", "earth") == ref_body
        if role == "held_out_reference" or (same_body and role != "candidate"):
            held_out.append(uid)
        else:
            compared.append(uid)
    return compared, held_out
_MISMATCH_MIN_RATIO = 1.5        # below this the mismatched control is not "available"
_READ_MARGIN = 1.1               # over-read margin so a centred crop is not truncated
_DEFAULT_N_BOOT = 200            # spatial-block bootstrap resamples for the primary cell

_HONEST_NOTE = (
    "map-scale terrain-MORPHOLOGY screening + resampling statistics only -- no "
    "traversability, geologic-equivalence, site-access, or mission-readiness claim.")


def _normalise_lenses(decision_metrics_list):
    """Accept either a single lens name or an iterable of lens names and return a
    tuple of names. (The real config carries a LIST under ``decision_metrics``; a
    bare string must not be split into characters.)"""
    if isinstance(decision_metrics_list, str):
        return (decision_metrics_list,)
    return tuple(decision_metrics_list)


def _center_bbox(center_lon_e, center_lat, extent_m, body):
    """Symmetric ``(west, south, east, north)`` degree bbox of physical side roughly
    ``extent_m`` centred on ``(center_lon_e, center_lat)`` for ``body``.

    Pure trigonometry (no rasterio), so the window geometry is unit-testable. The
    half-width in latitude is ``(extent_m/2) / (R*pi/180)`` for the body's mean
    radius ``R``; the longitude half-width divides that by ``cos(lat)``. Longitudes
    are kept in the config's East convention and passed through unchanged, so the
    downstream warp (:func:`terratrace.reproject.read_aoi_metric`) centres its local
    azimuthal-equidistant grid on exactly this AOI centre.
    """
    from . import reproject as rp
    m_per_deg = rp.body_radius_m(body) * math.pi / 180.0
    half_lat = (float(extent_m) / 2.0) / m_per_deg
    coslat = max(math.cos(math.radians(float(center_lat))), 1e-6)
    half_lon = half_lat / coslat
    lon0 = float(center_lon_e)
    lat0 = float(center_lat)
    return (lon0 - half_lon, lat0 - half_lat, lon0 + half_lon, lat0 + half_lat)


def _require_rasterio():
    """Probe rasterio up front; raise a catchable :class:`ImportError` if absent, so
    the runner can print an honest blocked message instead of a traceback."""
    try:
        import rasterio  # noqa: F401  (probe: fail with a catchable ImportError if absent)
    except Exception as exc:  # ModuleNotFoundError / env issues both land here
        raise ImportError(
            "rasterio is required for the REAL matched-footprint run (windowed, "
            "per-body reprojected DEM reads); install it on the data machine") from exc


def _read_unit_metric(u, body, res, read_extent):
    """Windowed read of ONE config unit, warped onto its own per-body local
    azimuthal-equidistant METRIC grid (rasterio seam; shared by the v1 and v2 loaders).

    AOI precedence: an explicit ``bbox``; else a centre (``center_lon_e`` +
    ``center_lat``, East longitude) giving a symmetric window of side
    ``read_extent``; else the raster's own geographic bounds (an already-AOI-sized
    tile, reprojected about its centroid). Returns ``(z, spacing_m)``.
    """
    import numpy as np
    import rasterio
    from rasterio.warp import transform_bounds
    from . import reproject as rp

    mask_kw = dict(mask_below=u.get("mask_below_m"),
                   mask_values=u.get("mask_values"),
                   mask_above=u.get("mask_above_m"))

    if u.get("bbox"):
        bbox = tuple(u["bbox"])
    elif u.get("center_lon_e") is not None and u.get("center_lat") is not None:
        bbox = _center_bbox(u["center_lon_e"], u["center_lat"], read_extent, body)
    else:
        # No centre: use the raster's own geographic bounds (reproject the tile
        # about its centroid). COP30 tiles are already AOI-sized in EPSG:4326.
        with rasterio.open(u["path"]) as ds:
            if ds.crs is None:
                raise RuntimeError(f"{u['path']} has no CRS; cannot infer AOI bounds")
            b = ds.bounds
            if ds.crs.is_geographic:
                bbox = (b.left, b.bottom, b.right, b.top)
            else:
                bbox = transform_bounds(ds.crs, rp.geographic_crs(body),
                                        b.left, b.bottom, b.right, b.top)

    z, spacing = rp.read_aoi_metric(u["path"], bbox, res, body, **mask_kw)
    return np.asarray(z, dtype=float), float(spacing)


def load_metric_grids(cfg):
    """REAL (rasterio) seam: per-body reprojected metric grids at (near) native spacing.

    For each unit in ``cfg['units']`` read the DEM window and warp it onto the
    unit's own local azimuthal-equidistant METRIC grid (the SAME machinery
    ``study.load_real_units`` uses, :func:`terratrace.reproject.read_aoi_metric`),
    then return ``(grids, spacings_m, rights, reference_id)``:

      * ``grids``       -- ``{uid: 2-D float array}`` in true metres per body;
      * ``spacings_m``  -- ``{uid: float}`` realised metric spacing (near native);
      * ``rights``      -- ``{uid: rights_status}``;
      * ``reference_id``-- the Mars reference id.

    The reference is read over a window ``_DEFAULT_MISMATCH_RATIO`` x larger than
    the matched ``extent_m`` (one windowed read) so :func:`run_from_grids` can crop
    it both to the matched extent and to the larger mismatched-control extent WITHOUT
    a second read; candidates are read at ~``extent_m``. Reads are WINDOWED -- the
    2.1 GB global MOLA is never loaded whole. A unit may specify its AOI centre
    (``center_lon_e`` + ``center_lat``, East longitude) or an explicit ``bbox``; a
    unit with neither (an already-AOI-sized Earth tile) is reprojected about its own
    raster centroid.

    This (with the v2 :func:`load_panel_grids`; both read through
    :func:`_read_unit_metric`) is the ONLY rasterio-dependent code in the module and
    the ONLY part of the experiment untestable in the sandbox. It raises
    :class:`ImportError` up front when rasterio is absent, so the runner can print an
    honest blocked message.
    """
    _require_rasterio()

    units = list(cfg["units"])
    reference_id = cfg.get("reference_id") or next(
        (u["id"] for u in units if u.get("is_reference")), units[0]["id"])
    extent_m = float(cfg["extent_m"])
    mismatch_ratio = float(cfg.get("mismatch_ratio", _DEFAULT_MISMATCH_RATIO))

    compared_ids, held_out_ids = select_compared_units(units, reference_id)
    if held_out_ids:
        print("[matched_real] held out (NOT candidates -- same body as reference or "
              "role=held_out_reference): " + ", ".join(held_out_ids))
    compared_set = set(compared_ids)

    grids, spacings, rights = {}, {}, {}
    for u in units:
        uid = u["id"]
        if uid not in compared_set:
            continue
        is_ref = (uid == reference_id) or bool(u.get("is_reference"))
        body = u.get("body", "mars" if is_ref else "earth")
        res = float(u.get("native_posting_m") or (extent_m / 100.0))
        read_extent = extent_m * (mismatch_ratio if is_ref else 1.0) * _READ_MARGIN
        grids[uid], spacings[uid] = _read_unit_metric(u, body, res, read_extent)
        rights[uid] = u.get("rights_status", "unknown")

    return grids, spacings, rights, reference_id


def _confound_verdict(matched_rec, mismatched):
    """Did the footprint mismatch ALONE change the recommended analog? Compares the
    matched-footprint recommendation against the mismatched-control recommendation."""
    if not mismatched.get("available", True):
        return {"evaluated": False,
                "note": "mismatched-footprint control not available at this extent"}
    mism_rec = mismatched.get("recommended_unit")
    flipped = (matched_rec is not None and mism_rec is not None and mism_rec != matched_rec)
    return {
        "evaluated": True,
        "matched_recommendation": matched_rec,
        "mismatched_recommendation": mism_rec,
        "footprint_confound_changes_result": bool(flipped),
        "note": ("matched and mismatched footprints recommend DIFFERENT units -- the "
                 "extent mismatch alone changes the analog (confound demonstrated)"
                 if flipped else
                 "matched and mismatched footprints agree on the recommendation"),
    }


def _write_bundle(bundle, out, filename="matched_benchmark_real.json"):
    """Write the JSON evidence bundle (deterministic: sort_keys) and return its path."""
    import json
    import os
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, sort_keys=True)
    return path


def _print_summary(bundle, path=None):
    """One-screen honest summary: scale stability, primary matched decision + the
    engine's spatial-block non-domination, the mismatched control + confound verdict,
    naive baselines, and the lens ablation. No composite score."""
    print("=" * 74)
    print("TerraTrace matched-footprint benchmark -- REAL Mars-Earth experiment")
    print("=" * 74)
    print(f"reference_id = {bundle['reference_id']}   "
          f"extent_m = {bundle['extent_m']:g}   "
          f"supports_m = {', '.join(f'{s:g}' for s in bundle['supports_m'])}")
    print("")
    print("matched recommendation per support (core lens, FIXED extent -- scale sweep):")
    for s in bundle["supports_m"]:
        print(f"  support {s:>8.0f} m -> {bundle['matched_recommendation_by_support'].get(f'{s:g}')}")
    primary = bundle["matched_primary"]
    print(f"\nprimary matched (core @ {bundle['representative_support_m']:g} m): "
          f"{primary['result_state']}  rec={primary['recommended_unit']}")
    nd = bundle.get("bootstrap_nondomination")
    if nd is not None:
        print(f"  spatial-block non-domination freq: {nd}")
    mism = bundle["mismatched"]
    if mism.get("available", True):
        print(f"mismatched control (ref {mism['ref_extent_m']:g} m / cand {mism['cand_extent_m']:g} m, "
              f"ratio {mism.get('footprint_ratio', float('nan')):.1f}): "
              f"{mism['result_state']}  rec={mism['recommended_unit']}")
    else:
        print(f"mismatched control: not available ({mism['reason']})")
    print(f"confound verdict: {bundle['confound_verdict']['note']}")
    print("baselines @ matched: " + "; ".join(
        f"{d}->{bundle['baselines'][d]['closest']}" for d in bundle["baselines"]))
    print("lens ablation @ matched: " + "; ".join(
        f"{k}={v['recommended_unit']}" for k, v in bundle["lens_ablation"].items()))
    print(f"\nNOTE: {_HONEST_NOTE}")
    if path:
        print(f"[bundle] wrote {path}")


def run_from_grids(grids, spacings, rights, reference_id, extent_m, supports, out=None,
                   decision_metrics_list=_DEFAULT_LENSES, rep_support_m=None,
                   mismatch_ratio=_DEFAULT_MISMATCH_RATIO, min_valid=0.5,
                   n_boot=_DEFAULT_N_BOOT):
    """PURE (no rasterio) core of the real matched-footprint experiment.

    Given per-body metric ``grids`` (``{uid: 2-D array}``) at near-native
    ``spacings`` (``{uid: metres}``), the ``rights`` map, the ``reference_id`` and
    the matched ``extent_m`` + the scale ``supports`` sweep, this crops every unit to
    the common ``extent_m`` (via :func:`matched_benchmark.crop_center`, inside each
    cell) and runs, reusing the engine throughout:

      1. a PRIMARY matched decision -- core lens at the representative support, with
         the engine's spatial-block bootstrap (seed-fixed, deterministic) when
         ``n_boot > 0`` -- giving the headline recommendation + non-domination;
      2. a SCALE stability grid -- :func:`matched_benchmark.extent_support_grid` over
         the supports at the FIXED matched extent under the core lens (the config's
         true scale experiment: support varies, extent does not);
      3. a MISMATCHED control -- the reference cropped to a LARGER extent while
         candidates stay at the matched extent (the original ~15x footprint confound),
         run only when the reference grid is materially larger than ``extent_m``;
      4. naive single-descriptor (slope / relief) baselines under the SAME controls;
      5. a lens ablation across ``decision_metrics_list`` at the matched (extent,
         support), so lens-robustness vs lens-dependence is explicit;

    and assembles a JSON-serialisable evidence bundle (with per-unit grid provenance,
    the confound verdict, the inherited claim firewall and the prohibited-claims
    list). Deterministic given the inputs. Writes ``matched_benchmark_real.json`` to
    ``out`` when ``out`` is not None, and prints an honest summary.
    """
    import numpy as np

    extent_m = float(extent_m)
    supports = [float(s) for s in supports]
    if not supports:
        raise ValueError("supports must be a non-empty list of common-support metres")
    lenses = _normalise_lenses(decision_metrics_list)
    rep = float(rep_support_m) if rep_support_m is not None else supports[0]
    ck = {"min_valid": float(min_valid)}

    # (1) PRIMARY matched decision (core lens) + spatial-block bootstrap.
    boot_kw = {"n_boot": int(n_boot), "bootstrap_method": "block"} if n_boot else {}
    primary = mb.matched_cell(grids, spacings, reference_id, extent_m, rep,
                              decision_metrics="core", rights=rights, **boot_kw, **ck)

    # (2) SCALE stability grid: sweep support at the FIXED matched extent (core lens).
    stability = mb.extent_support_grid(grids, spacings, reference_id,
                                       extents=[extent_m], supports=supports,
                                       decision_metrics="core", rights=rights, **ck)
    matched_by_support = {f"{c['support_m']:g}": c["recommended_unit"]
                          for c in stability["cells"]}

    # (3) MISMATCHED control (reference at a larger extent) -- only if available.
    ref_rows, ref_cols = np.asarray(grids[reference_id]).shape
    ref_phys_extent = float(min(ref_rows, ref_cols)) * float(spacings[reference_id])
    mism_extent = min(extent_m * float(mismatch_ratio), ref_phys_extent)
    if mism_extent >= extent_m * _MISMATCH_MIN_RATIO:
        mismatched = mb.mismatched_cell(grids, spacings, reference_id, mism_extent,
                                        extent_m, rep, decision_metrics="core",
                                        rights=rights, **ck)
    else:
        mismatched = {
            "available": False,
            "reason": "reference grid is not materially larger than the matched extent",
            "ref_extent_m": float(mism_extent), "cand_extent_m": extent_m,
            "support_m": rep, "reference_id": reference_id, "mode": "mismatched",
        }

    # (4) Naive single-descriptor baselines under the SAME matched controls.
    baselines = {d: mb.single_descriptor_baseline(grids, spacings, reference_id,
                                                  extent_m, rep, descriptor=d,
                                                  rights=rights)
                 for d in ("slope", "relief")}

    # (5) Lens ablation at the matched (extent, representative support).
    lens_ablation = mb.lens_ablation_matched(grids, spacings, reference_id, extent_m,
                                             rep, lenses=lenses, rights=rights, **ck)

    provenance = {
        "units": {uid: {
            "grid_shape": list(np.asarray(grids[uid]).shape),
            "spacing_m": float(spacings[uid]),
            "grid_extent_m": float(min(np.asarray(grids[uid]).shape) * float(spacings[uid])),
            "rights_status": rights.get(uid, "unknown"),
            "is_reference": bool(uid == reference_id),
        } for uid in grids},
        "controls": {
            "extent_m": extent_m, "supports_m": supports,
            "representative_support_m": rep, "mismatch_ratio": float(mismatch_ratio),
            "mismatch_ref_extent_m": float(mism_extent),
            "min_valid_fraction": float(min_valid),
            "n_boot": int(n_boot), "bootstrap_method": "block" if n_boot else None,
        },
    }

    bundle = {
        "experiment": "matched_footprint_real_v1",
        "reference_id": reference_id,
        "extent_m": extent_m,
        "supports_m": supports,
        "representative_support_m": rep,
        "decision_metrics_list": list(lenses),
        "matched_primary": primary,
        "matched_recommendation_by_support": matched_by_support,
        "stability_grid": stability,
        "cells": stability["cells"],
        "mismatched": mismatched,
        "baselines": baselines,
        "lens_ablation": lens_ablation,
        "bootstrap_nondomination": primary.get("nondominated_freq"),
        "confound_verdict": _confound_verdict(primary.get("recommended_unit"), mismatched),
        "provenance": provenance,
        "scope_note": _HONEST_NOTE,
        "prohibited_claims": gaps.prohibited_claims(),
    }

    path = _write_bundle(bundle, out) if out is not None else None
    _print_summary(bundle, path)
    return bundle


def run_real_matched(cfg, out="artifacts/mf_real"):
    """Front door for the REAL run: load per-body metric grids (rasterio seam), then
    run the pure core. ``cfg`` is the parsed matched-footprint config (see
    config/matched_footprint.example.yml). Raises :class:`ImportError` (from
    :func:`load_metric_grids`) when rasterio is unavailable, so the CLI can print an
    honest blocked message instead of a traceback."""
    grids, spacings, rights, ref = load_metric_grids(cfg)   # <-- the ONLY rasterio step
    return run_from_grids(
        grids, spacings, rights, ref,
        float(cfg["extent_m"]),
        cfg.get("support_sweep_m", [1000.0]),
        out=out,
        decision_metrics_list=cfg.get("decision_metrics", _DEFAULT_LENSES),
        mismatch_ratio=float(cfg.get("mismatch_ratio", _DEFAULT_MISMATCH_RATIO)),
        min_valid=float(cfg.get("min_valid_fraction", 0.5)),
        n_boot=int(cfg.get("n_boot", _DEFAULT_N_BOOT)),
    )


# =========================================================================== #
# v2 -- REFERENCE PANEL. Frozen protocol: docs/BENCHMARK-PROTOCOL-v2.md;      #
# frozen inputs: config/matched_footprint_v2.yml. Everything below only ADDS; #
# the v1 functions above keep their behaviour.                                #
#                                                                             #
# ERROR precedence (applied uniformly to H1-H3): when any cell a rule reads   #
# is an ERROR, the rule is not applied and the hypothesis is "inconclusive"   #
# -- a failed comparison is never read as evidence either way.               #
# =========================================================================== #

PROTOCOL_V2_PATH = "docs/BENCHMARK-PROTOCOL-v2.md"
_PANEL_BUNDLE_NAME = "matched_panel_real.json"

# Which references each frozen rule reads, and its thresholds (protocol v2).
_H1_CLASS, _H1_N_REFS, _H1_MIN_HOLDS = "volcanic_plains", 3, 2   # Amazonis, Syria, Hesperia
_H2_CLASS, _H2_N_REFS = "contrast", 2                             # Noachis, Coprates

# Frozen texts copied from docs/BENCHMARK-PROTOCOL-v2.md (markdown emphasis removed,
# words unchanged; tests/test_matched_real.py fails if they drift from the document).
_REGIME_RULE = (
    "Regime for all evidence: common extent = the largest window every unit provides "
    "untruncated (24 km, limited by the Craters tile); supports ≥ the support floor "
    "(1500 m, 2000 m). Supports 500/1000 m are diagnostic only and never count as "
    "evidence. Core lens. Same three Earth candidates for every reference. Panel "
    "references are never compared with each other.")
_RULES = {
    "H1": ("H1 — Confirmation. For held-out Mars volcanic plains, Craters of the Moon "
           "is the sole core-lens recommendation. Supported if ≥ 2 of the 3 "
           "confirmatory plains references (Amazonis, Syria, Hesperia) have outcome holds "
           "(recommended at both honest supports). Not supported if ≤ 1. Daedalia and "
           "Elysium are exploratory and are reported but never counted."),
    "H2": ("H2 — Specificity. The relationship is specific to volcanic plains, not a "
           "generic \"closest member of a weak shortlist\" effect. Supported if both "
           "contrast references (Noachis Terra, Coprates Chasma) have outcome holds for "
           "not_sole (Craters is not the sole recommendation at either honest support) and "
           "the panel specificity verdict is specific. Not supported if Craters is the sole "
           "recommendation for the contrast terrains too — then any plains result is "
           "reported as non-specific."),
    "H3": ("H3 — Not a source-smoothing artifact. Re-running with every unit low-passed "
           "to the coarsest effective resolution (resolution.match_effective_resolution) "
           "leaves the primary reference's honest-support recommendation unchanged, and "
           "changes no H1 confirmatory outcome from holds to fails. Not supported if the "
           "matched-resolution run reverses the primary recommendation. Diagnostic (not "
           "evidence): whether the v1 500 m result changes under resolution matching."),
    "H4": ("H4 — Absolute adequacy (reported, no predeclared direction). For each "
           "reference, is the recommended candidate within that reference's own internal "
           "variability (adequacy.adequacy_assessment, 95th percentile, 3×3 held-out "
           "sub-windows, at 1500 m)? If no candidate is adequate, the honest statement is: "
           "\"best among these candidates, but outside the reference's own morphological "
           "variability.\""),
}
_ROBUSTNESS_RULE = (
    "Robustness (exploratory, primary reference only): adversarial.stress_test — "
    "crop-origin shift, support step, correlated-noise / tilt / smoothing DEM "
    "perturbations, lens family, candidate dropout. Reported as trust bounds, never as "
    "confirmation.")
LIMITATIONS_V2 = (
    "Not independent replications: all Mars references share one source (MOLA) and all "
    "Earth candidates share one (COP30); the candidate set is the same three tiles. 7 "
    "references × 2 honest supports = 14 decisions — multiple comparisons, "
    "reported as such.",
    "Low statistical power: at 24 km extent the honest supports give only 16 and 12 cells "
    "per side. The block bootstrap and adequacy bands are correspondingly coarse.",
    "Representativeness: each 24 km window samples a small part of a named Mars unit; "
    "coordinates are approximate named-feature centres.",
    "The 3× effective-resolution figure is a heuristic, not a measured MOLA transfer "
    "function.",
    "Morphology only: no traversability, geologic-equivalence, site-access, or mission "
    "claim.",
)
_H4_NO_ADEQUATE = ("best among these candidates, but outside the reference's own "
                   "morphological variability.")
_DIAGNOSTIC_LABEL = "DIAGNOSTIC -- below the support floor; never evidence"
_HYP_NAMES = {"H1": "confirmation", "H2": "specificity",
              "H3": "not smoothing", "H4": "adequacy"}

# A Windows console or a redirected pipe may be cp1252, which cannot encode >= / <=:
# every printed line goes through _ascii so a print can never crash the real run.
_ASCII = (("≥", ">="), ("≤", "<="), ("×", "x"), ("—", "--"),
          ("–", "-"), ("→", "->"))


def _ascii(text):
    s = str(text)
    for a, b in _ASCII:
        s = s.replace(a, b)
    return s.encode("ascii", "replace").decode("ascii")


def _fmt_m(x):
    return "n/a" if x is None else f"{float(x):g}"


def _panel_ids(cfg):
    """``(panel_ids, candidate_ids)`` of a v2 config, in config order (pure)."""
    return [p["id"] for p in cfg["panel"]], list(cfg["candidates"])


def load_panel_grids(cfg):
    """REAL (rasterio) seam for the v2 reference panel: per-body metric grids for
    EVERY unit in ``cfg['units']`` (all panel references + all candidates).

    Same machinery as :func:`load_metric_grids` (:func:`_read_unit_metric` ->
    :func:`terratrace.reproject.read_aoi_metric`; WINDOWED, so the 2.1 GB MOLA is
    never loaded whole). A centred unit (each Mars reference) is read over a
    window of side ``extent_m * _READ_MARGIN`` -- v2 has NO enlarged
    mismatched-control over-read. A unit with neither centre nor bbox (a cached
    Earth tile) is read over its own raster bounds, as in v1. Returns
    ``(grids, spacings_m, rights)``.

    Raises :class:`ImportError` up front when rasterio is absent (the same probe as
    v1), and :class:`ValueError` BEFORE any read when a panel reference or candidate
    has no ``units`` entry. Untestable in the rasterio-free sandbox; exercised by
    the user's real run.
    """
    _require_rasterio()
    panel_ids, cands = _panel_ids(cfg)
    unit_ids = [u["id"] for u in cfg["units"]]
    missing = [uid for uid in panel_ids + cands if uid not in unit_ids]
    if missing:
        raise ValueError(f"v2 config: no 'units' entry for {missing}")
    extent_m = float(cfg["extent_m"])
    panel_set = set(panel_ids)

    grids, spacings, rights = {}, {}, {}
    for u in cfg["units"]:
        uid = u["id"]
        body = u.get("body", "mars" if uid in panel_set else "earth")
        res = float(u.get("native_posting_m") or (extent_m / 100.0))
        grids[uid], spacings[uid] = _read_unit_metric(u, body, res, extent_m * _READ_MARGIN)
        rights[uid] = u.get("rights_status", "unknown")
        print(f"[matched_real] read {uid}: grid {grids[uid].shape[0]}x{grids[uid].shape[1]} "
              f"at {spacings[uid]:.1f} m ({body})")
    return grids, spacings, rights


def _plan_supports(cfg, spacings, res_factor, floor_m):
    """Split the configured supports into HONEST (evidence) and DIAGNOSTIC.

    A configured honest support below the support floor is DEMOTED to diagnostic
    with an explicit warning -- never treated as honest. A support configured as
    both honest and diagnostic stays diagnostic only. Returns ``(plan, warnings)``.
    """
    from . import comparability as cp
    cfg_honest = sorted({float(s) for s in (cfg.get("honest_supports_m") or [])})
    cfg_diag = sorted({float(s) for s in (cfg.get("diagnostic_supports_m") or [])})
    above = cp.honest_supports(cfg_honest, spacings, res_factor)
    demoted = [s for s in cfg_honest if s not in above]
    both = [s for s in above if s in cfg_diag]
    warns = [f"configured honest support {s:g} m is below the support floor {floor_m:g} m "
             f"(finer than a source's effective resolution) -- DEMOTED to diagnostic; it "
             f"is never evidence" for s in demoted]
    warns += [f"support {s:g} m is configured as both honest and diagnostic -- kept "
              f"diagnostic only (never evidence)" for s in both]
    plan = {"honest_m": [s for s in above if s not in cfg_diag],
            "diagnostic_m": sorted(set(cfg_diag) | set(demoted)),
            "demoted_m": demoted,
            "configured_honest_m": cfg_honest,
            "configured_diagnostic_m": cfg_diag}
    return plan, warns


def _attach_comparability(panel_out):
    """Attach ``comparability = {regime, assessment}`` to every cell of one panel
    run (:func:`comparability.assess_cell` + :func:`comparability.regime_label` on
    the cell's own provenance). An ERROR cell has no provenance -> ``unassessed``."""
    from . import comparability as cp
    for r in (panel_out or {}).get("references", []):
        for c in r["cells"]:
            if c.get("provenance"):
                a = cp.assess_cell(c["provenance"])
                c["comparability"] = {"regime": cp.regime_label(a), "assessment": a}
            else:
                c["comparability"] = {"regime": "unassessed", "assessment": None,
                                      "reason": "ERROR cell: no provenance to assess"}


def _refs_by_id(panel_out):
    return {r["id"]: r for r in (panel_out or {}).get("references", [])}


def _cells(panel_out):
    """``{(ref_id, support_m): cell}`` for one panel run, in panel/support order."""
    return {(r["id"], float(c["support_m"])): c
            for r in (panel_out or {}).get("references", []) for c in r["cells"]}


def _sole(cell):
    """The cell's SOLE recommendation (a RECOMMEND_FOLLOW_UP unit), else None."""
    from . import confirmation as cf
    if cell is None or cell.get("result_state") != cf.RECOMMEND:
        return None
    return cell.get("recommended_unit")


def _cell_label(cell):
    """Recommended unit, or the result state when there is no sole recommendation."""
    if cell is None:
        return "-"
    return _sole(cell) or str(cell.get("result_state"))


def _has_error(record):
    from . import confirmation as cf
    return any(c["result_state"] == cf.ERROR_STATE for c in record["cells"])


def _regime_audit(runs):
    """Audit the HONEST-support cells of the given ``(name, panel_out)`` runs.

    Returns ``(violations, low_power, unassessed)``: a violation is an assessed
    cell whose regime is not ``honest`` once a ``+low-power`` suffix is ignored
    (low power is reported but allowed); an ERROR cell cannot be assessed and is
    listed separately (each rule handles ERROR cells itself)."""
    violations, low_power, unassessed = [], [], []
    for name, panel_out in runs:
        for r in (panel_out or {}).get("references", []):
            for c in r["cells"]:
                comp = c["comparability"]
                where = {"run": name, "reference": r["id"],
                         "support_m": float(c["support_m"]), "regime": comp["regime"]}
                if comp["assessment"] is None:
                    unassessed.append(where)
                    continue
                if comp["regime"].endswith("+low-power"):
                    low_power.append(where)
                if comp["regime"].replace("+low-power", "") != "honest":
                    violations.append(dict(where, issues=list(comp["assessment"]["issues"])))
    return violations, low_power, unassessed


def _regime_table(panel_out):
    """``{ref_id: {support: regime}}`` -- the compact per-cell regime view."""
    table = {}
    for (rid, s), c in _cells(panel_out).items():
        table.setdefault(rid, {})[f"{s:g}"] = c["comparability"]["regime"]
    return table


def _rc_rows(raw_run, matched_run, support_class):
    """Raw vs resolution-matched recommendation for every (reference, support)."""
    mc = _cells(matched_run)
    rows = []
    for (rid, s), c in _cells(raw_run).items():
        m = mc.get((rid, s))
        rows.append({"reference": rid, "support_m": s, "support_class": support_class,
                     "raw_state": c["result_state"], "raw_recommendation": _sole(c),
                     "matched_state": None if m is None else m["result_state"],
                     "matched_recommendation": _sole(m),
                     "changed": bool(m is None or _sole(c) != _sole(m))})
    return rows


def _expect_fact(record):
    """Compact, per-support facts behind one reference's expectation outcome."""
    by_s = {float(c["support_m"]): c for c in record["cells"]}
    e = record["expectation"]
    return {"status": record["status"], "class": record["class"],
            "counts_as_confirmation": record["counts_as_confirmation"],
            "declared": e["declared"], "outcome": e["outcome"],
            "per_support": [{"support_m": p["support_m"], "satisfied": p["satisfied"],
                             "result_state": by_s[p["support_m"]]["result_state"],
                             "recommendation": _sole(by_s[p["support_m"]])}
                            for p in e["per_support"]],
            "error_supports": list(e["error_supports"])}


def _hyp(verdict, rule_key, reason, evidence, counts):
    return {"verdict": verdict, "rule": _RULES[rule_key], "reason": reason,
            "evidence": evidence, "counts": counts}


_NO_HONEST = "no honest support survived the support floor -- nothing to evaluate"


def _hypothesis_h1(honest):
    """H1 (frozen): supported iff >= 2 of the 3 CONFIRMATORY volcanic-plains
    references have outcome ``holds`` over the HONEST supports; not supported if
    <= 1. Exploratory references are reported and never counted."""
    refs = (honest or {}).get("references", [])
    plains = [r for r in refs if r["class"] == _H1_CLASS]
    counted = [r for r in plains if r["counts_as_confirmation"]]
    holds = [r["id"] for r in counted if r["expectation"]["outcome"] == "holds"]
    errored = [r["id"] for r in counted if _has_error(r)]
    wrong = [r["id"] for r in counted
             if (r["expectation"]["declared"] or {}).get("type") != "recommends"]
    evidence = {r["id"]: _expect_fact(r) for r in counted}
    counts = {"confirmatory_refs": len(counted), "holds": len(holds), "holds_ids": holds,
              "required_holds": _H1_MIN_HOLDS, "frozen_n_refs": _H1_N_REFS}
    if honest is None:
        out = _hyp("inconclusive", "H1", _NO_HONEST, evidence, counts)
    elif len(counted) != _H1_N_REFS:
        out = _hyp("inconclusive", "H1",
                   f"{len(counted)} confirmatory {_H1_CLASS} reference(s) evaluated; the "
                   f"frozen rule is defined over exactly {_H1_N_REFS}", evidence, counts)
    elif wrong:
        out = _hyp("inconclusive", "H1",
                   f"expectation type is not 'recommends' for {wrong}; the frozen rule "
                   f"does not apply", evidence, counts)
    elif errored:
        out = _hyp("inconclusive", "H1",
                   f"ERROR cell(s) at honest supports for {errored} -- the rule is not "
                   f"applied to failed comparisons", evidence, counts)
    elif len(holds) >= _H1_MIN_HOLDS:
        out = _hyp("supported", "H1",
                   f"{len(holds)} of {_H1_N_REFS} confirmatory plains references hold "
                   f"(>= {_H1_MIN_HOLDS} required): {holds}", evidence, counts)
    else:
        out = _hyp("not_supported", "H1",
                   f"{len(holds)} of {_H1_N_REFS} confirmatory plains references hold "
                   f"(<= {_H1_MIN_HOLDS - 1})", evidence, counts)
    out["exploratory_not_counted"] = {
        r["id"]: dict(_expect_fact(r), counted=False)
        for r in plains if not r["counts_as_confirmation"]}
    return out


def _hypothesis_h2(honest):
    """H2 (frozen): supported iff BOTH confirmatory contrast references have outcome
    ``holds`` for ``not_sole`` over the HONEST supports AND the panel specificity
    verdict (honest supports only) is ``specific``; otherwise not supported.
    Inconclusive on any honest ERROR cell (the specificity verdict reads every
    reference) or a ``not_evaluable`` verdict."""
    refs = (honest or {}).get("references", [])
    contrast = [r for r in refs if r["class"] == _H2_CLASS and r["counts_as_confirmation"]]
    holds = [r["id"] for r in contrast if r["expectation"]["outcome"] == "holds"]
    wrong = [r["id"] for r in contrast
             if (r["expectation"]["declared"] or {}).get("type") != "not_sole"]
    errors = [f"{r['id']}@{s:g}m" for r in refs for s in r["expectation"]["error_supports"]]
    spec = (honest or {}).get("summary", {}).get("specificity") or {}
    evidence = {"contrast": {r["id"]: _expect_fact(r) for r in contrast},
                "specificity": {k: spec.get(k) for k in
                                ("verdict", "top_unit_by_class", "explanation")}}
    counts = {"contrast_refs": len(contrast), "not_sole_holds": len(holds),
              "not_sole_holds_ids": holds, "frozen_n_refs": _H2_N_REFS}
    if honest is None:
        return _hyp("inconclusive", "H2", _NO_HONEST, evidence, counts)
    if len(contrast) != _H2_N_REFS:
        return _hyp("inconclusive", "H2",
                    f"{len(contrast)} confirmatory {_H2_CLASS} reference(s) evaluated; the "
                    f"frozen rule is defined over exactly {_H2_N_REFS}", evidence, counts)
    if wrong:
        return _hyp("inconclusive", "H2",
                    f"expectation type is not 'not_sole' for {wrong}; the frozen rule "
                    f"does not apply", evidence, counts)
    if errors:
        return _hyp("inconclusive", "H2",
                    f"ERROR cell(s) at honest supports ({', '.join(errors)}) -- contrast "
                    f"outcomes and the panel specificity verdict cannot be relied on",
                    evidence, counts)
    if spec.get("verdict") == "not_evaluable":
        return _hyp("inconclusive", "H2",
                    f"panel specificity is not_evaluable: {spec.get('explanation')}",
                    evidence, counts)
    if len(holds) == _H2_N_REFS and spec.get("verdict") == "specific":
        return _hyp("supported", "H2",
                    f"both contrast references hold not_sole and the panel specificity "
                    f"verdict is specific ({spec.get('top_unit_by_class')})", evidence, counts)
    failed = [r["id"] for r in contrast if r["id"] not in holds]
    return _hyp("not_supported", "H2",
                f"contrast references not holding not_sole: {failed}; panel specificity "
                f"verdict: {spec.get('verdict')} -- per protocol v2 any plains result is "
                f"reported as NON-SPECIFIC", evidence, counts)


def _hypothesis_h3(raw_honest, matched_honest, rc_ran, primary_id, diagnostic_rows):
    """H3 (frozen): NOT supported iff the primary reference's recommendation at any
    honest support changes between the raw and the resolution-matched run, OR any
    H1 confirmatory reference goes from ``holds`` (raw) to ``fails`` (matched);
    otherwise supported. The primary's sub-floor supports are reported as a
    DIAGNOSTIC (never evidence)."""
    prim_diag = [r for r in diagnostic_rows if r["reference"] == primary_id]
    v1_500 = next((r for r in prim_diag if r["support_m"] == 500.0), None)
    diagnostic = {"label": _DIAGNOSTIC_LABEL, "primary_by_support": prim_diag,
                  "v1_500m": v1_500,
                  "note": (None if v1_500 is not None else
                           "500 m is not among the diagnostic supports of this run")}
    raw_refs, m_refs = _refs_by_id(raw_honest), _refs_by_id(matched_honest)
    h1_ids = [r["id"] for r in (raw_honest or {}).get("references", [])
              if r["class"] == _H1_CLASS and r["counts_as_confirmation"]]
    rc, mc = _cells(raw_honest), _cells(matched_honest)
    prim_rows = [{"support_m": s, "raw_state": c["result_state"],
                  "raw_recommendation": _sole(c),
                  "matched_state": (mc.get((rid, s)) or {}).get("result_state"),
                  "matched_recommendation": _sole(mc.get((rid, s))),
                  "changed": bool(_sole(c) != _sole(mc.get((rid, s))))}
                 for (rid, s), c in rc.items() if rid == primary_id]
    transitions = {rid: {"raw": raw_refs[rid]["expectation"]["outcome"],
                         "matched": (m_refs.get(rid) or {}).get("expectation", {}).get("outcome")}
                   for rid in h1_ids}
    evidence = {"primary_reference": primary_id, "primary_honest": prim_rows,
                "h1_outcome_raw_vs_matched": transitions}
    changes = [r["support_m"] for r in prim_rows if r["changed"]]
    flips = [rid for rid, t in transitions.items()
             if t["raw"] == "holds" and t["matched"] == "fails"]
    counts = {"primary_changed_supports": changes, "h1_holds_to_fails": flips}

    def _out(verdict, reason):
        h = _hyp(verdict, "H3", reason, evidence, counts)
        h["diagnostic"] = diagnostic
        return h

    if not rc_ran:
        return _out("inconclusive", "the resolution control was not run "
                    "(resolution_control is false)")
    if raw_honest is None:
        return _out("inconclusive", _NO_HONEST)
    if primary_id not in raw_refs:
        return _out("inconclusive", f"primary_reference {primary_id!r} is not in the panel")
    errored = [rid for rid in [primary_id] + h1_ids
               if _has_error(raw_refs[rid]) or (rid in m_refs and _has_error(m_refs[rid]))]
    if errored:
        return _out("inconclusive", f"ERROR cell(s) in the raw or resolution-matched run "
                    f"for {errored} -- the rule is not applied to failed comparisons")
    if changes or flips:
        parts = []
        if changes:
            parts.append(f"primary {primary_id} recommendation changes at honest "
                         f"support(s) {[f'{s:g} m' for s in changes]}")
        if flips:
            parts.append(f"H1 confirmatory outcome holds -> fails for {flips}")
        return _out("not_supported", "; ".join(parts))
    return _out("supported", f"primary {primary_id} recommendation unchanged at every "
                "honest support and no H1 confirmatory outcome goes holds -> fails under "
                "resolution matching")


def _hypothesis_h4(raw_honest, adequacy_info):
    """H4 (frozen, no predeclared direction): per reference, whether the recommended
    candidate is within that reference's own internal variability. Reported only."""
    ade_sup = adequacy_info.get("support_m")
    cells = _cells(raw_honest)
    per, counts = {}, {}
    for r in (raw_honest or {}).get("references", []):
        cell = cells.get((r["id"], ade_sup)) if ade_sup is not None else None
        if cell is not None:
            rec, rec_from = _sole(cell), f"{ade_sup:g} m honest cell"
        else:
            recs = {_sole(c) for c in r["cells"]}
            rec = next(iter(recs)) if len(recs) == 1 else None
            rec_from = "the single sole recommendation across honest supports"
        a = r.get("adequacy")
        if a is None:
            status, statement = "not_run", "adequacy was not run"
        elif rec is None:
            status = "no_recommendation"
            statement = "no sole recommendation to assess"
        elif a.get("error") or not a.get("established"):
            status, statement = "not_established", a.get("note")
        elif rec in a.get("adequate_candidates", []):
            status = "adequate"
            statement = ("within this reference's own internal variability at this footprint "
                         "and support (a relative statement, not a universal score)")
        elif not a.get("any_adequate"):
            status, statement = "inadequate", _H4_NO_ADEQUATE
        else:
            status = "inadequate"
            statement = (f"outside this reference's own variability; adequate candidate(s): "
                         f"{a.get('adequate_candidates')}")
        counts[status] = counts.get(status, 0) + 1
        per[r["id"]] = {"status_of_reference": r["status"], "recommended_unit": rec,
                        "recommended_from": rec_from, "adequacy": status,
                        "statement": statement,
                        "adequate_candidates": None if a is None else a.get("adequate_candidates"),
                        "support_m": None if a is None else a.get("support_m")}
    reason = ("reported per reference -- no predeclared direction"
              if raw_honest is not None else _NO_HONEST)
    return _hyp("reported", "H4", reason, per, counts)


def _apply_regime_gate(hyp, violations):
    """Protocol v2 admits evidence only from honest-regime cells. If the audit finds
    a violation, H1-H3 become inconclusive (the rule outcome is kept, labelled)."""
    if not violations:
        return
    for k in ("H1", "H2", "H3"):
        h = hyp[k]
        h["rule_verdict"], h["rule_reason"] = h["verdict"], h["reason"]
        h["verdict"] = "inconclusive"
        h["reason"] = (f"honest-regime violation in {len(violations)} honest-support "
                       f"cell(s) (see regime_violation) -- protocol v2 admits evidence only "
                       f"from honest-regime cells")
    hyp["H4"]["regime_caveat"] = ("honest-regime violation present; adequacy is reported "
                                  "for completeness only")


def _primary_block(g, sp, rt, cands, primary_id, extent, support, cfg, floor_m, ck):
    """Lens ablation + (optional) adversarial stress test for the primary reference
    against the candidates only, at the smallest honest support. Never raises."""
    from . import adversarial as adv
    if primary_id is None or primary_id not in g:
        return {"evaluated": False,
                "reason": f"primary_reference {primary_id!r} is not in the panel"}
    if support is None:
        return {"evaluated": False, "reason": _NO_HONEST}
    keys = [primary_id] + [c for c in cands if c != primary_id]
    units = {k: g[k] for k in keys}
    spk = {k: sp[k] for k in keys}
    rtk = {k: rt[k] for k in keys}

    ablation = {}
    for lens in _normalise_lenses(cfg.get("decision_metrics", _DEFAULT_LENSES)):
        try:
            ablation[lens] = mb.lens_ablation_matched(units, spk, primary_id, extent, support,
                                                      lenses=(lens,), rights=rtk, **ck)[lens]
        except Exception as exc:  # noqa: BLE001 -- one lens must not crash the run
            ablation[lens] = {"result_state": f"ERROR: {type(exc).__name__}: {exc}",
                              "recommended_unit": None, "pareto_layer1": []}

    stress = None
    if cfg.get("adversarial"):
        try:
            stress = adv.stress_test(units, spk, primary_id, extent, support,
                                     decision_metrics="core", rights=rtk,
                                     seed=int(cfg.get("seed", 0)))
        except Exception as exc:  # noqa: BLE001
            stress = {"error": f"{type(exc).__name__}: {exc}"}
        stress["evidence_status"] = "exploratory trust bounds -- never confirmation"
        if support * 0.67 < floor_m:
            stress["support_floor_note"] = (
                f"the 0.67x support_step probe (~{support * 0.67:.0f} m) is below the "
                f"support floor ({floor_m:g} m), i.e. in a below-effective-resolution "
                f"regime")
    return {"evaluated": True, "reference_id": primary_id, "extent_m": float(extent),
            "support_m": float(support), "compared_units": keys,
            "lens_ablation": ablation, "adversarial": stress, "rule": _ROBUSTNESS_RULE}


def _frozen_sha256(path):
    """sha256 of a frozen input (cwd- or repo-relative, or absolute); None if absent.
    Records WHICH protocol/config bytes were in effect for a bundle."""
    import hashlib
    import os
    if not path:
        return None
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (path, os.path.join(root, path)):
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()
    return None


def run_panel_from_grids(grids, spacings, rights, cfg, out=None):
    """PURE (no rasterio) core of the v2 reference-panel experiment.

    Implements docs/BENCHMARK-PROTOCOL-v2.md on per-body metric ``grids``
    (``{uid: 2-D array}``) at near-native ``spacings`` (``{uid: m}``) with the
    ``rights`` map and the parsed v2 ``cfg`` (``panel``, ``candidates``,
    ``extent_m``, ``honest_supports_m``, ``diagnostic_supports_m``, ...):

      a. footprint -- :func:`comparability.common_matched_extent` (largest window
         every used unit provides untruncated; reduction + limiting unit recorded);
      b. supports  -- :func:`comparability.support_floor_m`; configured honest
         supports below the floor are DEMOTED to diagnostic with a warning;
      c. raw panel -- :func:`confirmation.run_reference_panel` (core lens), run
         SEPARATELY on the honest and on the diagnostic supports, so expectation
         outcomes and the specificity verdict used as evidence are computed over
         honest supports only; adequacy at ``adequacy_support_m`` (smallest honest
         support substituted, and recorded, if it is below the floor);
      d. comparability -- every cell gets ``assess_cell`` + ``regime_label``; any
         honest-support cell outside the honest regime sets ``regime_violation``;
      e. resolution control -- :func:`resolution.match_effective_resolution`, then
         the same panel at the same supports; raw vs matched per (reference, support);
      f. primary reference -- lens ablation + :func:`adversarial.stress_test` at the
         smallest honest support (each failure recorded, never raised);
      g. H1-H4 -- the frozen decision rules, applied literally (honest supports only);
      h. bundle -- written to ``out``/matched_panel_real.json when ``out`` is set;
      i. a plain printed summary.

    Deterministic given the inputs; the bundle is JSON-serialisable.
    """
    import copy
    import numpy as np
    from . import comparability as cp, confirmation as cf, resolution as rz

    panel = copy.deepcopy(list(cfg["panel"]))
    panel_ids, cands = _panel_ids(cfg)
    used = list(dict.fromkeys(panel_ids + cands))
    missing = [u for u in used if u not in grids]
    if missing:
        raise KeyError(f"no grid for unit(s) {missing}")
    g = {u: grids[u] for u in used}
    sp = {u: float(spacings[u]) for u in used}
    rt = {u: rights.get(u, "unknown") for u in used}
    res_factor = float(cfg.get("res_factor", 3.0))
    ck = {"min_valid": float(cfg.get("min_valid_fraction", 0.5)), "res_factor": res_factor}
    warns = []

    # (a) Footprint: the largest window EVERY used unit provides untruncated.
    footprint = cp.common_matched_extent(g, sp, cfg.get("extent_m"))
    extent = footprint["extent_m"]

    # (b) Supports: floor over all units; sub-floor "honest" supports are demoted.
    floor = cp.support_floor_m(sp, res_factor)
    plan, plan_warns = _plan_supports(cfg, sp, res_factor, floor["floor_m"])
    warns += plan_warns
    honest, diagnostic = plan["honest_m"], plan["diagnostic_m"]
    if not honest:
        warns.append("no configured honest support is at or above the support floor -- "
                     "no hypothesis can be evaluated")

    ade_cfg = cfg.get("adequacy_support_m")
    ade_on = bool(cfg.get("adequacy", True)) and bool(honest)
    ade_sup, ade_sub = None, None
    if ade_on:
        if ade_cfg is None:
            ade_sup, ade_sub = honest[0], "not configured -> smallest honest support"
        elif float(ade_cfg) < floor["floor_m"]:
            ade_sup = honest[0]
            ade_sub = (f"configured {float(ade_cfg):g} m is below the support floor "
                       f"{floor['floor_m']:g} m -> smallest honest support {honest[0]:g} m")
            warns.append(f"adequacy support substituted: {ade_sub}")
        else:
            ade_sup = float(ade_cfg)
    adequacy_info = {"run": ade_on, "configured_m": None if ade_cfg is None else float(ade_cfg),
                     "support_m": ade_sup, "substituted": ade_sub is not None,
                     "substitution": ade_sub}

    def _panel_run(gr, sups, adequacy):
        if not sups:
            return None
        res = cf.run_reference_panel(gr, sp, panel, cands, extent, sups,
                                     decision_metrics="core", rights=rt, adequacy=adequacy,
                                     adequacy_support_m=ade_sup if adequacy else None, **ck)
        _attach_comparability(res)                                    # (d)
        return res

    # (c) Raw panel: honest (evidence) and diagnostic (never evidence), separately.
    raw = {"honest": _panel_run(g, honest, ade_on), "diagnostic": _panel_run(g, diagnostic, False)}

    # (e) Resolution control: low-pass every unit to the coarsest effective resolution.
    if cfg.get("resolution_control"):
        gm, rep = rz.match_effective_resolution(g, sp, res_factor)
        matched = {"honest": _panel_run(gm, honest, False),
                   "diagnostic": _panel_run(gm, diagnostic, False)}
        rows_h = _rc_rows(raw["honest"], matched["honest"], "honest")
        rows_d = _rc_rows(raw["diagnostic"], matched["diagnostic"], "diagnostic")
        resolution_control = {
            "run": True, "target_fwhm_m": rep["target_fwhm_m"], "units": rep["units"],
            "comparison": rows_h + rows_d,
            "changed_honest": [r for r in rows_h if r["changed"]],
            "changed_diagnostic": [r for r in rows_d if r["changed"]],
            "diagnostic_label": _DIAGNOSTIC_LABEL,
            "panel_matched": matched}
    else:
        matched, rows_d = {"honest": None, "diagnostic": None}, []
        resolution_control = {"run": False, "reason": "resolution_control is false in the config"}

    # (d) Comparability audit of every honest-support cell (raw + matched).
    violations, low_power, unassessed = _regime_audit(
        [("raw", raw["honest"]), ("resolution_matched", matched["honest"])])

    # (f) Primary reference: lens ablation + adversarial stress test.
    primary_id = cfg.get("primary_reference")
    primary = _primary_block(g, sp, rt, cands, primary_id, extent,
                             honest[0] if honest else None, cfg, floor["floor_m"], ck)

    # (g) The frozen decision rules.
    hyp = {"H1": _hypothesis_h1(raw["honest"]),
           "H2": _hypothesis_h2(raw["honest"]),
           "H3": _hypothesis_h3(raw["honest"], matched["honest"],
                                bool(resolution_control["run"]), primary_id, rows_d),
           "H4": _hypothesis_h4(raw["honest"], adequacy_info)}
    _apply_regime_gate(hyp, violations)
    if hyp["H2"]["verdict"] == "not_supported":
        hyp["H1"]["qualifier"] = ("NON-SPECIFIC: H2 is not supported, so per protocol v2 any "
                                  "plains result is reported as non-specific")

    provenance = {
        "units": {uid: {"grid_shape": list(np.shape(g[uid])), "spacing_m": sp[uid],
                        "available_extent_m": footprint["available_m"][uid],
                        "effective_resolution_m": floor["effective_m"][uid],
                        "rights_status": rt[uid],
                        "role": "panel_reference" if uid in panel_ids else "candidate"}
                  for uid in used},
        "unused_units": sorted(str(u) for u in grids if u not in g),
        "res_factor": res_factor, "min_valid_fraction": ck["min_valid"],
        "decision_metrics": "core",
    }
    config_path = cfg.get("config_path")
    bundle = {
        "experiment": cfg.get("experiment", "matched_footprint_panel_v2"),
        "protocol": {"path": PROTOCOL_V2_PATH, "sha256": _frozen_sha256(PROTOCOL_V2_PATH)},
        "config": {"path": config_path, "sha256": _frozen_sha256(config_path)},
        "regime_rule": _REGIME_RULE,
        "panel_ids": panel_ids, "candidates": cands, "primary_reference": primary_id,
        "footprint": footprint,
        "support_floor": floor,
        "supports": plan,
        "warnings": warns,
        "adequacy": adequacy_info,
        "panel_raw": raw,
        "comparability": {
            "assess_cell": "comparability.assess_cell(tol=0.05, min_cells=10)",
            "regime_by_cell": {"honest": _regime_table(raw["honest"]),
                               "diagnostic": _regime_table(raw["diagnostic"])},
            "low_power_cells": low_power, "unassessed_cells": unassessed},
        "regime_violation": {"flag": bool(violations), "cells": violations},
        "resolution_control": resolution_control,
        "primary": primary,
        "hypotheses": hyp,
        "limitations": list(LIMITATIONS_V2),
        "provenance": provenance,
        "scope_note": _HONEST_NOTE,
        "panel_note": cf.PANEL_NOTE,
        "prohibited_claims": gaps.prohibited_claims(),
    }
    path = _write_bundle(bundle, out, _PANEL_BUNDLE_NAME) if out is not None else None
    _print_panel_summary(bundle, path)
    return bundle


def _print_panel_summary(b, path=None):
    """Plain, honest one-screen summary of a v2 panel bundle (ASCII-only output)."""
    def p(line=""):
        print(_ascii(line).rstrip())

    p("=" * 78)
    p("TerraTrace matched-footprint benchmark v2 -- REFERENCE PANEL")
    p("=" * 78)
    p(f"protocol: {b['protocol']['path']} (frozen)   config: {b['config']['path'] or 'n/a'}")
    fp, fl, sup = b["footprint"], b["support_floor"], b["supports"]
    lim = fp["limiting_unit"]
    p(f"footprint: {fp['extent_m']:.0f} m common extent "
      f"({'REDUCED from' if fp['reduced'] else 'requested'} {_fmt_m(fp['requested_m'])} m; "
      f"limiting unit {lim} provides {fp['available_m'][lim]:.0f} m untruncated)")
    p(f"support floor: {fl['floor_m']:.0f} m (limiting {fl['limiting_unit']}; effective "
      f"resolution = {b['provenance']['res_factor']:g} x source spacing, a heuristic)")
    p(f"honest supports (evidence): {', '.join(f'{s:g}' for s in sup['honest_m']) or 'none'} m"
      f"   diagnostic (NEVER evidence): "
      f"{', '.join(f'{s:g}' for s in sup['diagnostic_m']) or 'none'} m")
    for w in b["warnings"]:
        p(f"WARNING: {w}")
    p(f"candidates: {', '.join(b['candidates'])}")

    honest = b["panel_raw"]["honest"]
    if honest:
        p("")
        p("HONEST cells, core lens -- recommended unit [regime]:")
        p(f"  {'reference':<18}{'status':<14}"
          + "".join(f"{f'{s:g} m':<46}" for s in honest["supports_m"]))
        for r in honest["references"]:
            p(f"  {r['id']:<18}{r['status']:<14}" + "".join(
                f"{_cell_label(c) + ' [' + c['comparability']['regime'] + ']':<46}"
                for c in r["cells"]))
        p("")
        p("expectations (evaluated over HONEST supports only):")
        for r in honest["references"]:
            d = r["expectation"]["declared"] or {}
            p(f"  {r['id']:<18}{d.get('type', '-')} {d.get('unit', '-')} -> "
              f"{r['expectation']['outcome']:<8} counts_as_confirmation="
              f"{r['counts_as_confirmation']}")
        p(f"panel specificity (honest supports): {honest['summary']['specificity']['verdict']}")
    diag = b["panel_raw"]["diagnostic"]
    if diag:
        p("")
        p(f"{_DIAGNOSTIC_LABEL}:")
        for r in diag["references"]:
            p(f"  {r['id']:<18}" + "; ".join(
                f"{c['support_m']:g} m: {_cell_label(c)} [{c['comparability']['regime']}]"
                for c in r["cells"]))

    rc = b["resolution_control"]
    p("")
    if rc["run"]:
        ch, cd = rc["changed_honest"], rc["changed_diagnostic"]
        p(f"resolution control (every unit low-passed to {rc['target_fwhm_m']:.0f} m FWHM): "
          f"{len(ch)} honest cell(s) changed"
          + (": " + "; ".join(f"{r['reference']}@{r['support_m']:g} m "
                              f"{r['raw_recommendation']} -> {r['matched_recommendation']}"
                              for r in ch) if ch else ""))
        p(f"  diagnostic cells changed (not evidence): {len(cd)}")
    else:
        p(f"resolution control: not run ({rc['reason']})")

    pr = b["primary"]
    if pr.get("evaluated"):
        p(f"primary {pr['reference_id']} lens ablation @ {pr['support_m']:g} m: " + "; ".join(
            f"{k}={v['recommended_unit'] or v['result_state']}"
            for k, v in pr["lens_ablation"].items()))
        st = pr.get("adversarial")
        if st is None:
            p("primary adversarial stress test: not run")
        elif st.get("error"):
            p(f"primary adversarial stress test: ERROR ({st['error']})")
        else:
            p(f"primary adversarial stress test (exploratory trust bounds): {st['verdict']}, "
              f"stable {st['stable_fraction']:.2f} over {st['n_perturbations']} perturbations; "
              f"reversing: {', '.join(st['reversing_conditions']) or 'none'}")
    else:
        p(f"primary reference: not evaluated ({pr.get('reason')})")

    p("")
    for k in ("H1", "H2", "H3", "H4"):
        h = b["hypotheses"][k]
        p(f"{k} {_HYP_NAMES[k]:<14}: {h['verdict'].upper()} -- {h['reason']}")
        if h.get("qualifier"):
            p(f"   {h['qualifier']}")
        if k == "H3" and h["diagnostic"]["primary_by_support"]:
            p("   diagnostic, not evidence (primary, raw -> resolution-matched): " + "; ".join(
                f"{r['support_m']:g} m {r['raw_recommendation'] or r['raw_state']} -> "
                f"{r['matched_recommendation'] or r['matched_state']}"
                for r in h["diagnostic"]["primary_by_support"]))
        if k == "H4" and h["counts"]:
            p("   " + ", ".join(f"{s}={n}" for s, n in sorted(h["counts"].items())) + "  ("
              + "; ".join(f"{rid}: {v['recommended_unit'] or '-'} {v['adequacy']}"
                          for rid, v in h["evidence"].items()) + ")")
    if b["regime_violation"]["flag"]:
        p(f"REGIME VIOLATION: {len(b['regime_violation']['cells'])} honest-support cell(s) "
          f"outside the honest regime -- H1-H3 are inconclusive")
    p("")
    p("LIMITATIONS (stated before the run, protocol v2):")
    for line in b["limitations"]:
        p(f"  - {line}")
    p(f"NOTE: {_HONEST_NOTE}")
    if path:
        p(f"[bundle] wrote {path}")


def run_real_panel(cfg, out="artifacts/mf_panel"):
    """Front door for the REAL v2 reference panel: load per-body metric grids for
    every unit (rasterio seam), then run the pure core. Raises :class:`ImportError`
    (from :func:`load_panel_grids`) when rasterio is unavailable, so the CLI can
    print an honest blocked message instead of a traceback."""
    grids, spacings, rights = load_panel_grids(cfg)   # <-- the ONLY rasterio step
    return run_panel_from_grids(grids, spacings, rights, cfg, out=out)
