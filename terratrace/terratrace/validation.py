"""Scientific-correctness validation for the TerraTrace engine.

A morphology engine is only credible if it provably behaves the way its claims
require. Most checks drive the *real* comparison pipeline (`study.compare_units`)
on synthetic terrains with KNOWN relationships and assert that the engine's
distances and Pareto decision come out the way geomorphometry says they must:

  * self-distance is zero (a unit compared with itself is identical);
  * slope/relief/ruggedness are invariant to a vertical offset and to a 90-deg
    rotation (they measure shape, not absolute height or orientation);
  * distance grows monotonically as a candidate is made rougher (the engine can
    actually DISCRIMINATE terrain, i.e. it has power);
  * a candidate closer on every axis DOMINATES and is the recommendation
    (dominance recovery), while an unrelated candidate is farther (null control);
  * a water/flat candidate is BLOCKED by eligibility, not silently compared;
  * the whole pipeline is deterministic (identical inputs -> identical hash).

A second group checks feature-level scientific correctness directly on the
morphology descriptors, independent of the pipeline:

  * profile, plan AND mean curvature all vanish on a tilted plane (a planar
    surface has no convexity);
  * the vector ruggedness measure is ~0 on a plane and rises strictly with
    added roughness amplitude, staying within [0, 1];
  * the Hurst scaling exponent is ~1 for a smooth linear ramp and ~0 for
    uncorrelated white noise.

A third group checks the two line-of-sight morphology descriptors against their
canonical analytic oracles on synthetic shapes with a KNOWN class:

  * topographic openness (Yokoyama 2002) is exactly 90 deg everywhere on a flat
    plane, rises above 90 (positive) / falls below 90 (negative) at a cone apex,
    and mirrors (negative > 90, positive < 90) at a bowl centre;
  * geomorphon landform classification (Jasiewicz & Stepinski 2013) labels a
    flat plane 'flat', a cone apex 'peak', a bowl centre 'pit' and a uniform
    tilt 'slope', and -- depending only on elevation DIFFERENCES -- is exactly
    invariant to a vertical offset (identical composition under +100 m).

Each check returns a uniform record; `run_validation()` aggregates them into a
hashed report that is both a test oracle and a publishable validation artifact.
Pure NumPy + the engine and its feature descriptors; no network, no rasterio.
"""
from __future__ import annotations

import numpy as np

from . import study, synthetic, provenance, features, openness, geomorphons

# Isolate the morphology math from aggregation smoothing: native == target gives
# an aggregation factor of 1, so features are computed on the grids as built.
_NATIVE = 10.0
_TARGET = 10.0
_SHAPE = (96, 96)
# core vector axes produced by compare_units, in order.
_CORE_AXES = ("slope", "relief", "ruggedness", "connectivity")


def _run(ref, cands, rights=None, decision_metrics="core", target=_TARGET, native=_NATIVE):
    """Drive the real engine: reference id 'ref' plus the candidate grids."""
    raw = {"ref": np.asarray(ref, dtype=float)}
    raw.update({k: np.asarray(v, dtype=float) for k, v in cands.items()})
    rr = {u: "verified_allowed" for u in raw}
    if rights:
        rr.update(rights)
    return study.compare_units(raw, rr, native, reference_id="ref",
                               target_support_m=target, min_valid=0.5,
                               source_label="validation", decision_metrics=decision_metrics)


def _result(name, passed, detail, **metrics):
    return {"name": name, "passed": bool(passed), "detail": detail, "metrics": metrics}


def _vec(pkg, uid):
    """Baseline distance vector for a candidate id (list of floats) or None."""
    v = pkg.get("baseline_vectors", {}).get(uid)
    return [float(x) for x in v] if v is not None else None


def _plane_with_noise(amp, seed, slope_x=0.02):
    """A gently sloped plane plus seeded roughness — a controllable terrain."""
    base = synthetic.plane(_SHAPE, slope_x=slope_x, dx=_NATIVE)
    return base + synthetic.rough_field(_SHAPE, amplitude=amp, seed=seed)


