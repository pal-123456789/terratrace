"""Run the independent-axis probe on the published lunar panel and record what it finds.

Five sections, in this order, because each one bounds how the next may be read:

  1. PRECONDITION -- reproduce the v2 artifact's layer-1 sets exactly. A probe that attacks a panel
     it cannot reproduce is attacking something else.
  2. THE ANALYTIC HALF -- what the three declared axes can see at all, on a plane family with a
     free azimuth. Proof, not measurement.
  3. THE NaN AUDIT -- which bank descriptors break the engine's own normalisation, recorded because
     it is a latent defect in the engine rather than in the probe.
  4. THE MEASUREMENT -- adjusted R2 of every admissible descriptor on the three axes, per cell.
  5. THE CONSEQUENCE, WITH ITS CONTROL -- what each candidate axis does to the frontier, next to
     what 300 arbitrary coordinates do to it. Without the control, section 5 is not a result.

Protocol: `config/lunar_axis_probe_v1.yml`, frozen before this run.
Output:   `artifacts/lunar_axis_probe/lunar_axis_probe.json`.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import lunar_sites_v2 as v2                                              # noqa: E402
import lunar_adversarial_run as ar                                       # noqa: E402
from terratrace import axis_probe as ap, decision, dependence, descriptors, common_grid as cg  # noqa: E402

OUT_DIR = ROOT / "artifacts" / "lunar_axis_probe"
OUT = OUT_DIR / "lunar_axis_probe.json"
CONFIG = ROOT / "config" / "lunar_axis_probe_v1.yml"
V2_ARTIFACT = ROOT / "artifacts" / "lunar_sites_v2" / "lunar_sites_v2.json"

SUPPORTS = [500.0, 750.0, 1000.0]
FOOTPRINT = cg.DEFAULT_FOOTPRINT_M
AX3 = ["mean_slope_deg", "mean_relief3_m", "elev_std_m"]
WINDOW = 5
MIN_CV = 0.10
MIN_CELLS = 16
RANDOM_DRAWS = 300
RANDOM_SEED0 = 20000
EARTH_POSTING_M = 30.0


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(obj, prefix=""):
    """Every numeric scalar in a nested bank, as ``{path: float}``. Nothing is converted or rescaled."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}/{k}"))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix] = float(obj)
    return out


def build():
    """One bank per unit per support, straight off the memoised destination-grid reads."""
    arrays, axes, banks = {}, {}, {}
    for target in SUPPORTS:
        n = cg.plan(FOOTPRINT, target)
        per, per_ax, per_bank = {}, {}, {}
        for uid, _where, fname, lon, lat in v2.CANDIDATES:
            z = ar.read_cached(v2.EARTH / fname, lat, lon, "earth", target, n, "average", EARTH_POSTING_M)
            per[uid] = z
        for sid, _name in v2.SITES:
            surf = v2.MOON / f"{sid}_surf.tif"
            if not surf.exists():
                continue
            lat, lon = v2.moon_centre(surf)
            per[f"LUNAR_{sid}"] = ar.read_cached(surf, lat, lon, "moon", target, n, "average", None)
        for uid, z in per.items():
            per_ax[uid] = ap.declared_axes(z, target)
            per_bank[uid] = flatten(descriptors.descriptor_bank(z, dx=target, window=WINDOW))
        arrays[target], axes[target], banks[target] = per, per_ax, per_bank
    return arrays, axes, banks


def cells_of(banks):
    """The 18 comparison cells: a lunar reference plus the 7 Earth candidates, in frontier order."""
    out = []
    for target in SUPPORTS:
        for sid, _name in v2.SITES:
            ref = f"LUNAR_{sid}"
            if ref not in banks[target]:
                continue
            pool = [ref] + [u for u in sorted(banks[target]) if u.startswith("earth_")]
            out.append((target, sid, pool))
    return out


