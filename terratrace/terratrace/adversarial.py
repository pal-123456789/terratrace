"""Adversarial robustness stress-test for a matched-footprint analog relationship.

WHY THIS EXISTS. The matched-footprint benchmark (:mod:`matched_benchmark`) removes
the extent/support confound and reports a *single* best-supported analog for one
reference under one lens. A single recommendation, however correct, says nothing
about HOW FAR it can be trusted: a 6x roughness gap and a hair's-breadth coin-flip
can both surface as "RECOMMEND_FOLLOW_UP". This module exists to attack that
recommendation rather than defend it. It re-runs the SAME engine decision under a
set of small, scientifically-justified perturbations and reports, honestly, the
fraction of conditions under which the answer survives and the conditions under
which it reverses.

STANCE (adversarial, not advocacy). The goal is to BREAK a proposed relationship, so
a "fragile" verdict is a success of the method, not a failure of it. We never tune a
perturbation to protect a favourite candidate; every perturbation is a bounded,
documented change a reviewer would accept as a legitimate "what if".

PERTURBATION FAMILIES (each a bounded, defensible change applied through the existing
``matched_cell`` / ``crop_center`` / ``lens_ablation_matched`` surface):
  * crop_origin      -- shift the crop centre by a few source pixels (AOI-boundary /
                        grid-origin sensitivity): the window is arbitrary to within a
                        few pixels, so the answer must not depend on exactly where it
                        is placed.
  * support_step     -- re-run at the neighbouring supports (0.67x and 1.5x the base
                        support): scale choice is a judgement call, so the answer must
                        persist across adjacent resolutions.
  * dem_perturbation -- three *realistic* DEM errors applied to every unit, each
                        separately: (a) bounded, SPATIALLY-CORRELATED noise (a smoothed
                        random field at a few % of the terrain's own std -- unlike a
                        uniform vertical offset, which is a morphology no-op), (b) a
                        mild regional tilt (a low-slope plane, which perturbs slope and
                        aspect descriptors), and (c) a mild 3x3 box-mean smoothing
                        (which perturbs high-frequency texture). Seeded, deterministic.
  * lens_family      -- re-ask the question under every OTHER decision lens (reusing
                        ``lens_ablation_matched``): a relationship that only one lens
                        sees is weaker than one many lenses agree on.
  * candidate_dropout-- drop one non-reference candidate at a time: does the winner
                        among the rest keep its identity (dropping a loser), and what
                        is recommended once the winner itself is removed?

The recommendation is "changed" for a perturbation when the recommended unit differs
from the UNPERTURBED baseline (``None`` for a TIE is handled uniformly: a tie that
resolves to a definite winner, or vice-versa, counts as a change). ``stable_fraction``
is the fraction of perturbations that leave the recommendation identical;
``reversing_conditions`` lists the labels that changed or removed it.

VERDICT. With a DEFINITE baseline analog the verdict follows ``stable_fraction``:
>= 0.8 is "robust", < 0.5 is "fragile", else "qualified". A baseline that establishes
NO analog (a TIE, ``recommended_unit`` is ``None``) can never be "robust" -- there is
no recommendation to be robust about. Such a baseline is "fragile" when perturbations
resolve the tie into CONFLICTING definite winners (any apparent analog is then an
artifact of the conditions) and "qualified" otherwise. For a tie baseline
``stable_fraction`` therefore measures persistence of the inconclusive state, not trust
in an analog, so it is reported but does not by itself drive the verdict.

Pure NumPy + the existing engine; deterministic given ``seed``; NaN-safe; no network.
All outputs are plain float/str/bool/list and JSON-serialisable.

Scope / claim firewall (inherited and NON-NEGOTIABLE): this is map-scale TERRAIN-
MORPHOLOGY screening only. The stress test probes the TRUST BOUNDS of a morphological
recommendation -- it is NOT a traversability, geologic-equivalence, site-access, or
mission-readiness claim, and a "robust" verdict upgrades none of those.

Evidence status: this is EXPLORATORY stress analysis. It characterises the stability
of a recommendation under perturbation; it is NOT confirmatory evidence and is kept
strictly separate from the frozen synthetic ground-truth validation. A robust verdict
means "hard to break with these perturbations", never "true".
"""
from __future__ import annotations