def _median_finite(arr):
    """Median of the finite entries of an array (nan if none are finite)."""
    a = np.asarray(arr, dtype=float).ravel()
    a = a[np.isfinite(a)]
    return float(np.median(a)) if a.size else float("nan")


# --- synthetic shapes + helpers for the openness / geomorphon oracles -------
# These checks exercise the line-of-sight descriptors directly (not through the
# comparison pipeline). Elevations are built in CELL units with unit spacing, so
# the sight-line angles depend only on the chosen gradient and are independent
# of any physical dx. A modest radius/search of 8 on the 96x96 grid keeps every
# ray well inside the data for the central cells under test.
_MORPH_DX = 1.0
_MORPH_LOS = 8                       # openness radius == geomorphon search
_CONE_SLOPE = 0.2                    # rise per cell -> ~11.3 deg faces (>> flat_deg)
_CONE_CENTER = (_SHAPE[0] // 2, _SHAPE[1] // 2)


def _radial_cone(sign):
    """A radial cone/bowl centred on a cell of the _SHAPE grid.

    ``sign=-1`` -> apex high (a cone/peak: z decreases with radius); ``sign=+1``
    -> centre low (a bowl/pit). The centre cell ``_CONE_CENTER`` is the unique
    extremum and every one of the eight rays leaving it is a constant-gradient
    face, so the expected openness value and landform class are unambiguous and
    sit far from any classifier boundary.
    """
    ci, cj = _CONE_CENTER
    ii, jj = np.indices(_SHAPE)
    radius_cells = np.hypot(ii - ci, jj - cj)
    return sign * _CONE_SLOPE * radius_cells


def _dominant_form(comp):
    """Most common landform name in a composition dict (FORM_NAMES breaks ties),
    mirroring geomorphons.geomorphon_signature."""
    counts = [comp[name] for name in geomorphons.FORM_NAMES]
    return geomorphons.FORM_NAMES[int(np.argmax(counts))]


def check_self_distance_zero(tol=1e-6):
    """A candidate identical to the reference must have an all-zero vector."""
    ref = _plane_with_noise(0.5, seed=1)
    pkg = _run(ref, {"twin": ref.copy()})
    v = _vec(pkg, "twin")
    worst = max(abs(x) for x in v) if v else float("inf")
    return _result("self_distance_zero", v is not None and worst <= tol,
                   f"identical twin max-axis distance {worst:.2e} (tol {tol:g})",
                   vector=v, recommended=pkg.get("recommended_unit"))


def check_translation_invariance(tol=1e-6):
    """Adding a constant elevation offset must not change any morphology axis
    (slope/relief/ruggedness/connectivity measure shape, not absolute height)."""
    ref = _plane_with_noise(0.5, seed=2)
    pkg = _run(ref, {"shifted": ref + 1000.0})
    v = _vec(pkg, "shifted")
    worst = max(abs(x) for x in v) if v else float("inf")
    return _result("translation_invariance", v is not None and worst <= tol,
                   f"+1000 m offset max-axis distance {worst:.2e} (tol {tol:g})",
                   vector=dict(zip(_CORE_AXES, v)) if v else None)


def check_rotation90_invariance(tol=0.05):
    """A 90-deg rotation preserves the (isotropic) slope/relief/ruggedness
    distributions, so those axes must stay ~0. Aspect is intentionally excluded
    (orientation changes), so this uses the core metric set."""
    ref = _plane_with_noise(0.6, seed=3, slope_x=0.03)
    pkg = _run(ref, {"rot": np.rot90(ref)})
    v = _vec(pkg, "rot")
    iso = dict(zip(_CORE_AXES, v)) if v else {}
    worst = max(abs(iso.get(a, float("inf"))) for a in ("slope", "relief", "ruggedness"))
    return _result("rotation90_invariance", v is not None and worst <= tol,
                   f"rot90 worst isotropic-axis distance {worst:.3f} (tol {tol:g})",
                   axes=iso)


def check_monotonic_roughness_discrimination():
    """Distance to a smooth reference must grow as a candidate is made rougher
    (the engine has real discriminating power, not noise)."""
    ref = synthetic.plane(_SHAPE, slope_x=0.02, dx=_NATIVE)
    amps = [0.1, 0.5, 1.5, 4.0]
    cands = {f"amp{i}": ref + synthetic.rough_field(_SHAPE, amplitude=a, seed=10 + i)
             for i, a in enumerate(amps)}
    pkg = _run(ref, cands)
    # ruggedness is axis index 2; also track the vector sum as an aggregate.
    rug = [(_vec(pkg, f"amp{i}") or [float("nan")] * 4)[2] for i in range(len(amps))]
    sums = [sum(_vec(pkg, f"amp{i}") or [float("nan")]) for i in range(len(amps))]
    mono_rug = all(rug[i] < rug[i + 1] for i in range(len(rug) - 1))
    mono_sum = all(sums[i] < sums[i + 1] for i in range(len(sums) - 1))
    return _result("monotonic_roughness_discrimination", mono_rug and mono_sum,
                   f"ruggedness-axis sequence {[round(x, 3) for x in rug]} strictly increasing",
                   ruggedness=rug, vector_sum=sums)


def check_dominance_recovery():
    """A candidate closer on every axis must DOMINATE and be recommended; the
    far candidate must not be in the top Pareto layer."""
    ref = synthetic.plane(_SHAPE, slope_x=0.02, dx=_NATIVE)
    near = ref + synthetic.rough_field(_SHAPE, amplitude=0.15, seed=21)
    far = ref + synthetic.rough_field(_SHAPE, amplitude=3.0, seed=22)
    pkg = _run(ref, {"near": near, "far": far})
    vn, vf = _vec(pkg, "near"), _vec(pkg, "far")
    dominates = vn is not None and vf is not None and all(a <= b for a, b in zip(vn, vf)) \
        and any(a < b for a, b in zip(vn, vf))
    rank = (pkg.get("frontier") or {}).get("rank", {})
    recommended = pkg.get("recommended_unit")
    passed = (dominates and recommended == "near"
              and pkg.get("result_state") == "RECOMMEND_FOLLOW_UP"
              and rank.get("near") == 1 and rank.get("far", 99) >= 2)
    return _result("dominance_recovery", passed,
                   f"state={pkg.get('result_state')} recommended={recommended} "
                   f"near_dominates_far={dominates} rank={rank}",
                   near=vn, far=vf, rank=rank)


def check_null_control():
    """A same-statistics twin (same generator, different seed) must be closer to
    the reference than a 5x-rougher impostor — distances track real similarity."""
    ref = _plane_with_noise(1.0, seed=31)
    twin = _plane_with_noise(1.0, seed=32)        # same amplitude, new realization
    impostor = _plane_with_noise(5.0, seed=33)    # much rougher
    pkg = _run(ref, {"twin": twin, "impostor": impostor})
    s_twin = sum(_vec(pkg, "twin") or [float("nan")])
    s_imp = sum(_vec(pkg, "impostor") or [float("nan")])
    return _result("null_control", s_twin < s_imp,
                   f"sum(dist) twin {s_twin:.3f} < impostor {s_imp:.3f}",
                   twin_sum=s_twin, impostor_sum=s_imp)


def check_water_candidate_blocked():
    """A flat/zero (water-proxy) candidate must be BLOCKED by eligibility even
    with verified rights — the water gate, not rights, excludes it."""
    ref = _plane_with_noise(0.8, seed=41)
    good = _plane_with_noise(0.8, seed=42)
    water = synthetic.constant(_SHAPE, 0.0)       # zero_fraction 1.0 > 0.6 -> BLOCKED
    pkg = _run(ref, {"good": good, "water": water})
    elig = pkg.get("eligibility", {}).get("water", {})
    passed = elig.get("eligible") is False and "BLOCKED" in str(elig.get("reason", "")) \
        and "water" not in pkg.get("baseline_vectors", {})
    return _result("water_candidate_blocked", passed,
                   f"water eligibility={elig.get('eligible')} reason={elig.get('reason')!r}",
                   eligibility=elig)


def check_determinism():
    """Identical inputs must yield an identical package hash (reproducibility)."""
    ref = _plane_with_noise(0.7, seed=51)
    cands = {"a": _plane_with_noise(0.3, seed=52), "b": _plane_with_noise(1.2, seed=53)}
    h1 = _run(ref, dict(cands))["package_hash"]
    h2 = _run(ref, dict(cands))["package_hash"]
    return _result("determinism", h1 == h2,
                   f"package_hash stable across runs ({h1[:12]}...)",
                   hash1=h1, hash2=h2)


def check_curvature_zero_on_plane(tol=1e-6):
    """Profile, plan AND mean curvature must all vanish on a tilted plane: a
    planar surface has zero convexity, so every curvature descriptor is ~0
    regardless of its (non-zero) slope."""
    z = synthetic.plane((21, 21), slope_x=0.2, slope_y=0.1, dx=1.0)
    prof = _median_finite(features.profile_curvature(z, dx=1.0))
    plan = _median_finite(features.plan_curvature(z, dx=1.0))
    mean = _median_finite(features.mean_curvature(z, dx=1.0))
    worst = max(abs(prof), abs(plan), abs(mean))
    return _result("curvature_zero_on_plane", worst < tol,
                   f"tilted-plane median |curvature| profile {prof:.2e} "
                   f"plan {plan:.2e} mean {mean:.2e} (worst {worst:.2e} < "
                   f"tol {tol:g})",
                   profile=prof, plan=plan, mean=mean)


def check_vrm_discriminates_roughness(amps=(0.0, 0.3, 1.0, 3.0), seed=71, tol=1e-9):
    """Vector ruggedness is ~0 on a plane and rises strictly as seeded roughness
    of growing amplitude is added to it, always staying within [0, 1] — a
    slope-decoupled ruggedness measure with genuine discriminating power."""
    base = synthetic.plane(_SHAPE, slope_x=0.02, dx=1.0)
    seq = [_median_finite(features.vector_ruggedness(
               base + synthetic.rough_field(_SHAPE, amplitude=a, seed=seed), dx=1.0))
           for a in amps]
    strictly_up = all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))
    bounded = all(0.0 <= s <= 1.0 for s in seq)
    plane_zero = seq[0] <= tol
    return _result("vrm_discriminates_roughness",
                   strictly_up and bounded and plane_zero,
                   f"VRM median sequence {[round(s, 4) for s in seq]} strictly "
                   f"increasing in [0,1] (plane {seq[0]:.2e} ~ 0)",
                   sequence=seq, amplitudes=list(amps))


