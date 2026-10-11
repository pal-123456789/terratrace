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

import warnings

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


def _feature_maps_2d(z, dx, slope_threshold, relief_alpha, relief_window=5, rug_window=5):
    """Same features as _feature_distributions but kept as 2-D maps, for the
    spatial block bootstrap (which must resample patches, not raveled values)."""
    s = features.slope_deg(z, dx, dx)
    r = features.relief(z, window=relief_window, alpha=relief_alpha)
    rug = features.ruggedness(z, window=rug_window, dx=dx, dy=dx)
    conn, _ = features.low_slope_connectivity(s, slope_threshold)
    return {"slope": s, "relief": r, "ruggedness": rug, "connectivity_scalar": conn}



def _vector(ref, cand, scales=None):
    def nd(f):
        s = None if scales is None else scales.get(f)
        return distances.normalized_distance(cand[f], ref[f], scale=s)
    scale = abs(ref["connectivity_scalar"]) + 1e-6
    d_conn = abs(cand["connectivity_scalar"] - ref["connectivity_scalar"]) / scale
    return (float(nd("slope")), float(nd("relief")), float(nd("ruggedness")), float(d_conn))


def _feature_scales(ref):
    """Fixed per-feature normalizers from the REFERENCE distribution, so every
    candidate's Pareto axis is divided by the same scale (comparable across
    candidates). IQR with std -> range fallback."""
    out = {}
    for f in ("slope", "relief", "ruggedness"):
        v = np.asarray(ref[f], dtype=float)
        v = v[np.isfinite(v)]
        s = 0.0
        if v.size:
            s = float(np.percentile(v, 75) - np.percentile(v, 25))
            if not np.isfinite(s) or s <= 1e-9:
                s = float(np.std(v))
            if not np.isfinite(s) or s <= 1e-9:
                s = float(np.max(v) - np.min(v))
        out[f] = s if (np.isfinite(s) and s > 1e-9) else 1.0
    return out


def _extended_dims(extended, cid, reference_id):
    """Extra Pareto dimensions from scalar extended metrics (nan-safe)."""
    def diff(key):
        a = extended[cid].get(key)
        b = extended[reference_id].get(key)
        if a is None or b is None or a != a or b != b:  # None or NaN
            return 1.0
        return abs(float(a) - float(b))
    return (diff("aspect_dispersion"), diff("hypsometric_integral"))


def _geomorphic_distributions(z, dx):
    """Map-valued descriptors for the opt-in 'geomorphic' decision mode: ZT mean
    curvature (surface convexity) + Vector Ruggedness Measure (slope-decoupled
    ruggedness), raveled to 1-D distributions comparable like slope/relief."""
    mc = features.mean_curvature(z, dx=dx)
    vrm = features.vector_ruggedness(z, window=3, dx=dx, dy=dx)
    return {"mean_curvature": np.asarray(mc, dtype=float).ravel(),
            "vrm": np.asarray(vrm, dtype=float).ravel()}


def _geomorphic_scales(ref):
    """Reference-IQR normalizers for the geomorphic axes (std->range fallback),
    mirroring _feature_scales so each candidate's axis uses the same scale."""
    out = {}
    for f in ("mean_curvature", "vrm"):
        v = np.asarray(ref[f], dtype=float)
        v = v[np.isfinite(v)]
        s = 0.0
        if v.size:
            s = float(np.percentile(v, 75) - np.percentile(v, 25))
            if not np.isfinite(s) or s <= 1e-9:
                s = float(np.std(v))
            if not np.isfinite(s) or s <= 1e-9:
                s = float(np.max(v) - np.min(v))
        out[f] = s if (np.isfinite(s) and s > 1e-9) else 1.0
    return out


def _geomorphic_dims(geo, cid, reference_id, scales):
    """Two extra Pareto dimensions: normalized distances on mean curvature + VRM."""
    def nd(f):
        return distances.normalized_distance(geo[cid][f], geo[reference_id][f],
                                             scale=scales.get(f))
    return (float(nd("mean_curvature")), float(nd("vrm")))


