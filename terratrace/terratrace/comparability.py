"""Honest-regime comparability gate for matched-footprint comparisons.

WHY THIS EXISTS (a real defect, found in a real run). A Mars-vs-Earth
matched-footprint run asked for a 40 km common window. The cached Earth DEM
tiles were smaller than that, so :func:`matched_benchmark.crop_center` clamped
each one to what the tile held (by design, and recorded as ``truncated=True``).
The realised windows were Mars 39.8 km, Nevada 36.1 km, Andes 33.2 km and
Craters of the Moon 24.4 km. The recommended analog had the SMALLEST window,
leaving a ~1.6x footprint mismatch in a run labelled "matched". The same run
compared Mars MOLA (463 m spacing, ~1389 m effective resolution) at 500 m and
1000 m supports, which is finer than the source resolves. The per-unit
provenance recorded both conditions, but the runner printed neither.

WHAT THIS DOES. It does bookkeeping over grid shapes, spacings and the
provenance that ``matched_benchmark.cell_provenance`` already records:

  * planning -- :func:`common_matched_extent` (the largest window EVERY unit can
    supply without truncation) and :func:`support_floor_m` /
    :func:`honest_supports` (the supports at or above every unit's effective
    resolution), so an honest cell can be chosen BEFORE it is run;
  * auditing -- :func:`assess_cell` + :func:`regime_label` judge a finished
    cell and name each problem (unit + numbers) in plain English.

The gate does not fix data. It cannot add pixels a tile does not have, or detail
a source does not resolve. What it does is label comparability honestly, so a
result is never presented as matched when it is not. The effective resolution is
the harness's ``factor * spacing`` rule (default 3x). That rule is a
conservative HEURISTIC, not a measured resolving capability (there is no MTF or
point-spread analysis behind it). The module only reads array shapes, is
deterministic, and every output is JSON-serialisable.

Scope / claim firewall (inherited): map-scale terrain-morphology screening only.
An "honest" label means the windows and supports are comparable under these
rules. It does not mean the analog is correct, and it is not a traversability,
geologic-equivalence, site-access, or mission-readiness claim.
"""
from __future__ import annotations

import numpy as np

from .matched_benchmark import effective_resolution_m

__all__ = [
    "available_extent_m",
    "common_matched_extent",
    "support_floor_m",
    "honest_supports",
    "assess_cell",
    "regime_label",
]


def _spacing_map(spacings, keys):
    """{uid: spacing_m} from one shared scalar or a per-unit dict; validated > 0."""
    if isinstance(spacings, dict):
        missing = sorted(k for k in keys if k not in spacings)
        if missing:
            raise KeyError(f"no spacing given for unit(s) {missing}")
        out = {k: float(spacings[k]) for k in keys}
    else:
        out = {k: float(spacings) for k in keys}
    bad = sorted(k for k, s in out.items() if not (np.isfinite(s) and s > 0))
    if bad:
        raise ValueError(f"spacing must be a positive number of metres; bad unit(s) {bad}")
    return out


def _m(x):
    """Metres for an issue string: '24360 m', '1389 m', '12.5 m'."""
    x = float(x)
    return f"{x:.0f} m" if x == round(x) else f"{x:.1f} m"


def available_extent_m(grid, spacing_m):
    """Physical side (metres) of the largest centred square ``grid`` can supply.

    ``min(rows, cols) * spacing_m``. This is the largest ``extent_m`` that
    :func:`matched_benchmark.crop_center` realises on this grid WITHOUT
    truncation.
    """
    shape = np.shape(grid)
    if len(shape) != 2:
        raise ValueError(f"expected a 2-D grid, got shape {shape}")
    return float(min(shape)) * float(spacing_m)


def common_matched_extent(grids, spacings, requested_extent_m=None):
    """Largest extent EVERY unit can provide with no truncation.

    ``spacings`` is one shared scalar or ``{uid: spacing_m}``. Returns
    ``{"extent_m", "limiting_unit", "available_m", "requested_m", "reduced"}``:
    ``extent_m = min(requested, min available)`` (just the min available when no
    request is given). ``limiting_unit`` is always the unit with the smallest
    available extent, i.e. the binding constraint (ties go to the first uid in
    sorted order). ``reduced`` is True only when that constraint actually cut the
    request down. Cropping every unit to ``extent_m`` cannot truncate any of them.
    """
    if not grids:
        raise ValueError("common_matched_extent needs at least one unit")
    keys = sorted(grids)
    sp = _spacing_map(spacings, keys)
    avail = {u: available_extent_m(grids[u], sp[u]) for u in keys}
    limiting = min(avail, key=avail.get)
    floor = avail[limiting]
    if requested_extent_m is None:
        req, extent, reduced = None, floor, False
    else:
        req = float(requested_extent_m)
        if not (np.isfinite(req) and req > 0):
            raise ValueError(f"requested_extent_m must be > 0, got {requested_extent_m!r}")
        extent, reduced = min(req, floor), bool(req > floor)
    return {"extent_m": float(extent), "limiting_unit": limiting,
            "available_m": avail, "requested_m": req, "reduced": reduced}