def check_roughness_hurst_sane(tol=1e-6, noise_max=0.1):
    """The roughness scaling (Hurst) exponent must separate a perfectly smooth
    gradient from uncorrelated roughness: ~1 for a linear ramp (long-range
    correlated) and ~0 (<0.1) for white noise. The ramp uses a square grid, so
    its structure function scales exactly as the lag."""
    ramp = synthetic.ramp_x(_SHAPE, rise_per_pixel=1.0)
    noise = synthetic.rough_field(_SHAPE, amplitude=1.0, seed=81)
    h_ramp = features.hurst_exponent(ramp, dx=1.0)
    h_noise = features.hurst_exponent(noise, dx=1.0)
    ramp_ok = np.isfinite(h_ramp) and abs(h_ramp - 1.0) < tol
    noise_ok = np.isfinite(h_noise) and h_noise < noise_max
    return _result("roughness_hurst_sane", ramp_ok and noise_ok,
                   f"Hurst ramp {h_ramp:.6f} (|Δ1| < {tol:g}) vs white noise "
                   f"{h_noise:.4f} (< {noise_max:g})",
                   hurst_ramp=float(h_ramp), hurst_noise=float(h_noise))


def check_openness_flat(tol=1e-6):
    """A perfectly flat surface has BOTH positive and negative topographic
    openness equal to exactly 90 deg at every cell: no sight line in any of the
    eight azimuths goes up or down, so every zenith and nadir angle is 90."""
    z = synthetic.constant(_SHAPE, 100.0)
    pos = openness.positive_openness(z, dx=_MORPH_DX, radius=_MORPH_LOS)
    neg = openness.negative_openness(z, dx=_MORPH_DX, radius=_MORPH_LOS)
    dev_pos = float(np.nanmax(np.abs(pos - 90.0)))
    dev_neg = float(np.nanmax(np.abs(neg - 90.0)))
    worst = max(dev_pos, dev_neg)
    return _result("openness_flat", worst < tol,
                   f"flat-plane max |openness-90| positive {dev_pos:.2e} "
                   f"negative {dev_neg:.2e} (worst {worst:.2e} < tol {tol:g})",
                   positive_dev=dev_pos, negative_dev=dev_neg)


