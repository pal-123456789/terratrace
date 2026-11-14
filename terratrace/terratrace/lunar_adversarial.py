"""Adversarial stress test for the lunar panel: how far can the ordering be broken?

WHY THIS EXISTS
---------------
The v2 lunar panel (`scripts/lunar_sites_v2.py`) reports that `earth_nevada_basin` is the sole
non-dominated Earth candidate at all six lunar references and all three supports -- 18 of 18 cells.
A single recommendation, however correct, says nothing about how far it can be trusted: a wide gap
and a coin-flip both surface as "non-dominated". This module attacks the answer instead of
defending it, and reports the fraction of conditions under which it survives and the conditions
under which it reverses.

STANCE: adversarial, not advocacy. A "fragile" verdict is a success of the method. No perturbation
may be tuned to protect the survivor, and none may be weakened after seeing the result -- which is
why the ranges live in `config/lunar_adversarial_v1.yml`, committed BEFORE the run, and why a test
asserts that this module's declared list and that file agree.

WHAT IS A PERTURBATION HERE
---------------------------
A perturbation is a *specification* for a whole panel evaluation:

    supports, footprint_m, centre_shift_m, resampling,
    border_ring, tail_fraction, array_perturbation, axes, pool

so the families are not special-cased code paths but points in one declared space. The driver reads
the real DEMs for the spec and this module turns the resulting arrays into layer-1 sets. That split
is deliberate: everything decision-shaped here is pure NumPy over arrays, so it is testable without
a single DEM on disk, while the data access stays in the driver where it can be checked against the
committed panel.

THE COMPARISON RULE IS NOT REIMPLEMENTED
----------------------------------------
`axes_of` is the SAME three declared axes the panel uses, and `layer1` calls the engine's own
`decision.non_dominated` on the same fractional distances. A stress test that re-derived the
comparison would be measuring a different comparison. `tests/test_lunar_adversarial.py` pins both
against the panel script itself.

SCOPE (inherited, non-negotiable): map-scale terrain-MORPHOLOGY screening only. A "robust" verdict
means "hard to break with these perturbations"; it is never "true", and it upgrades no claim about
traversability, geologic equivalence, site access or mission readiness. Exploratory robustness
analysis, not confirmation.
"""
from __future__ import annotations

import numpy as np

from . import adversarial as _adv, decision, features

__all__ = [
    "AXES", "FAMILIES", "BASE_FOOTPRINT_M", "BASE_SUPPORTS_M", "THRESHOLDS",
    "axes_of", "fractional_distance", "layer1", "panel_layer1",
    "apply_border_ring", "apply_tail_mask", "perturb_arrays",
    "declared_specs", "informational_specs", "declared_labels", "base_spec",
    "compare_to_baseline", "verdict", "stability",
]

AXES = ("mean_slope_deg", "mean_relief3_m", "elev_std_m")
BASE_FOOTPRINT_M = 9000.0
BASE_SUPPORTS_M = (500.0, 750.0, 1000.0)

FAMILIES = ("grid_origin", "support_jitter", "footprint", "resampling", "mask",
            "dem_perturbation", "descriptor_dropout", "candidate_dropout", "pool_change")

# Declared in config/lunar_adversarial_v1.yml before the run; mirrored here so the two can be
# compared mechanically. Same thresholds the Mars-panel stress test uses, so the two panels are
# read on one scale.
THRESHOLDS = {"robust_at": 0.80, "fragile_below": 0.50}

_ARRAY_PERTURBATIONS = ("noise3pct", "tilt0.5deg", "smooth3x3")
_NOISE_FRACTION = 0.03      # of each unit's OWN std, matching adversarial.py
_TILT_DEG = 0.5             # matching adversarial.py
_SMOOTH_PASSES = 2          # matching adversarial.py
_TAIL_FRACTION = 0.10       # fraction of cells masked, per unit, symmetric in |z - median|


