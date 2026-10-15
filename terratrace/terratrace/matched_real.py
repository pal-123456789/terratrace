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
and reprojecting it -- is isolated behind :func:`load_metric_grids`. Everything
downstream (:func:`run_from_grids`) is pure NumPy + the engine and is fully testable
offline by substituting synthetic metric grids (see tests/test_matched_real.py,
which mirrors tests/test_real_study_path.py). :func:`load_metric_grids` is therefore
the single part of this experiment that cannot be exercised in the rasterio-free
sandbox; it is exercised by the user's real run on the data machine.

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
]

# Defaults for the frozen real-run spec (config/matched_footprint.example.yml).
_DEFAULT_LENSES = ("core", "extended", "geomorphic", "landform", "texture", "hydro")
_DEFAULT_MISMATCH_RATIO = 10.0   # reference-extent / candidate-extent for the control
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

    This is the ONLY rasterio-dependent function in the module and the ONLY part of
    the experiment untestable in the sandbox. It raises :class:`ImportError` up front
    when rasterio is absent, so the runner can print an honest blocked message.
    """
    try:
        import rasterio  # noqa: F401  (probe: fail with a catchable ImportError if absent)
    except Exception as exc:  # ModuleNotFoundError / env issues both land here
        raise ImportError(
            "rasterio is required for the REAL matched-footprint run (windowed, "
            "per-body reprojected DEM reads); install it on the data machine") from exc
    import numpy as np
    from . import reproject as rp
    from rasterio.warp import transform_bounds

    units = list(cfg["units"])
    reference_id = cfg.get("reference_id") or next(
        (u["id"] for u in units if u.get("is_reference")), units[0]["id"])
    extent_m = float(cfg["extent_m"])
    mismatch_ratio = float(cfg.get("mismatch_ratio", _DEFAULT_MISMATCH_RATIO))

    grids, spacings, rights = {}, {}, {}
    for u in units:
        uid = u["id"]
        is_ref = (uid == reference_id) or bool(u.get("is_reference"))
        body = u.get("body", "mars" if is_ref else "earth")
        res = float(u.get("native_posting_m") or (extent_m / 100.0))
        read_extent = extent_m * (mismatch_ratio if is_ref else 1.0) * _READ_MARGIN
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
        grids[uid] = np.asarray(z, dtype=float)
        spacings[uid] = float(spacing)
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


def _write_bundle(bundle, out):
    """Write the JSON evidence bundle (deterministic: sort_keys) and return its path."""
    import json
    import os
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "matched_benchmark_real.json")
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
