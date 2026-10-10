"""Reproducibility + performance benchmark harness for TerraTrace.

Where `validation` proves the engine is *correct*, this module proves it is
*stable and characterised*: a pinned battery of end-to-end studies whose
behavioural invariants (which state is reached, which unit wins, what is
blocked) must hold, a hash-stability check (identical inputs reproduce an
identical package hash), and a scaling profile (wall-clock time vs grid size)
so performance is reported honestly rather than guessed.

Invariants are asserted as *properties* (e.g. "the near twin is recommended",
"the water tile is blocked"), not brittle hard-coded numbers, so the benchmark
stays meaningful as thresholds evolve. Timings are reported, never pass/failed
on an absolute value — they depend on the host. Pure NumPy + the engine.
"""
from __future__ import annotations

import time

import numpy as np

from . import study, synthetic, decision, provenance

_NATIVE = 10.0
_TARGET = 10.0


def _scene(shape, slope_x=0.02):
    """Deterministic (reference, near, far) terrains for a scene of a given size."""
    base = synthetic.plane(shape, slope_x=slope_x, dx=_NATIVE)
    ref = base + synthetic.rough_field(shape, amplitude=0.8, seed=1)
    near = base + synthetic.rough_field(shape, amplitude=0.9, seed=2)
    far = base + synthetic.rough_field(shape, amplitude=4.0, seed=3)
    return ref, near, far


def _run(raw, rights=None, target=_TARGET):
    rr = {u: "verified_allowed" for u in raw}
    if rights:
        rr.update(rights)
    return study.compare_units(raw, rr, _NATIVE, reference_id="ref",
                               target_support_m=target, min_valid=0.5,
                               source_label="benchmark")


def _record(name, passed, detail, **extra):
    return {"name": name, "passed": bool(passed), "detail": detail, **extra}


def _scenario_clear_winner(shape=(96, 96)):
    ref, near, far = _scene(shape)
    pkg = _run({"ref": ref, "near": near, "far": far})
    state, rec = pkg["result_state"], pkg["recommended_unit"]
    ok = state == "RECOMMEND_FOLLOW_UP" and rec == "near"
    return _record("clear_winner", ok, f"state={state} recommended={rec}", state=state)


def _scenario_water_blocked(shape=(96, 96)):
    ref, good, _ = _scene(shape)
    water = synthetic.constant(shape, 0.0)
    pkg = _run({"ref": ref, "good": good, "water": water})
    elig = pkg["eligibility"].get("water", {})
    ok = elig.get("eligible") is False and "BLOCKED" in str(elig.get("reason", ""))
    return _record("water_blocked", ok, f"water_eligible={elig.get('eligible')}",
                   state=pkg["result_state"])


def _scenario_synthetic_study():
    pkg = study.run_study()
    state = pkg["result_state"]
    ok = state in decision.STATES
    return _record("synthetic_study", ok, f"state={state} in STATES", state=state)


def _hash_stability():
    """Identical study inputs must reproduce an identical package hash."""
    h1 = study.run_study()["package_hash"]
    h2 = study.run_study()["package_hash"]
    return _record("hash_stability", h1 == h2, f"hash {h1[:12]}... reproduced", stable=h1 == h2)


def scaling_profile(sizes=(48, 96, 144), repeats=1):
    """Wall-clock time to run a 3-unit study at each grid size (median of repeats).

    Timings are reported, not pass/failed (host-dependent). `cells` is the grid
    cell count so a reader can see the per-cell cost trend.
    """
    rows = []
    for n in sizes:
        ref, near, far = _scene((n, n))
        raw = {"ref": ref, "near": near, "far": far}
        times = []
        for _ in range(max(1, repeats)):
            t0 = time.perf_counter()
            pkg = _run(raw)
            times.append(time.perf_counter() - t0)
        times.sort()
        rows.append({"size": n, "cells": n * n,
                     "seconds": round(times[len(times) // 2], 4),
                     "state": pkg["result_state"]})
    return rows


def run_benchmark(sizes=(48, 96, 144), repeats=1):
    """Run the invariant battery + hash stability + scaling profile.

    Returns {suite, scenarios, scaling, passed, failed, all_passed, package_hash}.
    The hash covers only the scenario pass/fail outcomes (host-independent), so it
    is a stable regression oracle; `scaling` carries the (host-dependent) timings.
    """
    scenarios = [
        _scenario_clear_winner(),
        _scenario_water_blocked(),
        _scenario_synthetic_study(),
        _hash_stability(),
    ]
    passed = sum(1 for s in scenarios if s["passed"])
    scaling = scaling_profile(sizes=sizes, repeats=repeats)
    report = {
        "suite": "terratrace-benchmark",
        "scenarios": scenarios,
        "scaling": scaling,
        "passed": passed,
        "failed": len(scenarios) - passed,
        "all_passed": passed == len(scenarios),
    }
    outcome = {s["name"]: s["passed"] for s in scenarios}
    report["package_hash"] = provenance.sha256_json(outcome)
    return report