def support_floor_m(spacings, res_factor=3.0):
    """Finest support that is at or above EVERY unit's effective resolution.

    ``spacings`` is ``{uid: spacing_m}``. Returns ``{"floor_m", "limiting_unit",
    "effective_m"}``, where ``effective_m[uid] = res_factor * spacing`` (the
    heuristic in :func:`matched_benchmark.effective_resolution_m`) and the floor is
    their maximum (ties go to the first uid in sorted order).
    """
    if not isinstance(spacings, dict) or not spacings:
        raise TypeError("support_floor_m needs a non-empty {uid: spacing_m} dict")
    sp = _spacing_map(spacings, sorted(spacings))
    eff = {u: effective_resolution_m(s, res_factor) for u, s in sp.items()}
    limiting = max(eff, key=eff.get)
    return {"floor_m": eff[limiting], "limiting_unit": limiting, "effective_m": eff}


def honest_supports(supports, spacings, res_factor=3.0):
    """The ``supports`` (sorted, as floats) that are >= :func:`support_floor_m`.

    The floor is inclusive, which matches ``cell_provenance``: a support exactly at
    a unit's effective resolution carries no upsampling risk.
    """
    floor = support_floor_m(spacings, res_factor)["floor_m"]
    return sorted(float(s) for s in supports if float(s) >= floor)


def assess_cell(provenance, tol=0.05, min_cells=10):
    """Judge ONE cell's comparability from its per-unit provenance.

    ``provenance`` is ``{uid: cell_provenance-dict}`` (what ``matched_cell`` returns
    under ``"provenance"``). A cell is ``footprint_matched`` when no unit was
    truncated AND the max/min realised extent is ``<= 1 + tol``. The tolerance
    absorbs pixel rounding between spacings; it does not cover a truncated tile.
    It is ``honest`` when it is footprint-matched AND no unit is supported below
    its effective resolution. ``low_power_units`` (fewer than ``min_cells``
    support cells per side) is reported separately and does not affect
    ``honest``. Unit lists are sorted, and ``issues`` holds one plain-English
    string per problem, naming the unit and the numbers.
    """
    if not provenance:
        raise ValueError("assess_cell needs provenance for at least one unit")
    keys = sorted(provenance)
    ext = {u: float(provenance[u]["actual_extent_m"]) for u in keys}
    lo = min(ext, key=ext.get)
    hi = max(ext, key=ext.get)
    min_e, max_e = ext[lo], ext[hi]
    ratio = max_e / min_e if min_e > 0 else None
    within = ratio is not None and ratio <= 1.0 + float(tol)
    truncated = [u for u in keys if bool(provenance[u]["truncated"])]
    upsampling = [u for u in keys if bool(provenance[u]["upsampling_risk"])]
    low_power = [u for u in keys
                 if int(provenance[u]["support_cells_per_side"]) < int(min_cells)]
    matched = not truncated and within

    issues = []
    for u in truncated:
        p = provenance[u]
        issues.append(
            f"{u}: window truncated to {_m(p['actual_extent_m'])} "
            f"({int(p['n_source_pixels'])} px at {_m(p['src_spacing_m'])} spacing) -- the "
            f"source grid is smaller than the requested extent, so this unit is not on "
            f"the common footprint")
    if not within:
        shown = "undefined" if ratio is None else f"{ratio:.3f}"
        issues.append(
            f"footprint mismatch: realised extents run from {_m(min_e)} ({lo}) to "
            f"{_m(max_e)} ({hi}), max/min ratio {shown} > {1.0 + float(tol):.2f} allowed "
            f"-- descriptors are being compared over different physical windows")
    for u in upsampling:
        p = provenance[u]
        factor = float(p["effective_resolution_m"]) / float(p["src_spacing_m"])
        issues.append(
            f"{u}: support {_m(p['support_m'])} is below its effective resolution "
            f"{_m(p['effective_resolution_m'])} ({factor:g}x its {_m(p['src_spacing_m'])} "
            f"spacing) -- detail at this support is interpolated, not resolved by the source")
    for u in low_power:
        p = provenance[u]
        issues.append(
            f"{u}: only {int(p['support_cells_per_side'])} support cells per side at "
            f"{_m(p['support_m'])} support (fewer than {int(min_cells)}) -- low statistical "
            f"power for this unit's descriptor distributions")

    return {
        "footprint_matched": bool(matched),
        "extent_ratio": ratio,
        "min_extent_m": min_e,
        "max_extent_m": max_e,
        "truncated_units": truncated,
        "upsampling_units": upsampling,
        "low_power_units": low_power,
        "honest": bool(matched and not upsampling),
        "issues": issues,
    }


def regime_label(assessment):
    """One-line regime for an :func:`assess_cell` result.

    The base label is ``honest``, ``footprint-mismatched``,
    ``below-effective-resolution`` or
    ``footprint-mismatched+below-effective-resolution``. ``+low-power`` is
    appended whenever ``low_power_units`` is non-empty, including on ``honest``.
    """
    mismatched = not assessment["footprint_matched"]
    below = bool(assessment["upsampling_units"])
    if mismatched and below:
        label = "footprint-mismatched+below-effective-resolution"
    elif mismatched:
        label = "footprint-mismatched"
    elif below:
        label = "below-effective-resolution"
    else:
        label = "honest"
    if assessment["low_power_units"]:
        label += "+low-power"
    return label