def check_openness_peak():
    """At a cone apex every sight line descends, so POSITIVE (sky) openness rises
    above 90 deg while NEGATIVE (ground) openness drops below 90 deg."""
    ci, cj = _CONE_CENTER
    z = _radial_cone(-1.0)                       # apex high
    pos = float(openness.positive_openness(z, dx=_MORPH_DX, radius=_MORPH_LOS)[ci, cj])
    neg = float(openness.negative_openness(z, dx=_MORPH_DX, radius=_MORPH_LOS)[ci, cj])
    return _result("openness_peak", pos > 90.0 and neg < 90.0,
                   f"cone apex positive openness {pos:.3f} (>90) and negative "
                   f"openness {neg:.3f} (<90)",
                   positive=pos, negative=neg)


def check_openness_pit_mirror():
    """A pit mirrors a peak: at a bowl centre every sight line ascends, so
    NEGATIVE openness rises above 90 deg while POSITIVE openness drops below."""
    ci, cj = _CONE_CENTER
    z = _radial_cone(1.0)                        # centre low
    pos = float(openness.positive_openness(z, dx=_MORPH_DX, radius=_MORPH_LOS)[ci, cj])
    neg = float(openness.negative_openness(z, dx=_MORPH_DX, radius=_MORPH_LOS)[ci, cj])
    return _result("openness_pit_mirror", neg > 90.0 and pos < 90.0,
                   f"bowl centre negative openness {neg:.3f} (>90) and positive "
                   f"openness {pos:.3f} (<90)",
                   positive=pos, negative=neg)


