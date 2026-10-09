"""End-to-end study orchestration.

The comparison core (`compare_units`) is shared by two front doors:

* `run_study`      - deterministic synthetic data (offline, CI, teaching).
* `run_real_study` - real Mars (MOLA) and Earth (Copernicus/USGS) DEMs
                     loaded via :mod:`terratrace.ingest`.

Both paths produce the identical study-package contract, so the viewer,
tests, and provenance apply unchanged.

Scientific boundary: morphology screening only. No rover, traversability,
geologic-equivalence, access, or mission-readiness claim is produced.
"""
from __future__ import annotations

import numpy as np

from . import synthetic, features, support, distances, decision, gaps, protocol, provenance, masks
from .provenance import EvidenceGraph

METRICS = ("slope", "relief", "ruggedness", "connectivity")

SCENARIOS = [
    {"slope_threshold": 15.0, "relief_alpha": 0.0, "name": "baseline"},
    {"slope_threshold": 10.0, "relief_alpha": 0.0, "name": "stricter_slope"},
    {"slope_threshold": 15.0, "relief_alpha": 0.05, "name": "robust_relief"},
    {"slope_threshold": 20.0, "relief_alpha": 0.05, "name": "lenient"},
]


def _unit_grid(kind, shape=(96, 96)):
    if kind == "reference":
        return synthetic.plane(shape, 0.12, 0.05) + synthetic.rough_field(shape, 0.6, 1)
    if kind == "earth_close":
        return synthetic.plane(shape, 0.11, 0.06) + synthetic.rough_field(shape, 0.65, 2)
    if kind == "earth_far":
        return synthetic.plane(shape, 0.30, 0.02) + synthetic.rough_field(shape, 2.2, 3)
    if kind == "earth_blocked":
        base = synthetic.plane(shape, 0.12, 0.05) + synthetic.rough_field(shape, 0.6, 4)
        return synthetic.with_nodata_wedge(base, fraction=0.9)
    raise ValueError(kind)


def _feature_distributions(z, dx, slope_threshold, relief_alpha, relief_window=5, rug_window=5):
    s = features.slope_deg(z, dx, dx)
    r = features.relief(z, window=relief_window, alpha=relief_alpha)
    rug = features.ruggedness(z, window=rug_window, dx=dx, dy=dx)
    conn, _ = features.low_slope_connectivity(s, slope_threshold)
    return {"slope": s.ravel(), "relief": r.ravel(),
            "ruggedness": rug.ravel(), "connectivity_scalar": conn}


def _vector(ref, cand):
    d_slope = distances.normalized_distance(cand["slope"], ref["slope"])
    d_relief = distances.normalized_distance(cand["relief"], ref["relief"])
    d_rug = distances.normalized_distance(cand["ruggedness"], ref["ruggedness"])
    scale = abs(ref["connectivity_scalar"]) + 1e-6
    d_conn = abs(cand["connectivity_scalar"] - ref["connectivity_scalar"]) / scale
    return (float(d_slope), float(d_relief), float(d_rug), float(d_conn))


def _extended_dims(extended, cid, reference_id):
    """Extra Pareto dimensions from scalar extended metrics (nan-safe)."""
    def diff(key):
        a = extended[cid].get(key)
        b = extended[reference_id].get(key)
        if a is None or b is None or a != a or b != b:  # None or NaN
            return 1.0
        return abs(float(a) - float(b))
    return (diff("aspect_dispersion"), diff("hypsometric_integral"))