import math
import warnings

import numpy as np

from . import matched_benchmark as mb, synthetic

__all__ = ["stress_test", "DEFAULT_LENSES", "FAMILIES"]

# The six decision lenses the engine exposes; lens_family re-asks under each OTHER lens.
DEFAULT_LENSES = ("core", "extended", "geomorphic", "landform", "texture", "hydro")
# The perturbation families this module applies. ``perturbations=`` selects a subset.
FAMILIES = ("crop_origin", "support_step", "dem_perturbation", "lens_family",
            "candidate_dropout")

_NOISE_FRACTION = 0.03   # correlated DEM-error amplitude as a fraction of per-unit std
_TILT_DEG = 0.5          # mild regional tilt (low-slope plane), degrees
_SMOOTH_PASSES = 2       # box-mean passes used to spatially correlate the noise field
_ROBUST_AT = 0.8         # stable_fraction >= this -> "robust"
_FRAGILE_BELOW = 0.5     # stable_fraction < this  -> "fragile"


# --------------------------------------------------------------------------- #
# Small, deterministic, NaN-safe perturbation primitives.                     #
# --------------------------------------------------------------------------- #
def _box3(z):
    """3x3 box-mean (edge-padded, NaN-aware). A mild smoothing that attenuates the
    highest-frequency texture without shifting the mean or introducing a bias."""
    z = np.asarray(z, dtype=float)
    if z.ndim != 2 or z.size == 0:
        return z.copy()
    padded = np.pad(z, 1, mode="edge")
    rows, cols = z.shape
    stack = np.empty((9, rows, cols), dtype=float)
    k = 0
    for di in (0, 1, 2):
        for dj in (0, 1, 2):
            stack[k] = padded[di:di + rows, dj:dj + cols]
            k += 1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN neighbourhood -> NaN
        return np.nanmean(stack, axis=0)


def _correlated_noise(shape, rng, passes=_SMOOTH_PASSES):
    """A unit-std, spatially-CORRELATED random field (white noise smoothed a few times).

    Smoothing gives the field a finite correlation length (a few pixels), so adding it
    perturbs descriptors the way real DEM error does -- not as independent per-pixel
    salt-and-pepper. Renormalised to unit std AFTER smoothing so the caller controls
    the amplitude. Seeded via ``rng`` for determinism.
    """
    f = rng.standard_normal(shape)
    for _ in range(int(passes)):
        f = _box3(f)
    s = float(np.nanstd(f))
    if np.isfinite(s) and s > 0:
        f = f / s
    return f


def _tilt_plane(shape, src_spacing_m, angle_deg=_TILT_DEG):
    """A low-slope plane of inclination ``angle_deg`` along the grid diagonal.

    A uniform vertical offset is a morphology no-op (slope/relief are offset-invariant);
    a mild tilt is not -- it adds a small directional bias to slope and aspect, which is
    exactly the kind of mild, realistic error a stress test should probe.
    """
    g = math.tan(math.radians(float(angle_deg)))
    comp = g / math.sqrt(2.0)
    return synthetic.plane(shape, slope_x=comp, slope_y=comp,
                           dx=float(src_spacing_m), dy=float(src_spacing_m))