def check_geomorphon_flat():
    """A flat plane is classified 'flat' over essentially the whole grid: no
    direction rises or falls past the flatness threshold, so every cell has
    ternary counts (n_plus, n_minus) == (0, 0)."""
    z = synthetic.constant(_SHAPE, 100.0)
    comp = geomorphons.composition(z, dx=_MORPH_DX, search=_MORPH_LOS)
    frac = comp["flat"]
    dominant = _dominant_form(comp)
    return _result("geomorphon_flat", frac > 0.95 and dominant == "flat",
                   f"flat-plane composition['flat']={frac:.4f} (>0.95), "
                   f"dominant form {dominant!r}",
                   flat_fraction=frac, dominant=dominant)


def check_geomorphon_cone_peak():
    """The apex cell of a radial cone classifies as 'peak' (FORM_NAMES index 1):
    terrain falls away in all eight directions (n_plus == 8)."""
    ci, cj = _CONE_CENTER
    code = int(geomorphons.landforms(_radial_cone(-1.0), dx=_MORPH_DX,
                                     search=_MORPH_LOS)[ci, cj])
    name = geomorphons.FORM_NAMES[code] if code >= 0 else "unclassified"
    expected = geomorphons.FORM_NAMES.index("peak")
    return _result("geomorphon_cone_peak", code == expected,
                   f"cone apex form {name!r} (code {code}; expected 'peak'={expected})",
                   code=code, form=name)