def _landform_data(z, dx):
    """Per-unit landform descriptors for the opt-in 'landform' capability: the
    geomorphon composition / dominant form / 9x9 (n_plus, n_minus) spectrum
    (Jasiewicz & Stepinski 2013) and the topographic openness signature
    (Yokoyama 2002). ``dx`` is the unit's realized common support in metres.

    This is map-scale MORPHOLOGY only - a description of local surface SHAPE and
    exposure. It makes no traversability, hazard, geologic-unit, or
    mission-readiness claim. Imported lazily so the opt-in capability stays off
    the default study path (keeping core/extended/geomorphic hashes untouched)."""
    from . import geomorphons, openness
    return {
        "composition": geomorphons.composition(z, dx=dx, search=8),
        "dominant_form": geomorphons.geomorphon_signature(z, dx=dx, search=8)["dominant_form"],
        "openness": openness.openness_signature(z, dx=dx, radius=8),
        "spectrum": geomorphons.spectrum(z, dx=dx, search=8).tolist(),
    }


def _landform_dims(lf, cid, reference_id):
    """Two extra Pareto axes for the 'landform' lens, each a candidate->reference
    morphology DISTANCE (0.0 for the reference against itself, same convention as
    the other lenses):

    * ``landform_spectrum`` - half the L1 total variation between the two 9x9
      geomorphon spectra, so it ranges in [0, 1] (0 identical, 1 disjoint);
    * ``openness`` - the mean absolute difference of the positive and negative
      openness medians, normalised by 90 degrees into [0, 1].

    Dissimilarity measures only - no traversability/hazard/mission meaning."""
    spec_c = np.asarray(lf[cid]["spectrum"], dtype=float)
    spec_r = np.asarray(lf[reference_id]["spectrum"], dtype=float)
    axis_spectrum = 0.5 * float(np.abs(spec_c - spec_r).sum())
    oc = lf[cid]["openness"]
    orf = lf[reference_id]["openness"]
    axis_openness = (abs(oc["positive_median"] - orf["positive_median"])
                     + abs(oc["negative_median"] - orf["negative_median"])) / 2.0 / 90.0
    return (axis_spectrum, axis_openness)


def _texture_scalars(z, dx):
    """Three per-unit TEXTURE scalars for the opt-in 'texture' decision lens, each
    computed on the unit's aggregated grid at its realized common support ``dx``
    (metres). Imported lazily so the lens stays off the default study path (keeping
    the core/extended/geomorphic/landform packages and their hashes untouched):

    * ``spectral_slope``   - log-log slope of the radially-averaged power spectral
      density (Fourier roughness-scaling exponent; :mod:`terratrace.spectral`);
    * ``fractal_dim``      - differential box-counting fractal dimension in [2, 3]
      (:mod:`terratrace.fractal`; scale-free, so it takes only ``z``);
    * ``normal_roughness`` - mean surface-normal dispersion ``1 - R`` in [0, 1]
      (:mod:`terratrace.normal_roughness`).

    Map-scale MORPHOLOGY / roughness descriptors only - no traversability, hazard,
    geologic, or mission claim."""
    from . import spectral, fractal, normal_roughness
    return {
        "spectral_slope": float(spectral.spectral_signature(z, dx=dx)["spectral_slope"]),
        "fractal_dim": float(fractal.box_counting_dimension(z)),
        "normal_roughness": float(
            normal_roughness.normal_roughness_signature(z, dx=dx)["roughness_mean"]),
    }


def _texture_dims(tex, cid, reference_id):
    """Three extra Pareto axes for the 'texture' lens, each a candidate->reference
    scalar DISTANCE on one texture descriptor, using the SAME relative convention
    the connectivity-scalar axis uses in :func:`_vector`::

        d = |cand_value - ref_value| / (|ref_value| + 1e-6)

    so the reference against itself is exactly 0.0 on every axis. Returns
    ``(d_spectral, d_fractal, d_normal)``. Dissimilarity measures only - no
    traversability/hazard/mission meaning."""
    def d(key):
        a = float(tex[cid][key])
        b = float(tex[reference_id][key])
        return abs(a - b) / (abs(b) + 1e-6)
    return (d("spectral_slope"), d("fractal_dim"), d("normal_roughness"))