# --------------------------------------------------------------------------- #
# The comparison, identical to the panel's                                   #
# --------------------------------------------------------------------------- #
def axes_of(z, dx, axes=AXES):
    """The three declared axes, NaN-safe. Byte-for-byte the panel's own definition.

    `nanmean`/`nanstd` over the whole array is what excludes both the warp's empty cells and the
    NaN border the stencils leave at the window edge -- so this is the same measurement the panel
    made, and a masked or perturbed array flows through it unchanged.
    """
    z = np.asarray(z, dtype=float)
    slope = features.slope_deg(z, dx, dx)
    relief = features.relief(z, window=3, alpha=0.0)
    finite = np.isfinite(z)
    allv = {"mean_slope_deg": float(np.nanmean(slope)),
            "mean_relief3_m": float(np.nanmean(relief)),
            "elev_std_m": float(np.nanstd(z[finite]))}
    return {k: allv[k] for k in axes}


def fractional_distance(unit_axes, ref_id, axes=AXES):
    """Distance to the reference as a fraction of the reference's own value, per axis.

    Unchanged from the panel: the axes are made commensurate by dividing by the reference's own
    value, so no weighting is invented and there is no composite score.
    """
    ref = unit_axes[ref_id]
    out = {}
    for uid, a in unit_axes.items():
        if uid == ref_id:
            continue
        row = []
        for k in axes:
            denom = abs(ref[k])
            row.append(abs(a[k] - ref[k]) / denom if denom else float("nan"))
        out[uid] = row
    return out


def layer1(unit_axes, ref_id, axes=AXES):
    """The non-dominated set, via the engine's own Pareto rule. Sorted for comparability."""
    return sorted(decision.non_dominated(fractional_distance(unit_axes, ref_id, axes)))


def panel_layer1(arrays, dx, reference_ids, candidate_ids, axes=AXES):
    """One panel evaluation: ``{reference_id: [sorted layer-1 members]}``.

    ``arrays`` maps unit id to a 2-D destination-grid array. The CANDIDATE POOL IS EXPLICIT and
    every reference is compared against ``candidate_ids`` only -- the references are not mutual
    candidates. That is the panel's structure, and getting it wrong is not a subtle error: the
    first version of the stress driver fed all six lunar sites in as one pool, so they competed
    with each other, and the baseline reproduction check rejected it instead of reporting it.

    Every unit must share the grid, so the caller is responsible for the comparability gate --
    which the driver runs on the actual records.
    """
    cands = [c for c in candidate_ids if c in arrays]
    if not cands:
        raise KeyError("no candidate unit is present in the comparison")
    ax = {uid: axes_of(z, dx, axes) for uid, z in arrays.items()}
    bad = [uid for uid, a in ax.items() if not all(np.isfinite(v) for v in a.values())]
    if bad:
        raise ValueError(
            f"unit(s) {bad} produced a non-finite axis, so no ordering over them is meaningful. "
            f"Raised rather than silently ranked.")
    out = {}
    for ref in reference_ids:
        if ref not in ax:
            raise KeyError(f"reference unit {ref!r} absent from the comparison")
        pool = {ref: ax[ref]}
        pool.update({c: ax[c] for c in cands})
        out[ref] = layer1(pool, ref, axes)
    return out


# --------------------------------------------------------------------------- #
# The masks and the DEM perturbations                                        #
# --------------------------------------------------------------------------- #
def apply_border_ring(z, ring=1):
    """Drop the outermost ``ring`` cells. Edge cells are where warp coverage is thinnest."""
    z = np.asarray(z, dtype=float)
    if ring <= 0:
        return z.copy()
    if 2 * ring >= min(z.shape):
        return np.full(z.shape, np.nan)
    out = np.full(z.shape, np.nan)
    out[ring:-ring, ring:-ring] = z[ring:-ring, ring:-ring]
    return out