def check_geomorphon_bowl_pit():
    """The centre cell of a radial bowl classifies as 'pit' (the antisymmetric
    mirror of the cone apex): terrain rises in all eight directions."""
    ci, cj = _CONE_CENTER
    code = int(geomorphons.landforms(_radial_cone(1.0), dx=_MORPH_DX,
                                     search=_MORPH_LOS)[ci, cj])
    name = geomorphons.FORM_NAMES[code] if code >= 0 else "unclassified"
    expected = geomorphons.FORM_NAMES.index("pit")
    return _result("geomorphon_bowl_pit", code == expected,
                   f"bowl centre form {name!r} (code {code}; expected 'pit'={expected})",
                   code=code, form=name)


def check_geomorphon_tilt_slope():
    """A uniform planar tilt is dominated by 'slope': three directions fall and
    three rise (the two cross-slope directions are flat), so the interior
    ternary signature is (n_plus, n_minus) == (3, 3)."""
    z = synthetic.plane(_SHAPE, slope_x=0.1, dx=_MORPH_DX)
    comp = geomorphons.composition(z, dx=_MORPH_DX, search=_MORPH_LOS)
    dominant = _dominant_form(comp)
    return _result("geomorphon_tilt_slope", dominant == "slope",
                   f"planar-tilt dominant form {dominant!r} "
                   f"(slope fraction {comp['slope']:.4f})",
                   dominant=dominant, slope_fraction=comp["slope"])


def check_geomorphon_relief_invariance():
    """Geomorphons depend only on elevation DIFFERENCES, so a uniform vertical
    offset must leave the landform composition completely unchanged: the two
    compositions compare exactly equal (identical class fractions)."""
    z = synthetic.plane(_SHAPE, slope_x=0.1, dx=_MORPH_DX)
    base = geomorphons.composition(z, dx=_MORPH_DX, search=_MORPH_LOS)
    lifted = geomorphons.composition(z + 100.0, dx=_MORPH_DX, search=_MORPH_LOS)
    forms = sum(1 for v in base.values() if v > 0.0)
    return _result("geomorphon_relief_invariance", base == lifted,
                   f"composition over {forms} forms identical under +100 m offset "
                   f"(equal={base == lifted})",
                   forms=forms)


_CHECKS = (
    check_self_distance_zero,
    check_translation_invariance,
    check_rotation90_invariance,
    check_monotonic_roughness_discrimination,
    check_dominance_recovery,
    check_null_control,
    check_water_candidate_blocked,
    check_determinism,
    check_curvature_zero_on_plane,
    check_vrm_discriminates_roughness,
    check_roughness_hurst_sane,
    check_openness_flat,
    check_openness_peak,
    check_openness_pit_mirror,
    check_geomorphon_flat,
    check_geomorphon_cone_peak,
    check_geomorphon_bowl_pit,
    check_geomorphon_tilt_slope,
    check_geomorphon_relief_invariance,
)


def run_validation():
    """Run every scientific-correctness check and return a hashed report.

    Returns {checks, passed, failed, all_passed, package_hash}. The hash covers
    only the pass/fail outcomes (not float metrics) so it is a stable regression
    oracle across machines while the metrics remain for human inspection.
    """
    checks = [c() for c in _CHECKS]
    passed = sum(1 for c in checks if c["passed"])
    report = {
        "suite": "terratrace-validation",
        "checks": checks,
        "passed": passed,
        "failed": len(checks) - passed,
        "all_passed": passed == len(checks),
    }
    outcome = {c["name"]: c["passed"] for c in checks}
    report["package_hash"] = provenance.sha256_json(outcome)
    return report