def compare_units(raw_units, rights, native_posting_m, reference_id="mars_reference",
                  target_support_m=100.0, min_valid=0.5, source_label="synthetic",
                  decision_metrics="core", n_boot=0):
    """Run the full comparison on a dict of elevation arrays.

    raw_units: {unit_id: 2-D elevation array}
    rights:    {unit_id: rights_status str}
    native_posting_m: scalar or {unit_id: metres}
    """
    def native(uid):
        return native_posting_m[uid] if isinstance(native_posting_m, dict) else native_posting_m

    agg, meta = {}, {}
    for uid, grid in raw_units.items():
        factor = max(int(round(target_support_m / native(uid))), 1)
        a, rec = support.block_aggregate(grid, factor, native(uid), min_valid=min_valid)
        agg[uid] = a
        meta[uid] = {"data_present": a.size > 0, "support_valid": a.size > 0,
                     "valid_fraction": rec.valid_fraction, "min_valid_fraction": min_valid,
                     "zero_fraction": masks.zero_fraction(a),
                     "zero_fraction_max": decision.ZERO_FRACTION_MAX,
                     "rights_status": rights.get(uid, "unknown"), "support": rec.to_dict()}

    dx = float(target_support_m)
    extended = {}
    for uid, a in agg.items():
        extended[uid] = {
            "aspect_dispersion": features.aspect_dispersion(a, dx, dx),
            "hypsometric_integral": features.hypsometric_integral(a),
        }
    candidate_ids = [u for u in agg if u != reference_id]
    scenario_vectors, baseline_vectors = [], {}
    ref_feats_base, cand_feats_base = None, {}
    for cfg in SCENARIOS:
        ref_f = _feature_distributions(agg[reference_id], dx, cfg["slope_threshold"], cfg["relief_alpha"])
        vecs = {}
        for cid in candidate_ids:
            ok, _ = decision.eligibility(meta[cid])
            if not ok:
                continue
            cand_f = _feature_distributions(agg[cid], dx, cfg["slope_threshold"], cfg["relief_alpha"])
            vec = _vector(ref_f, cand_f)
            if decision_metrics == "extended":
                vec = vec + _extended_dims(extended, cid, reference_id)
            vecs[cid] = vec
            if cfg["name"] == "baseline":
                cand_feats_base[cid] = cand_f
        scenario_vectors.append(vecs)
        if cfg["name"] == "baseline":
            baseline_vectors = vecs
            ref_feats_base = ref_f

    elig_map = {u: decision.eligibility(meta[u]) for u in agg}
    if not baseline_vectors and candidate_ids:
        reasons = [elig_map[c][1] for c in candidate_ids]
        state = "BLOCKED" if any(r.startswith("BLOCKED") for r in reasons) else "NOT_COMPARABLE"
        recommended, flips = None, {}
    else:
        eligible_scns = [v for v in scenario_vectors if v]
        state, recommended, flips = decision.resolve_state(baseline_vectors, eligible_scns)
    gap_ledger = gaps.ledger_for(state)
    metric_names = list(METRICS) + (["aspect_dispersion", "hypsometric_integral"]
                                     if decision_metrics == "extended" else [])
    profile = {"task": "map_scale_terrain_route_study", "target_body": "mars",
               "target_support_m": dx, "metrics": metric_names,
               "decision_metrics": decision_metrics,
               "source_label": source_label, "claim_maturity": "prototype_morphology_only"}
    proto = protocol.draft_protocol(state, recommended, profile, gap_ledger)
    graph = _build_graph(meta, baseline_vectors, state, recommended, source_label, elig_map, flips)

    package = {
        "schema_version": "0.1.0", "profile": profile,
        "unit_metadata": meta,
        "baseline_vectors": {u: list(v) for u, v in baseline_vectors.items()},
        "scenario_vectors": [{u: list(v) for u, v in s.items()} for s in scenario_vectors],
        "scenario_names": [c["name"] for c in SCENARIOS],
        "pairwise_flip_matrix": flips, "result_state": state,
        "recommended_unit": recommended,
        "extended_metrics": extended,
        "eligibility": {u: {"eligible": e, "reason": r} for u, (e, r) in elig_map.items()},
        "transfer_gap_ledger": gap_ledger, "draft_protocol": proto,
        "prohibited_claims": gaps.prohibited_claims(), "evidence_graph": graph.to_dict(),
    }
    if n_boot and baseline_vectors and ref_feats_base is not None:
        from . import uncertainty
        package["bootstrap"] = uncertainty.bootstrap_pareto(
            ref_feats_base, cand_feats_base, n_boot=n_boot, seed=0)
    package["package_hash"] = provenance.sha256_json(
        {k: v for k, v in package.items() if k != "package_hash"})
    return package