def apply_tail_mask(z, fraction=_TAIL_FRACTION):
    """Mask the ``fraction`` of cells furthest from the window median, both tails.

    The rule is applied per unit with the SAME fraction, so it is symmetric across bodies: it asks
    whether a handful of extreme cells is driving the ordering, not whether one unit has outliers.
    """
    z = np.asarray(z, dtype=float)
    if fraction <= 0:
        return z.copy()
    finite = np.isfinite(z)
    n = int(finite.sum())
    if n == 0:
        return z.copy()
    k = int(round(fraction * n))
    if k <= 0:
        return z.copy()
    med = float(np.median(z[finite]))
    dev = np.abs(z - med)
    # Mark EXACTLY the k largest deviations rather than thresholding with `>=`, which over-masks
    # whenever the deviations tie -- and on a smooth window they tie a lot.
    idx = np.argsort(dev[finite], kind="stable")[max(0, n - k):]
    out = z.copy()
    flat = np.flatnonzero(finite.ravel())
    out.ravel()[flat[idx]] = np.nan
    return out


def perturb_arrays(arrays, kind, dx, seed=0):
    """Apply one declared DEM perturbation to every unit. Deterministic given ``seed``.

    Identical semantics to :mod:`terratrace.adversarial`, so the lunar and Mars panels are read on
    one scale. A uniform vertical offset is deliberately NOT offered: slope and relief are
    offset-invariant, so it would be a morphology no-op dressed up as a perturbation.
    """
    if kind not in _ARRAY_PERTURBATIONS:
        raise ValueError(f"unknown array perturbation {kind!r}; declared: {_ARRAY_PERTURBATIONS}")
    out = {}
    if kind == "noise3pct":
        rng = np.random.default_rng(int(seed))
        for uid in arrays:                       # drawn in order, so the seed is deterministic
            z = np.asarray(arrays[uid], dtype=float)
            sd = float(np.nanstd(z))
            amp = _NOISE_FRACTION * (sd if np.isfinite(sd) and sd > 0 else 1.0)
            out[uid] = z + amp * _adv.correlated_noise(z.shape, rng, _SMOOTH_PASSES)
    elif kind == "tilt0.5deg":
        for uid, z in arrays.items():
            z = np.asarray(z, dtype=float)
            out[uid] = z + _adv.tilt_plane(z.shape, dx, _TILT_DEG)
    else:                                        # smooth3x3
        for uid, z in arrays.items():
            out[uid] = _adv.box3(np.asarray(z, dtype=float))
    return out


# --------------------------------------------------------------------------- #
# The declared perturbation space                                            #
# --------------------------------------------------------------------------- #
def _spec(label, family, supports=BASE_SUPPORTS_M, footprint_m=BASE_FOOTPRINT_M,
          centre_shift_m=(0.0, 0.0), resampling="average", border_ring=0,
          tail_fraction=None, array_perturbation=None, axes=AXES,
          drop_units=(), add_units=(), counted=True, support_map=None):
    sup = tuple(float(s) for s in supports)
    if support_map is None:
        support_map = {f"{s:.0f}": f"{s:.0f}" for s in sup}
    return {"label": label, "family": family, "supports": sup,
            "footprint_m": float(footprint_m), "centre_shift_m": (float(centre_shift_m[0]),
                                                                  float(centre_shift_m[1])),
            "resampling": resampling, "border_ring": int(border_ring),
            "tail_fraction": (None if tail_fraction is None else float(tail_fraction)),
            "array_perturbation": array_perturbation, "axes": tuple(axes),
            "drop_units": tuple(drop_units), "add_units": tuple(add_units),
            "counted": bool(counted), "support_map": dict(support_map)}