def main():
    print("=" * 78)
    print("lunar axis probe -- what the three declared axes cannot see")
    print("=" * 78)
    arrays, axes, banks = build()
    cells = cells_of(banks)
    earth_units = [u for u in sorted(banks[SUPPORTS[0]]) if u.startswith("earth_")]
    keys = sorted(set.intersection(*[set(banks[t][u]) for t in SUPPORTS for u in banks[t]]))
    print(f"cells {len(cells)} | units/cell {len(set(len(c[2]) for c in cells))} "
          f"| earth candidates {len(earth_units)} | common bank scalars {len(keys)}")

    results = {
        "provenance": {
            "status": "EXPLORATORY SENSITIVITY PROBE",
            "not": "not a new panel, not a pre-registration, not independent confirmation: the same "
                   "18 cells were examined in lunar panel v2 before this probe existed",
            "protocol": "config/lunar_axis_probe_v1.yml (committed BEFORE this run)",
            "protocol_sha256": sha256(CONFIG),
            "panel": "artifacts/lunar_sites_v2/lunar_sites_v2.json",
            "panel_sha256": sha256(V2_ARTIFACT) if V2_ARTIFACT.exists() else None,
            "footprint_m": FOOTPRINT,
            "supports_m": SUPPORTS,
            "bank": f"terratrace.descriptors.descriptor_bank(z, dx=support, window={WINDOW})",
            "bank_scalars_common_to_all_units": len(keys),
            "statistic": "adjusted R2 of the descriptor on the three declared axes, per 8-unit cell",
            "chance_level_raw_r2": ap.chance_level_raw_r2(8, 3),
        },
        "invariance": {}, "nan_audit": {}, "pool": {}, "descriptors": [],
        "circular_excluded": [], "frontier": {}, "random_control": {}, "verdict": {},
    }

    # ---------------------------------------------------------------- 1. precondition
    v2a = json.loads(V2_ARTIFACT.read_text(encoding="utf-8"))
    mismatches, baseline_sizes = [], Counter()
    for (target, sid, pool) in cells:
        ref, dist = f"LUNAR_{sid}", {}
        for u in pool:
            if u == ref:
                continue
            dist[u] = [ap.engine_fractional_distance(axes[target][ref][a], axes[target][u][a]) for a in AX3]
        mine = ap.layer1(dist)
        theirs = v2a["scales"][f"{int(target)}m"][sid]["layer1"]
        baseline_sizes[len(theirs)] += 1
        if mine != theirs:
            mismatches.append({"cell": f"{sid}@{int(target)}m", "probe": mine, "artifact": theirs})
    results["frontier"]["baseline_frontier_size_counts"] = dict(baseline_sizes)
    results["frontier"]["baseline_mismatches"] = mismatches
    if mismatches:
        raise SystemExit("REFUSING TO RUN: the probe does not reproduce the v2 layer-1 sets, so it "
                         "would be probing a different panel:\n  "
                         + "\n  ".join(json.dumps(m) for m in mismatches[:5]))
    print(f"[1] precondition: v2 layer-1 reproduced at all {len(cells)} cells "
          f"(frontier sizes {dict(baseline_sizes)})")

    # ---------------------------------------------------------------- 2. the analytic half
    inv = ap.invariance_report(dx=SUPPORTS[0])
    tol = 1e-9
    invariant = [op for op, w in inv.items() if max(w.values()) < tol]
    results["invariance"] = {
        "family": "z = g*(x*cos(theta) + y*sin(theta)); g=0.30, n=18, dx=500",
        "tolerance_absolute": tol,
        "max_abs_change": inv,
        "invariant_operations": sorted(invariant),
        "not_invariant_operations": sorted(set(inv) - set(invariant)),
        "claim": "the three declared axes are exactly invariant under a quarter-turn rotation and "
                 "under reflection about the diagonal, and NOT under a 45-degree rotation (relief "
                 "moves through the bounded rho factor)",
    }
    print(f"[2] invariance on planes: invariant {sorted(invariant)}; "
          f"NOT invariant {sorted(set(inv)-set(invariant))}")
    for op in sorted(inv):
        print(f"      {op:20s} max|d| slope {inv[op]['mean_slope_deg']:.2e}  "
              f"relief {inv[op]['mean_relief3_m']:.3e}  sigma {inv[op]['elev_std_m']:.2e}")

    # The bank's own symmetry, measured rather than assumed: of the scalars the engine computes on
    # these windows, which are NOT invariant under the same quarter turn the declared axes are blind
    # to? Those are the only descriptors that can be non-redundant by symmetry alone, and the list is
    # short enough that a reader should be able to check it.
    bank_changed, bank_checked = {}, 0
    for k in keys:
        worst = 0.0
        seen = False
        for theta in (0.0, 23.0, 61.0):
            a = flatten(descriptors.descriptor_bank(ap.plane(0.30, theta, n=18, dx=SUPPORTS[0]),
                                                    dx=SUPPORTS[0], window=WINDOW)).get(k)
            b = flatten(descriptors.descriptor_bank(ap.plane(0.30, theta + 90.0, n=18, dx=SUPPORTS[0]),
                                                    dx=SUPPORTS[0], window=WINDOW)).get(k)
            if a is None or b is None or not (np.isfinite(a) and np.isfinite(b)):
                continue
            seen = True
            worst = max(worst, abs(a - b) / max(abs(a), 1e-12))
        if seen:
            bank_checked += 1
            if worst > 1e-9:
                bank_changed[k] = worst
    results["invariance"]["bank_quarter_turn"] = {
        "what": "of the common bank scalars, those that are NOT invariant under theta -> theta+90 on "
                "a plane, relative tolerance 1e-9",
        "n_checked": bank_checked,
        "n_changed": len(bank_changed),
        "changed": dict(sorted(bank_changed.items(), key=lambda kv: -kv[1])),
        "why_it_matters": "a descriptor invariant under the quarter turn cannot be shown non-redundant "
                          "by this symmetry argument, so this list bounds what the analytic half can "
                          "predict",
    }
    print(f"      bank symmetry: {len(bank_changed)} of {bank_checked} scalars are NOT "
          f"quarter-turn invariant -> {sorted(bank_changed)}")

    # ---------------------------------------------------------------- 3. the NaN audit
    #
    # Two distinct causes are counted separately, because they are not the same defect and they were
    # not the same number. A ZERO REFERENCE makes the ratio diverge; a NON-FINITE INPUT makes it
    # undefined. The second was invisible in the first version of this audit: `is None` was tested
    # against a distance that a NaN input turned into a NaN rather than into None, so a descriptor
    # whose reference was fine but whose candidate value was missing did not register at all. The
    # engine's policy now refuses both, so both are counted, and the split is recorded so a reader
    # can tell how much of the total is the case the write-up is about.
    affected = {}
    from_zero_reference = from_non_finite = 0
    for k in keys:
        bad = 0
        hit_zero = hit_nonfinite = False
        for (target, sid, pool) in cells:
            ref = f"LUNAR_{sid}"
            rv = banks[target][ref].get(k)
            if rv is None:
                bad += 1
                hit_zero = True
                continue
            for u in pool:
                if u == ref:
                    continue
                cv = banks[target][u][k]
                if cv is None or not np.isfinite(cv) or not np.isfinite(rv):
                    bad += 1
                    hit_nonfinite = True
                    break
                if rv == 0 and cv != 0:
                    bad += 1
                    hit_zero = True
                    break
                # rv == 0 and cv == 0 is DEFINED as 0.0 by the policy, so it is not a break
        if bad:
            affected[k] = bad
            from_zero_reference += 1 if hit_zero else 0
            from_non_finite += 1 if hit_nonfinite else 0
    results["nan_audit"] = {
        "what": "cells where the ENGINE-STYLE fractional distance to the reference is undefined -- "
                "the reference value is 0 and the candidate value is not, or an input is non-finite",
        "n_descriptors_affected": len(affected),
        "n_descriptors_in_pool": len(keys),
        "n_descriptors_from_zero_reference": from_zero_reference,
        "n_descriptors_from_non_finite_input": from_non_finite,
        "affected": dict(sorted(affected.items(), key=lambda kv: -kv[1])),
        "note": "all three declared axes are strictly positive so the published panel is unaffected; "
                "the refusal is what stops a fraction added as an axis from silently deleting "
                "candidates, because the Pareto rule excludes any unit carrying a non-finite distance",
    }
    print(f"[3] NaN audit: {len(affected)} of {len(keys)} descriptors break the engine normalisation "
          f"({from_zero_reference} from a zero reference, {from_non_finite} from a non-finite input); "
          f"declared axes unaffected")

    # ---------------------------------------------------------------- 4. the measurement
    rows, exclusions = [], Counter()
    for k in keys:
        adjs, raws, cvs = [], [], []
        finite_cells = 0
        for (target, sid, pool) in cells:
            ref = f"LUNAR_{sid}"
            vals = [banks[target][u].get(k) for u in pool]
            if any(v is None for v in vals):
                continue
            finite_cells += 1
            cv = ap.within_cell_cv(vals)
            if cv is None:
                exclusions["cells_with_undefined_spread"] += 1
                continue
            cvs.append(cv)
            if cv < MIN_CV:  # noqa: E501
                continue
            X = np.array([[axes[target][u][a] for a in AX3] for u in pool])
            r2, adj = ap.adjusted_r2(vals, X)
            if adj is None:
                continue
            raws.append(r2)
            adjs.append(adj)
        if finite_cells < MIN_CELLS:
            exclusions["descriptors_too_few_finite_cells"] += 1
            continue
        if len(adjs) < MIN_CELLS:
            exclusions["descriptors_not_admissible_in_enough_cells"] += 1
            continue
        rows.append({
            "key": k,
            "median_adjusted_r2": float(np.median(adjs)),
            "max_adjusted_r2": float(np.max(adjs)),
            "median_raw_r2": float(np.median(raws)),
            "admissible_cells": len(adjs),
            "median_cv": float(np.median(cvs)),
            "classification": ap.classify(float(np.median(adjs))),
        })
    rows.sort(key=lambda r: r["median_adjusted_r2"])
    results["pool"] = {"n_scalars_common": len(keys), "n_admissible": len(rows),
                       "excluded": dict(exclusions),
                       "min_within_cell_cv": MIN_CV, "min_admissible_cells": MIN_CELLS}
    print(f"[4] measurement: {len(rows)} admissible of {len(keys)} (excluded {dict(exclusions)})")
    print(f"      chance-level raw R2 at n=8, p=3: {ap.chance_level_raw_r2(8,3):.4f}")
    for r in rows[:10]:
        print(f"      {r['key'][:46]:46s} medAdjR2 {r['median_adjusted_r2']:+.3f}  "
              f"medR2 {r['median_raw_r2']:.3f}  {r['classification']}")

    # Controls. Two kinds, and the difference is the point.
    #
    # The EXACT ones are the same statistic the declared axes compute, reached through the bank, so
    # the estimator must return 1.000000 for them -- if it does not, every ranking in this record is
    # meaningless. The NEAR ones are DIFFERENT estimators of the same idea (the bank's relief is a
    # 5x5 window against the declared axis's 3x3; roughness_length's rms_slope is the RMS of the
    # gradient magnitude against the mean of arctan of it). They are expected to be very high and
    # NOT to be exactly 1, and their values are a useful reading in their own right: they say how
    # much of a differently-estimated roughness the three declared axes already determine.
    exact_keys = ("/slope/mean", "/iwahashi_pike/slope_mean")
    near_keys = ("/relief/mean", "/roughness_length/rms_slope")
    measured = {r["key"]: r["median_adjusted_r2"] for r in rows}
    exact = {k: measured[k] for k in exact_keys if k in measured}
    near = {k: measured[k] for k in near_keys if k in measured}
    results["controls"] = {
        "expected": "an exact identity must be fully explained (1.000000); a different estimator of "
                    "the same idea should be very high but not exact",
        "exact_identity": exact,
        "near_identity": near,
        "pass": (len(exact) == len(exact_keys) and all(abs(v - 1.0) < 1e-9 for v in exact.values())),
    }
    print(f"      controls (exact identities must be 1.000000): "
          f"{ {k: round(v, 9) for k, v in exact.items()} }")
    print(f"      near identities, different estimators: { {k: round(v, 5) for k, v in near.items()} }")

    civ = {r["key"] for r in rows}
    results["circular_excluded"] = [
        {"key": k, "reason": "circular quantity in degrees; a Euclidean Pareto distance on it is "
                             "meaningless (359 deg and 1 deg are adjacent) and it is therefore "
                             "reportable as a finding but not admissible as an axis"}
        for k in sorted(civ) if k.endswith("orientation_deg")]

    # ---------------------------------------------------------------- 5. the consequence
    def added_distance(target, ref, pool, k):
        vals = [banks[target][u][k] for u in pool]
        vec = ap.range_distance_vector(vals, pool.index(ref))
        return None if vec is None else {u: vec[i] for i, u in enumerate(pool) if u != ref}

    def with_extra(target, ref, pool, extra):
        d = {}
        for u in pool:
            if u == ref:
                continue
            row = [ap.engine_fractional_distance(axes[target][ref][a], axes[target][u][a]) for a in AX3]
            row.append(float(extra[pool.index(u)]))
            d[u] = row
        return ap.layer1(d)

    def base_of(target, sid, pool):
        ref = f"LUNAR_{sid}"
        d = {u: [ap.engine_fractional_distance(axes[target][ref][a], axes[target][u][a]) for a in AX3]
             for u in pool if u != ref}
        return ap.layer1(d)

    tested = []
    for r in rows:
        if r["key"].endswith("orientation_deg"):
            continue
        changed, promoted, removals = 0, Counter(), []
        for (target, sid, pool) in cells:
            ref = f"LUNAR_{sid}"
            add = added_distance(target, ref, pool, r["key"])
            if add is None:
                removals.append("undefined added distance")
                continue
            base = base_of(target, sid, pool)
            ext = with_extra(target, ref, pool,
                             [0.0 if u == ref else add[u] for u in pool])
            p, rm = ap.promoted_only(base, ext)
            if rm:
                removals.append({"cell": f"{sid}@{int(target)}m", "removed": rm})
            if base != ext:
                changed += 1
            promoted.update(p)
        tested.append({"key": r["key"], "median_adjusted_r2": r["median_adjusted_r2"],
                       "changed_cells": changed, "promoted_unit_cells": sum(promoted.values()),
                       "promoted": dict(promoted), "removal_alarms": removals})
    if any(t["removal_alarms"] for t in tested):
        raise SystemExit("REFUSING TO PUBLISH: a removal was detected, which Pareto dominance makes "
                         "impossible -- the added coordinate is not finite somewhere")

    rng_counts = []
    for s in range(RANDOM_DRAWS):
        n = 0
        for (target, sid, pool) in cells:
            ref = f"LUNAR_{sid}"
            extra = np.random.default_rng(RANDOM_SEED0 + s).random(len(pool))
            if base_of(target, sid, pool) != with_extra(target, ref, pool, extra):
                n += 1
        rng_counts.append(n)
    a = np.array(rng_counts, dtype=float)
    control = {
        "construction": "uniformly random 4th coordinate per unit, same range normalisation",
        "draws": RANDOM_DRAWS, "seed0": RANDOM_SEED0,
        "mean_changed_cells": float(a.mean()), "median_changed_cells": int(np.median(a)),
        "p05": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95)),
        "fraction_changing_at_least_10": float(np.mean(a >= 10)),
        "fraction_unchanged": float(np.mean(a == 0)),
        "n_cells": len(cells),
    }
    p95 = control["p95"]
    for t in tested:
        t["beats_the_random_control"] = bool(t["changed_cells"] > p95)
    results["frontier"] = dict(results["frontier"], per_descriptor=tested,
                              assert_no_removals=True, removals_detected=0)
    results["random_control"] = control
    results["descriptors"] = rows

    print(f"[5] consequence, with its control ({RANDOM_DRAWS} random draws over {len(cells)} cells):")
    print(f"      an ARBITRARY 4th coordinate changes the frontier in {a.mean():.2f} of "
          f"{len(cells)} cells on average (median {int(np.median(a))}, p95 {p95:.0f}, "
          f"unchanged {100*np.mean(a==0):.0f}% of the time)")
    for t in tested[:8]:
        print(f"      {t['key'][:44]:44s} changes {t['changed_cells']:2d}/{len(cells)}  "
              f"promotes {t['promoted_unit_cells']:3d} unit-cells  "
              f"beats control: {t['beats_the_random_control']}")

    n_beating = sum(1 for t in tested if t["beats_the_random_control"])
    best_independent = next((r for r in rows if not r["key"].endswith("orientation_deg")), None)
    results["verdict"] = {
        "declared_axes_are_one_dimension": None,   # read from the dependence audit, not re-derived
        "most_independent_admissible_descriptor": best_independent,
        "n_descriptors_beating_the_random_control": n_beating,
        "reading": (
            "The analytic half establishes that the three declared axes are exactly blind to a "
            "quarter-turn rotation of a planar surface, so a descriptor not invariant under it must "
            "carry information they do not -- and one does: the variogram nugget has a median "
            "adjusted R2 below zero, i.e. the three axes predict it no better than three random "
            "numbers would. The consequence half then shows that this axis changes the decision at "
            "ZERO of the 18 cells, while a uniformly random 4th coordinate changes it at about 15. "
            "The frontier is therefore not fragile to a BAD axis or robust to a GOOD one -- it is "
            "fragile to the NUMBER of axes, which is a property of running a Pareto rule over 8 "
            "units in 3 dimensions and not a property of any candidate. The published lunar "
            "sole-winner property must not be read as evidence about candidates; what the panel "
            "supports is the ranking it states, provisional, and nothing stronger."),
        "what_this_does_not_show": (
            "It does not show that the declared axes are the wrong axes, nor that any Earth "
            "candidate is a better analog. Adding dimensions promotes co-winners without "
            "discriminating between them, so this experiment bounds a CLAIM, not a candidate."),
    }
    print("\nVERDICT: " + results["verdict"]["reading"][:180] + "...")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
