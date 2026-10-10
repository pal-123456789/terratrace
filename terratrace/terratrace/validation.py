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

Each check returns a uniform record; `run_validation()` aggregates them into a
hashed report that is both a test oracle and a publishable validation artifact.
Pure NumPy + the engine and its feature descriptors; no network, no rasterio.
"""
from __future__ import annotations

import numpy as np

from . import study, synthetic, provenance, features

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