def declared_specs():
    """The 30 counted perturbations, in the order the frozen config lists them."""
    s = []
    # --- grid_origin: the window is arbitrary to within a few hundred metres
    for tag, shift in (("+400m_e", (400.0, 0.0)), ("-400m_e", (-400.0, 0.0)),
                       ("+400m_n", (0.0, 400.0)), ("-400m_n", (0.0, -400.0))):
        s.append(_spec(f"grid_origin:{tag}", "grid_origin", centre_shift_m=shift))
    # --- support_jitter: move ONE support to its nearest valid divisor of the footprint.
    # The perturbed support is compared against the support it REPLACED, so the question asked is
    # "at 450 m instead of 500 m, does the answer change?" and not "is 450 m the same as the mean
    # of the other two".
    for frm, to in ((500.0, 450.0), (500.0, 600.0), (750.0, 900.0), (1000.0, 1500.0)):
        sup = tuple(to if x == frm else x for x in BASE_SUPPORTS_M)
        smap = {f"{to:.0f}": f"{frm:.0f}"} if to not in BASE_SUPPORTS_M else {}
        for x in BASE_SUPPORTS_M:
            if x != frm:
                smap[f"{x:.0f}"] = f"{x:.0f}"
        s.append(_spec("support_jitter:%d-to-%d" % (frm, to), "support_jitter", supports=sup,
                       support_map=smap))
    # --- footprint: is the answer a property of terrain, or of the 9000 m window?
    s.append(_spec("footprint:6000m", "footprint", footprint_m=6000.0))
    s.append(_spec("footprint:3000m", "footprint", footprint_m=3000.0))
    s.append(_spec("footprint:10500m@500", "footprint", supports=(500.0,), footprint_m=10500.0))
    s.append(_spec("footprint:9750m@750", "footprint", supports=(750.0,), footprint_m=9750.0))
    s.append(_spec("footprint:10000m@1000", "footprint", supports=(1000.0,), footprint_m=10000.0))
    # --- resampling: `average` is correct for downsampling; `nearest` is the strongest stress
    s.append(_spec("resampling:bilinear", "resampling", resampling="bilinear"))
    s.append(_spec("resampling:nearest", "resampling", resampling="nearest"))
    # --- mask: edges, and the extreme cells
    s.append(_spec("mask:border_ring1", "mask", border_ring=1))
    s.append(_spec("mask:tail10pct", "mask", tail_fraction=_TAIL_FRACTION))
    # --- dem: the same three perturbations the Mars panel uses
    s.append(_spec("dem:noise3pct", "dem_perturbation", array_perturbation="noise3pct"))
    s.append(_spec("dem:tilt0.5deg", "dem_perturbation", array_perturbation="tilt0.5deg"))
    s.append(_spec("dem:smooth3x3", "dem_perturbation", array_perturbation="smooth3x3"))
    # --- descriptor_dropout: the dependence audit says the axes span one dimension
    for a in AXES:
        keep = tuple(x for x in AXES if x != a)
        s.append(_spec(f"drop_axis:{a}", "descriptor_dropout", axes=keep))
    # --- candidate_dropout: one non-survivor removed at a time
    for uid in ("earth_nullarbor", "earth_llano_estacado", "earth_deccan_traps",
                "earth_snake_river_plain", "earth_harrat_khaybar", "earth_odadahraun"):
        s.append(_spec(f"drop_unit:{uid}", "candidate_dropout", drop_units=(uid,)))
    # --- pool_change: an eighth candidate the v2 panel never saw
    s.append(_spec("add_unit:earth_andean_volcano", "pool_change",
                   add_units=("earth_andean_volcano",)))
    return s


def informational_specs():
    """Reported, never counted. Removing the survivor is not a robustness probe.

    It asks a different question -- "who is second?" -- and a perturbation whose outcome is certain
    before it is run must not dilute a stability fraction.
    """
    return [_spec("info_drop_winner:earth_nevada_basin", "candidate_dropout",
                  drop_units=("earth_nevada_basin",), counted=False)]


def declared_labels():
    return [p["label"] for p in declared_specs()] + [p["label"] for p in informational_specs()]


def base_spec():
    """The unperturbed v2 panel spec: 9000 m, the three declared supports, area-weighted average."""
    return _spec("baseline", "baseline")