def compare_units(raw_units, rights, native_posting_m, reference_id="mars_reference",
                  target_support_m=100.0, min_valid=0.5, source_label="synthetic",
                  decision_metrics="core", n_boot=0, bootstrap_method="independent",
                  block_size=4, vertical_accuracy=None, previews=False, landform=False,
                  significance=False, n_perm=1000, significance_seed=0,
                  terrain_spectra=False):
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

    dxs = {uid: float(meta[uid]["support"]["target_support_m"]) for uid in agg}
    extended = {}
    for uid, a in agg.items():
        extended[uid] = {
            "aspect_dispersion": features.aspect_dispersion(a, dxs[uid], dxs[uid]),
            "hypsometric_integral": features.hypsometric_integral(a),
            "tpi_dispersion": features.tpi_dispersion(a, window=5),
        }
    # Geomorphic axes are computed ONLY for the opt-in geomorphic mode, so the
    # core/extended study packages (and their provenance hashes) are untouched.
    geo, geo_scales = {}, {}
    if decision_metrics == "geomorphic":
        for uid, a in agg.items():
            geo[uid] = _geomorphic_distributions(a, dxs[uid])
        if reference_id in geo:
            geo_scales = _geomorphic_scales(geo[reference_id])
    # Landform descriptors (geomorphon composition/spectrum + openness) are
    # computed ONLY for the opt-in landform capability (flag or decision mode),
    # on the SAME per-unit aggregated grid at the realized support, so the
    # core/extended/geomorphic study packages (and their hashes) are untouched.
    lf = {}
    if landform or decision_metrics == "landform":
        for uid, a in agg.items():
            lf[uid] = _landform_data(a, dxs[uid])
    # Texture axes (spectral slope + box-counting fractal dimension + surface-
    # normal dispersion roughness) are computed ONLY for the opt-in 'texture'
    # decision lens, on the SAME per-unit aggregated grid at the realized support,
    # so the core/extended/geomorphic/landform study packages (and their hashes)
    # are untouched.
    tex = {}
    if decision_metrics == "texture":
        for uid, a in agg.items():
            tex[uid] = _texture_scalars(a, dxs[uid])
    dx_ref = dxs[reference_id]
    candidate_ids = [u for u in agg if u != reference_id]
    ref_ok, ref_reason = decision.eligibility(meta[reference_id])
    scenario_vectors, baseline_vectors = [], {}
    ref_feats_base, cand_feats_base, scales = None, {}, None
    if ref_ok:
        for cfg in SCENARIOS:
            ref_f = _feature_distributions(agg[reference_id], dx_ref, cfg["slope_threshold"], cfg["relief_alpha"])
            if cfg["name"] == "baseline":
                scales = _feature_scales(ref_f)
                ref_feats_base = ref_f
            vecs = {}
            for cid in candidate_ids:
                ok, _ = decision.eligibility(meta[cid])
                if not ok:
                    continue
                cand_f = _feature_distributions(agg[cid], dxs[cid], cfg["slope_threshold"], cfg["relief_alpha"])
                vec = _vector(ref_f, cand_f, scales)
                if decision_metrics == "extended":
                    vec = vec + _extended_dims(extended, cid, reference_id)
                elif decision_metrics == "geomorphic":
                    vec = vec + _geomorphic_dims(geo, cid, reference_id, geo_scales)
                elif decision_metrics == "landform":
                    vec = vec + _landform_dims(lf, cid, reference_id)
                elif decision_metrics == "texture":
                    vec = vec + _texture_dims(tex, cid, reference_id)
                vecs[cid] = vec
                if cfg["name"] == "baseline":
                    cand_feats_base[cid] = cand_f
            scenario_vectors.append(vecs)
            if cfg["name"] == "baseline":
                baseline_vectors = vecs

    elig_map = {u: decision.eligibility(meta[u]) for u in agg}
    if not ref_ok:
        state = "BLOCKED" if ref_reason.startswith("BLOCKED") else "NOT_COMPARABLE"
        recommended, flips = None, {}
    elif not baseline_vectors and candidate_ids:
        reasons = [elig_map[c][1] for c in candidate_ids]
        state = "BLOCKED" if any(r.startswith("BLOCKED") for r in reasons) else "NOT_COMPARABLE"
        recommended, flips = None, {}
    else:
        eligible_scns = [v for v in scenario_vectors if v]
        state, recommended, flips = decision.resolve_state(baseline_vectors, eligible_scns)
    gap_ledger = gaps.ledger_for(state)
    metric_names = list(METRICS)
    if decision_metrics == "extended":
        metric_names += ["aspect_dispersion", "hypsometric_integral"]
    elif decision_metrics == "geomorphic":
        metric_names += ["mean_curvature", "vector_ruggedness"]
    elif decision_metrics == "landform":
        metric_names += ["landform_spectrum", "openness"]
    elif decision_metrics == "texture":
        metric_names += ["spectral_slope", "fractal_dim", "normal_roughness"]
    profile = {"task": "map_scale_terrain_route_study", "target_body": "mars",
               "target_support_m": float(target_support_m), "metrics": metric_names,
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
    if len(baseline_vectors) >= 2:
        from . import frontier
        package["frontier"] = frontier.summarize(baseline_vectors)
    if decision_metrics == "geomorphic":
        # Report the geomorphic descriptor scalars per unit (incl. the Hurst
        # roughness-scaling exponent). Present only in this opt-in mode, so other
        # modes' packages/hashes are unchanged.
        package["geomorphic_metrics"] = {uid: {
            "hurst_exponent": features.hurst_exponent(agg[uid], dx=dxs[uid]),
            "mean_curvature_median": (float(np.nanmedian(geo[uid]["mean_curvature"]))
                                      if geo[uid]["mean_curvature"].size else float("nan")),
            "vrm_median": (float(np.nanmedian(geo[uid]["vrm"]))
                           if geo[uid]["vrm"].size else float("nan")),
        } for uid in agg}
    if landform or decision_metrics == "landform":
        # Per-unit geomorphon composition / dominant form / 9x9 spectrum +
        # topographic openness signature. Present only for the opt-in landform
        # capability, so other modes' packages/hashes are unchanged. Morphology
        # descriptors only (no traversability/hazard/mission claim).
        package["landform"] = {uid: lf[uid] for uid in agg}
    # Opt-in, GATED per-unit terrain-spectra descriptor block (OFF by default, so
    # run_study's package/hash stays byte-identical). Mirrors the geomorphic/
    # landform opt-in blocks: lazily imported, computed on the SAME aggregated grid
    # at the realized support (agg[uid], dx=dxs[uid]) for each compared/eligible
    # unit, and attaches the "spectral" + "anisotropy" keys ONLY when
    # terrain_spectra=True. Map-scale MORPHOLOGY / roughness-spectrum + directional-
    # fabric descriptors only -- no traversability/hazard/geologic/mission claim.
    if terrain_spectra:
        from . import spectral, anisotropy
        compared = [uid for uid in agg if elig_map[uid][0]]
        package["spectral"] = {uid: spectral.spectral_signature(agg[uid], dx=dxs[uid])
                               for uid in compared}
        package["anisotropy"] = {uid: anisotropy.anisotropy_signature(agg[uid], dx=dxs[uid])
                                 for uid in compared}
    # Optional, OFF by default so the synthetic study package/hash is byte-unchanged.
    # vertical_accuracy (scalar or {uid: sigma_z}) -> propagated feature uncertainty.
    if vertical_accuracy is not None:
        from . import errorprop
        def _sigma(uid):
            return (vertical_accuracy.get(uid) if isinstance(vertical_accuracy, dict)
                    else vertical_accuracy)
        fu = {}
        for uid in agg:
            sz = _sigma(uid)
            if sz is None:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                med_slope = float(np.nanmedian(features.slope_deg(agg[uid], dxs[uid], dxs[uid])))
            if not np.isfinite(med_slope):
                med_slope = 0.0
            fu[uid] = errorprop.propagate_feature_uncertainty(float(sz), dxs[uid], med_slope)
        if fu:
            package["feature_uncertainty"] = fu
    # previews -> inline, self-contained hillshade PNG data-URIs per unit.
    if previews:
        from . import hillshade
        package["previews"] = {uid: hillshade.hillshade_data_uri(agg[uid], dxs[uid], dxs[uid])
                               for uid in agg}
    # Landform/openness preview PNGs ride along only when BOTH the landform flag
    # and previews are on; categorical geomorphon map + grayscale openness field,
    # one self-contained data-URI per unit. Visualisation aids only.
    if landform and previews:
        from . import hillshade, geomorphons, openness
        package["landform_previews"] = {
            uid: hillshade.form_map_png_datauri(
                geomorphons.landforms(agg[uid], dx=dxs[uid], search=8))
            for uid in agg}
        package["openness_previews"] = {
            uid: hillshade.scalar_png_datauri(
                openness.positive_openness(agg[uid], dx=dxs[uid], radius=8))
            for uid in agg}
    if n_boot and baseline_vectors and ref_feats_base is not None:
        from . import uncertainty
        extra = None
        if decision_metrics == "extended":
            extra = {cid: _extended_dims(extended, cid, reference_id) for cid in cand_feats_base}
        elif decision_metrics == "geomorphic":
            extra = {cid: _geomorphic_dims(geo, cid, reference_id, geo_scales) for cid in cand_feats_base}
        elif decision_metrics == "landform":
            extra = {cid: _landform_dims(lf, cid, reference_id) for cid in cand_feats_base}
        elif decision_metrics == "texture":
            extra = {cid: _texture_dims(tex, cid, reference_id) for cid in cand_feats_base}
        if bootstrap_method == "block":
            bc = SCENARIOS[0]
            ref_maps = _feature_maps_2d(agg[reference_id], dx_ref, bc["slope_threshold"], bc["relief_alpha"])
            cand_maps = {cid: _feature_maps_2d(agg[cid], dxs[cid], bc["slope_threshold"], bc["relief_alpha"])
                         for cid in cand_feats_base}
            package["bootstrap"] = uncertainty.block_bootstrap_pareto(
                ref_maps, cand_maps, block=block_size, n_boot=n_boot, seed=0,
                extra_dims=extra, scales=scales)
        else:
            package["bootstrap"] = uncertainty.bootstrap_pareto(
                ref_feats_base, cand_feats_base, n_boot=n_boot, seed=0, extra_dims=extra, scales=scales)
    # Opt-in, GATED resampling significance (OFF by default, so run_study's
    # package/hash stays byte-identical). Mirrors the geomorphic/landform opt-in
    # blocks: lazily imported, attaches a single "significance" key only when
    # significance=True. DISTRIBUTION-SHAPE resampling statistics only (see
    # significance.py) -- not a physical, geologic, or mission claim.
    if significance:
        if state == "RECOMMEND_FOLLOW_UP" and recommended is not None and len(baseline_vectors) >= 2:
            from .significance import permutation_closer_test, effect_size
            # Runner-up = the non-recommended eligible compared candidate with the
            # smallest sum of its core distance vector (baseline_vectors); ties
            # broken by unit-id sort order (min on (sum, uid) picks the lexically
            # first id when the sums tie).
            others = [u for u in baseline_vectors if u != recommended]
            runner_up = min(others, key=lambda u: (float(sum(baseline_vectors[u])), u))
            ref_f, rec_f = ref_feats_base, cand_feats_base[recommended]
            run_f = cand_feats_base[runner_up]
            per_metric = {}
            # Sample-ARRAY metrics (slope/relief/ruggedness) get the permutation
            # test + standardized effect size, using the SAME per-metric scale the
            # decision used (scales[m]).
            for m in ("slope", "relief", "ruggedness"):
                pt = permutation_closer_test(ref_f[m], rec_f[m], run_f[m], n_perm=n_perm,
                                             seed=significance_seed, scale=scales[m])
                per_metric[m] = {
                    "observed_diff": pt["observed_diff"],
                    "p_value_one_sided": pt["p_value_one_sided"],
                    "p_value_two_sided": pt["p_value_two_sided"],
                    "a_closer": pt["a_closer"], "significant": pt["significant"],
                    "effect_size": effect_size(ref_f[m], rec_f[m], run_f[m], scale=scales[m]),
                    "method": "permutation"}
            # Connectivity is one SCALAR per unit, so a permutation is undefined:
            # record only the signed scaled difference of the two scaled
            # connectivity distances (negative => recommended closer), using the
            # SAME scale _vector uses, plus the a_closer flag. Clearly labelled
            # method="scalar" and kept apart from the permutation metrics.
            cs = abs(ref_f["connectivity_scalar"]) + 1e-6
            d_rec = abs(rec_f["connectivity_scalar"] - ref_f["connectivity_scalar"]) / cs
            d_run = abs(run_f["connectivity_scalar"] - ref_f["connectivity_scalar"]) / cs
            conn_obs = float(d_rec - d_run)
            per_metric["connectivity"] = {"observed_diff": conn_obs,
                                          "a_closer": bool(conn_obs < 0), "method": "scalar"}
            # Documented rule: a sample-array metric SUPPORTS the recommendation
            # iff the recommended is the closer one (a_closer) AND its one-sided
            # p-value < 0.05; recommendation_significant iff >=1 such metric.
            sig_ms = [m for m in ("slope", "relief", "ruggedness")
                      if per_metric[m]["a_closer"] and per_metric[m]["p_value_one_sided"] < 0.05]
            package["significance"] = {
                "n_perm": int(n_perm), "seed": int(significance_seed),
                "reference_id": reference_id, "recommended_unit": recommended,
                "runner_up": runner_up, "per_metric": per_metric,
                "n_significant_metrics": int(len(sig_ms)),
                "recommendation_significant": bool(len(sig_ms) >= 1)}
        else:
            if state != "RECOMMEND_FOLLOW_UP":
                reason = f"decision state {state} is not a single RECOMMEND_FOLLOW_UP"
            elif recommended is None:
                reason = "no recommended unit to test"
            else:
                reason = f"only {len(baseline_vectors)} eligible compared unit(s); need >= 2"
            package["significance"] = {"evaluated": False, "state": state,
                                       "reason": reason, "reference_id": reference_id}
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


def load_real_units(units, target_support_m=1000.0, reproject=True):
    """Load AOI unit dicts into (raw, rights, native, reference_ids) arrays.

    Each unit is read (and, with reproject=True, warped to its own local
    azimuthal-equidistant metric grid at target_support_m using the correct body)
    and optional masks are applied. Returns the elevation arrays, rights map,
    per-unit native posting, and the list of ids flagged is_reference. Requires
    rasterio. Shared by run_real_study and the batch runner so both load identically.
    """
    from . import ingest
    raw, rights, native, reference_ids = {}, {}, {}, []
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
            reference_ids.append(u["id"])
    return raw, rights, native, reference_ids


def _unit_vertical_accuracy(unit):
    """Resolve a unit's 1-sigma vertical accuracy (m): explicit override, else the
    catalog value for its demtype/dataset product, else None (skip)."""
    if unit.get("vertical_accuracy_m") is not None:
        return float(unit["vertical_accuracy_m"])
    from . import catalog
    demtype, dataset = unit.get("demtype"), unit.get("dataset")
    for sid, s in catalog.SOURCES.items():
        acc = s.get("access", {})
        if (demtype and acc.get("demtype") == demtype) or (dataset and acc.get("datasetName") == dataset):
            return catalog.vertical_accuracy_for(sid)
    return None


def run_real_study(units, target_support_m=1000.0, min_valid=0.5, reproject=True,
                   decision_metrics="core", n_boot=0, bootstrap_method="independent",
                   block_size=4, previews=False, landform=False,
                   significance=False, n_perm=1000, significance_seed=0,
                   terrain_spectra=False):
    """Compare REAL DEMs.

    units: list of dicts with keys: id, path, native_posting_m, rights_status,
    optional bbox (west,south,east,north in degrees), optional body
    ("mars"/"earth"), and optional is_reference (exactly one is reference).

    With reproject=True (default) each AOI is warped to its own local
    azimuthal-equidistant metric grid at target_support_m before features
    are computed (correct cross-body comparison). Requires rasterio.

    bootstrap_method ("independent" | "block") selects the uncertainty resampler
    when n_boot>0; "block" is the spatial block bootstrap (honest, autocorrelation-
    respecting CIs) with the given block_size in aggregated pixels.

    Real studies also attach propagated measurement uncertainty (from each source's
    catalog vertical accuracy, or a unit-level vertical_accuracy_m override) and,
    with previews=True, an inline self-contained hillshade PNG per unit.

    landform=True opts in to the per-unit landform descriptor block (geomorphon
    composition/spectrum + topographic openness); with previews=True it also adds
    categorical landform and openness preview PNGs. Pass decision_metrics="landform"
    to compare candidates on two extra morphology-dissimilarity axes instead.
    Landform/openness are map-scale morphology descriptors only.

    significance=True opts in to a GATED resampling-significance block on the
    recommendation (one-sided permutation closeness test on the sample-array
    metrics slope/relief/ruggedness + a scalar signed difference on connectivity);
    distribution-shape resampling statistics only, no physical/mission claim.

    terrain_spectra=True opts in to a GATED per-unit terrain-spectra block
    (radially-averaged PSD roughness signature + directional-fabric anisotropy
    signature) attached under "spectral"/"anisotropy" for each compared/eligible
    unit; map-scale morphology / roughness-spectrum descriptors only.
    """
    raw, rights, native, reference_ids = load_real_units(units, target_support_m, reproject)
    reference_id = reference_ids[-1] if reference_ids else None
    if reference_id is None:
        raise ValueError("exactly one unit must set is_reference=True")
    label = "real_dem_aeqd" if reproject else "real_dem"
    vacc = {u["id"]: _unit_vertical_accuracy(u) for u in units}
    vacc = {k: v for k, v in vacc.items() if v is not None} or None
    return compare_units(raw, rights, native, reference_id=reference_id,
                         target_support_m=target_support_m, min_valid=min_valid,
                         source_label=label, decision_metrics=decision_metrics, n_boot=n_boot,
                         bootstrap_method=bootstrap_method, block_size=block_size,
                         vertical_accuracy=vacc, previews=previews, landform=landform,
                         significance=significance, n_perm=n_perm,
                         significance_seed=significance_seed, terrain_spectra=terrain_spectra)


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