def run_study(target_support_m=100.0, native_posting_m=25.0, min_valid=0.5, n_boot=0):
    raw = {"mars_reference": _unit_grid("reference"), "earth_close": _unit_grid("earth_close"),
           "earth_far": _unit_grid("earth_far"), "earth_blocked": _unit_grid("earth_blocked")}
    rights = {"mars_reference": "verified_allowed", "earth_close": "verified_allowed",
              "earth_far": "verified_allowed", "earth_blocked": "unknown"}
    return compare_units(raw, rights, native_posting_m, target_support_m=target_support_m,
                         min_valid=min_valid, source_label="synthetic", n_boot=n_boot)


def run_real_study(units, target_support_m=1000.0, min_valid=0.5, reproject=True,
                   decision_metrics="core", n_boot=0):
    """Compare REAL DEMs.

    units: list of dicts with keys: id, path, native_posting_m, rights_status,
    optional bbox (west,south,east,north in degrees), optional body
    ("mars"/"earth"), and optional is_reference (exactly one is reference).

    With reproject=True (default) each AOI is warped to its own local
    azimuthal-equidistant metric grid at target_support_m before features
    are computed (correct cross-body comparison). Requires rasterio.
    """
    from . import ingest
    raw, rights, native = {}, {}, {}
    reference_id = None
    for u in units:
        body = u.get("body", "mars" if u.get("is_reference") else "earth")
        mask_kw = dict(mask_below=u.get("mask_below_m"),
                       mask_values=u.get("mask_values"),
                       mask_above=u.get("mask_above_m"))
        if reproject and u.get("bbox"):
            from . import reproject as rp
            z, res = rp.read_aoi_metric(u["path"], u["bbox"], target_support_m, body, **mask_kw)
            native[u["id"]] = res
        elif u.get("bbox"):
            z, posting = ingest.window_from_bbox(u["path"], u["bbox"])
            z = masks.apply_masks(z, **mask_kw)
            native[u["id"]] = u.get("native_posting_m", posting)
        else:
            z, posting = ingest.load_dem_array(u["path"])
            z = masks.apply_masks(z, **mask_kw)
            native[u["id"]] = u.get("native_posting_m", posting)
        raw[u["id"]] = z
        rights[u["id"]] = u.get("rights_status", "unknown")
        if u.get("is_reference"):
            reference_id = u["id"]
    if reference_id is None:
        raise ValueError("exactly one unit must set is_reference=True")
    label = "real_dem_aeqd" if reproject else "real_dem"
    return compare_units(raw, rights, native, reference_id=reference_id,
                         target_support_m=target_support_m, min_valid=min_valid,
                         source_label=label, decision_metrics=decision_metrics, n_boot=n_boot)


def _build_graph(meta, vectors, state, recommended, source_label, elig_map, flips):
    g = EvidenceGraph()
    src = g.add(provenance.source_node(
        "src:" + source_label, "TerraTrace " + source_label, source_label, "0.1.0",
        "see source_lock / dataset terms", status="C3"))
    tr = g.add(provenance.transform_node(
        "tr:common_support", "block_aggregate+features", {"metrics": list(METRICS)}, [src]))
    for uid in meta:
        g.link(uid, "represented_by", src)
    # Eligibility verdicts are first-class, traceable claims.
    for uid, (ok, reason) in elig_map.items():
        eid = g.add(provenance.claim_node(
            f"c:elig:{uid}", f"{uid} eligibility={ok}: {reason}", "C3", [src]))
        g.link(eid, "about", uid)
    for uid, vec in vectors.items():
        mid = g.add(provenance.measurement_node(
            f"m:{uid}", "morphology_distance_vector", list(vec), "normalized",
            meta[uid]["support"]["target_support_m"],
            {"valid_fraction": meta[uid]["valid_fraction"]}, tr))
        cid = g.add(provenance.claim_node(
            f"c:{uid}", f"{uid} morphology distance to reference at common support", "C3", [mid]))
        g.link(cid, "about", uid)
    sens = g.add(provenance.claim_node(
        "c:sensitivity", f"pairwise rank-flip matrix across scenarios: {flips}", "C3",
        [f"c:{u}" for u in vectors]))
    res = g.add(provenance.claim_node(
        "c:result", f"result={state}; recommended={recommended}", "C3",
        [f"c:{u}" for u in vectors] + [sens]))
    g.add(provenance.claim_node(
        "c:protocol", "draft study protocol (not an authorization)", "C3", [res]))
    return g