# --------------------------------------------------------------------------- #
# Scoring                                                                    #
# --------------------------------------------------------------------------- #
def compare_to_baseline(baseline, panel, support_map=None):
    """Per-cell agreement between a baseline panel and a perturbed one.

    ``baseline`` and ``panel`` are ``{reference_id: {support_key: sorted layer-1 list}}``. A cell
    CHANGES when its layer-1 set differs -- a member added, removed or swapped. Membership is what
    the panel's headline claim is about, so membership is what is compared.

    ``support_map`` says which BASELINE support each perturbed support is to be read against. It
    exists for two different reasons and both are honest bookkeeping, not convenience:

    * three footprint specs deliberately move ONE support (10500 m at 500 m, 9750 m at 750 m,
      10000 m at 1000 m), so they evaluate a single support and must be scored on that one;
    * the four support_jitter specs REPLACE a support (450 m instead of 500 m), and the question
      asked is "at 450 m instead of 500 m, does the answer change?" -- so 450 m is read against 500 m
      and not against the mean of the other two.

    A cell the perturbed panel does not have is not scored; a support it has that the baseline does
    not, or a mapping onto a support the baseline lacks, is an error and is raised. The first
    version scored every baseline support regardless, so the single-support specs reported twelve
    "reversals" each with an empty layer-1 set -- a measurement error wearing the costume of a
    finding.
    """
    changed, cells = [], 0
    smap = support_map or {}
    for ref in sorted(baseline):
        base_sups = set(baseline[ref])
        got_sups = set(panel.get(ref, {}))
        if not got_sups:
            raise ValueError(
                f"{ref}: the perturbed panel evaluated no support at all, so there is nothing to "
                f"compare against the baseline")
        for sup in sorted(got_sups):
            target = smap.get(sup, sup)
            if target not in base_sups:
                raise ValueError(
                    f"{ref}: perturbed support {sup} maps to baseline support {target}, which the "
                    f"baseline does not have ({sorted(base_sups)}). The two are not the same panel.")
            cells += 1
            want = list(baseline[ref][target])
            got = list(panel[ref][sup])
            if got != want:
                changed.append({"reference": ref, "support": sup, "baseline_support": target,
                                "baseline_layer1": want, "perturbed_layer1": got})
    return {"n_cells": cells, "n_changed": len(changed), "changed": changed,
            "stable_fraction": float((cells - len(changed)) / cells) if cells else 1.0,
            "supports_evaluated": sorted({s for ref in panel for s in panel[ref]})}


def verdict(stable_fraction, n_counted=0, thresholds=None):
    """The declared rule. No data, no tuning: the thresholds come from the frozen config."""
    t = thresholds or THRESHOLDS
    if n_counted <= 0:
        return "qualified"            # nothing probed -> nothing can be claimed
    if stable_fraction >= t["robust_at"]:
        return "robust"
    if stable_fraction < t["fragile_below"]:
        return "fragile"
    return "qualified"


def stability(rows, thresholds=None):
    """Aggregate per-perturbation rows into the headline numbers.

    PRIMARY metric is perturbation-level and deliberately strict: a perturbation is STABLE only if
    EVERY one of its site x support cells kept the baseline set. A single site flipping is a
    reversal, not a rounding error. The cell-level fraction is reported alongside and does not
    drive the verdict, and informational rows are excluded from both.
    """
    counted = [r for r in rows if r.get("counted", True)]
    n = len(counted)
    stable = [r["label"] for r in counted if r["n_changed"] == 0]
    reversing = [r["label"] for r in counted if r["n_changed"] != 0]
    cells = sum(r["n_cells"] for r in counted)
    changed_cells = sum(r["n_changed"] for r in counted)
    frac = float(len(stable) / n) if n else 1.0
    return {
        "n_counted_perturbations": int(n),
        "n_stable_perturbations": int(len(stable)),
        "stable_perturbations": stable,
        "reversing_perturbations": reversing,
        "perturbation_stable_fraction": frac,
        "n_cells": int(cells),
        "n_changed_cells": int(changed_cells),
        "cell_stable_fraction": float((cells - changed_cells) / cells) if cells else 1.0,
        "verdict": verdict(frac, n, thresholds),
        "informational": [{"label": r["label"], "n_changed": r["n_changed"],
                           "resulting_layer1": r.get("panel")}
                          for r in rows if not r.get("counted", True)],
    }