def _crop_offset(z, src_spacing_m, extent_m, dr, dc):
    """Centre-crop ``z`` to ``extent_m`` but with the crop centre shifted by (``dr``,
    ``dc``) source pixels (clamped to stay inside the array).

    Reuses :func:`matched_benchmark.crop_center` to compute the exact pixel count the
    matched protocol would use, so the returned grid is already the matched size: a
    later ``matched_cell`` at the same ``extent_m`` re-crops it to itself (a no-op) and
    only the ORIGIN has moved. If the array has no room to shift, the clamp returns the
    centred crop unchanged (origin sensitivity is simply unprobeable there).
    """
    z = np.asarray(z, dtype=float)
    _sub, info = mb.crop_center(z, src_spacing_m, extent_m)
    n = int(info["n_pixels"])
    rows, cols = z.shape
    r0 = int(min(max((rows - n) // 2 + int(dr), 0), rows - n))
    c0 = int(min(max((cols - n) // 2 + int(dc), 0), cols - n))
    return z[r0:r0 + n, c0:c0 + n]


def _sensible_support_m(x):
    """Round a support (metres) to the nearest 5 m, floored at 5 m -- so a 0.67x/1.5x
    step lands on a clean, defensible number rather than 60.3 m."""
    return max(5.0, round(float(x) / 5.0) * 5.0)


def _src_of(src_spacings, uid):
    """Source spacing for one unit (``src_spacings`` is a scalar or a per-unit dict)."""
    return src_spacings[uid] if isinstance(src_spacings, dict) else src_spacings


def _restrict(mapping, keys):
    """Restrict a per-unit dict to ``keys``; pass a scalar (or None) through unchanged."""
    if isinstance(mapping, dict):
        return {k: mapping[k] for k in keys if k in mapping}
    return mapping


# --------------------------------------------------------------------------- #
# The stress test.                                                            #
# --------------------------------------------------------------------------- #
def stress_test(units, src_spacings, reference_id, base_extent_m, base_support_m,
                decision_metrics="core", rights=None, perturbations=None, seed=0):
    """Attack the matched-footprint recommendation and report how far it is trustworthy.

    Runs the UNPERTURBED :func:`matched_benchmark.matched_cell` for the baseline, then
    re-runs the SAME engine decision under each selected perturbation family and records
    whether the recommended unit changed. See the module docstring for the families and
    the (adversarial, exploratory) stance.

    Parameters mirror ``matched_cell`` plus:
      perturbations : iterable of family names to run, or None for all of :data:`FAMILIES`.
      seed          : seeds the (only) stochastic family, dem_perturbation's noise.

    Returns a JSON-serialisable dict (plain float/str/bool/list); deterministic given
    ``seed`` and the unit ordering.
    """
    keys = list(units)
    active = set(FAMILIES) if perturbations is None else {p for p in perturbations}

    base = mb.matched_cell(units, src_spacings, reference_id, base_extent_m,
                           base_support_m, decision_metrics=decision_metrics, rights=rights)
    base_rec = base.get("recommended_unit")
    base_state = base.get("result_state")

    perts = []

    def _run(units_d, src_d, support_m, lens, rights_d, extent_m=base_extent_m):
        """One perturbed decision -> (recommended_unit, result_state). Defensive: the
        engine does not raise on reasonable input, but a perturbation that somehow
        breaks comparability is recorded as a (reversing) ERROR rather than crashing."""
        try:
            cell = mb.matched_cell(units_d, src_d, reference_id, extent_m, support_m,
                                   decision_metrics=lens, rights=rights_d)
            return cell.get("recommended_unit"), cell.get("result_state")
        except Exception as exc:  # pragma: no cover - defensive, not expected on valid input
            return None, "ERROR:%s" % type(exc).__name__

    def _add(family, label, rec, state):
        perts.append({"family": family, "label": label,
                      "recommended_unit": rec, "result_state": state,
                      "changed": bool(rec != base_rec)})

    # --- crop_origin: shift the AOI centre by a few source pixels ------------- #
    if "crop_origin" in active:
        _sub, info_ref = mb.crop_center(units[reference_id],
                                        _src_of(src_spacings, reference_id), base_extent_m)
        step = max(1, int(round(0.05 * int(info_ref["n_pixels"]))))
        for tag, dr, dc in (("row+", step, 0), ("row-", -step, 0),
                            ("col+", 0, step), ("col-", 0, -step)):
            shifted = {u: _crop_offset(units[u], _src_of(src_spacings, u),
                                       base_extent_m, dr, dc) for u in keys}
            rec, state = _run(shifted, src_spacings, base_support_m, decision_metrics, rights)
            _add("crop_origin", "crop_origin:%s%dpx" % (tag, step), rec, state)

    # --- support_step: neighbouring supports (0.67x, 1.5x) -------------------- #
    if "support_step" in active:
        for tag, mult in (("0.67x", 0.67), ("1.5x", 1.5)):
            sup = _sensible_support_m(base_support_m * mult)
            rec, state = _run(units, src_spacings, sup, decision_metrics, rights)
            _add("support_step", "support:%s(%gm)" % (tag, sup), rec, state)

    # --- dem_perturbation: correlated noise, mild tilt, mild smoothing -------- #
    if "dem_perturbation" in active:
        rng = np.random.default_rng(int(seed))
        noisy = {}
        for u in keys:                                   # draw per unit, in order (deterministic)
            z = np.asarray(units[u], dtype=float)
            sd = float(np.nanstd(z))
            amp = _NOISE_FRACTION * (sd if np.isfinite(sd) and sd > 0 else 1.0)
            noisy[u] = z + amp * _correlated_noise(z.shape, rng, _SMOOTH_PASSES)
        rec, state = _run(noisy, src_spacings, base_support_m, decision_metrics, rights)
        _add("dem_perturbation", "dem_noise:correlated~%.0f%%std" % (_NOISE_FRACTION * 100),
             rec, state)

        tilted = {u: np.asarray(units[u], dtype=float)
                  + _tilt_plane(np.asarray(units[u]).shape, _src_of(src_spacings, u), _TILT_DEG)
                  for u in keys}
        rec, state = _run(tilted, src_spacings, base_support_m, decision_metrics, rights)
        _add("dem_perturbation", "dem_tilt:%.1fdeg" % _TILT_DEG, rec, state)

        smoothed = {u: _box3(units[u]) for u in keys}
        rec, state = _run(smoothed, src_spacings, base_support_m, decision_metrics, rights)
        _add("dem_perturbation", "dem_smooth:3x3box", rec, state)

    # --- lens_family: does the recommendation hold across the OTHER lenses? --- #
    if "lens_family" in active:
        other = tuple(l for l in DEFAULT_LENSES if l != decision_metrics)
        try:
            la = mb.lens_ablation_matched(units, src_spacings, reference_id, base_extent_m,
                                          base_support_m, lenses=other, rights=rights)
        except Exception:  # pragma: no cover - defensive
            la = {}
        for lens in other:
            v = la.get(lens, {})
            _add("lens_family", "lens:%s" % lens,
                 v.get("recommended_unit"),
                 v.get("result_state", "ERROR:lens"))

    # --- candidate_dropout: drop one non-reference candidate at a time -------- #
    if "candidate_dropout" in active:
        for c in [u for u in keys if u != reference_id]:
            keep = [u for u in keys if u != c]
            if reference_id not in keep:
                continue
            units_sub = {u: units[u] for u in keep}
            rec, state = _run(units_sub, _restrict(src_spacings, keep), base_support_m,
                              decision_metrics, _restrict(rights, keep))
            _add("candidate_dropout", "drop:%s" % c, rec, state)

    n = len(perts)
    n_changed = sum(1 for p in perts if p["changed"])
    stable_fraction = float((n - n_changed) / n) if n else 1.0
    reversing = [p["label"] for p in perts if p["changed"]]
    if n == 0:
        verdict = "qualified"            # nothing probed -> cannot assess
    elif base_rec is None:
        # No analog established at baseline: a (non-)recommendation cannot be "robust".
        # Fragile when perturbations resolve the tie into conflicting definite winners
        # (any apparent analog is an artifact of the conditions); else merely qualified.
        distinct = {p["recommended_unit"] for p in perts
                    if p["recommended_unit"] is not None}
        verdict = "fragile" if len(distinct) >= 2 else "qualified"
    elif stable_fraction >= _ROBUST_AT:
        verdict = "robust"
    elif stable_fraction < _FRAGILE_BELOW:
        verdict = "fragile"
    else:
        verdict = "qualified"

    return {
        "baseline": {
            "recommended_unit": base_rec,
            "result_state": base_state,
            "extent_m": float(base_extent_m),
            "support_m": float(base_support_m),
        },
        "perturbations": perts,
        "n_perturbations": int(n),
        "n_changed": int(n_changed),
        "stable_fraction": stable_fraction,
        "reversing_conditions": reversing,
        "verdict": verdict,
        # provenance (informative, JSON-safe)
        "reference_id": reference_id,
        "decision_metrics": decision_metrics,
        "seed": int(seed),
    }
