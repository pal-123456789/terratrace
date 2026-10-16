"""Confirmatory, frozen ground-truth test for the matched-footprint benchmark.

This is EMPIRICAL METHOD VALIDATION (that the harness behaves correctly), NOT a
scientific discovery about Mars. It plants a KNOWN footprint confound on synthetic
terrain and asserts the harness detects and corrects it.

GROUND TRUTH (fixed, first-principles). The reference is heterogeneous: a small
ROUGH core (texture amplitude 25) inside a large SMOOTH apron (amplitude 4). The
scientific area of interest is the rough core. Candidate B_rough is uniformly rough
(25); A_smooth is uniformly smooth (4). For the core AOI the reference is rough, so
B_rough is the morphologically correct analog. Enlarging the reference window
dilutes the rough core with the smooth apron, lowering its measured roughness -- so
a MISMATCHED comparison (reference window >> candidate windows) should wrongly prefer
A_smooth, while a MATCHED comparison at the core extent should recover B_rough.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network.
Deterministic seeds; the 6x roughness gap makes the recommendation robust.
"""
import json

import numpy as np

from terratrace import matched_benchmark as mb, synthetic, features, support as sup

_N = 400
_DX = 30.0
_CORE_RADIUS_M = 700.0
_SMALL_EXTENT_M = 1200.0
_LARGE_EXTENT_M = 12000.0
_SUPPORT_M = 90.0


def _scene():
    """The frozen synthetic scene: rough-core reference + smooth/rough candidates."""
    ii, jj = np.indices((_N, _N))
    r = np.hypot(ii - _N // 2, jj - _N // 2) * _DX
    core = r < _CORE_RADIUS_M
    X = synthetic.rough_field((_N, _N), amplitude=25.0, seed=1)
    Y = synthetic.rough_field((_N, _N), amplitude=4.0, seed=1)
    ref = np.where(core, X, Y)
    return {
        "ref": ref,
        "A_smooth": synthetic.rough_field((_N, _N), amplitude=4.0, seed=2),
        "B_rough": synthetic.rough_field((_N, _N), amplitude=25.0, seed=3),
    }


def test_crop_center_dimensions_and_truncation():
    z = np.zeros((100, 80))
    sub, info = mb.crop_center(z, 30.0, 1200.0)      # 1200/30 = 40 px
    assert sub.shape == (40, 40), sub.shape
    assert info["n_pixels"] == 40 and not info["truncated"]
    assert abs(info["actual_extent_m"] - 1200.0) < 1e-9
    sub2, info2 = mb.crop_center(z, 30.0, 9000.0)    # 300 px requested > 80 -> truncate
    assert info2["truncated"] and sub2.shape[0] == 80


def test_effective_resolution_and_upsampling_flag():
    assert mb.effective_resolution_m(30.0, factor=3.0) == 90.0
    prov_fine = mb.cell_provenance("u", {"src_spacing_m": 30.0, "actual_extent_m": 1200.0,
                                         "n_pixels": 40, "valid_fraction": 1.0,
                                         "truncated": False}, support_m=60.0)
    assert prov_fine["upsampling_risk"] is True          # 60 < 3*30
    prov_ok = mb.cell_provenance("u", {"src_spacing_m": 30.0, "actual_extent_m": 1200.0,
                                       "n_pixels": 40, "valid_fraction": 1.0,
                                       "truncated": False}, support_m=90.0)
    assert prov_ok["upsampling_risk"] is False           # 90 == 3*30
    assert prov_ok["support_cells_per_side"] == 13 and prov_ok["usable_blocks"] == 9


def test_matched_small_extent_recovers_rough_core():
    # Oracle: at the core extent the reference is rough -> B_rough is the match.
    cell = mb.matched_cell(_scene(), _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M,
                           decision_metrics="core")
    assert cell["recommended_unit"] == "B_rough", cell
    assert cell["mode"] == "matched" and cell["extent_m"] == _SMALL_EXTENT_M


def test_mismatched_footprint_flips_to_wrong_analog():
    # Oracle: diluting the reference with its smooth apron (big ref window, small
    # candidate windows) wrongly prefers A_smooth -- and differs from the matched
    # answer. This is the confound the matched protocol corrects.
    scene = _scene()
    matched = mb.matched_cell(scene, _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M,
                              decision_metrics="core")
    mismatched = mb.mismatched_cell(scene, _DX, "ref", _LARGE_EXTENT_M,
                                    _SMALL_EXTENT_M, _SUPPORT_M, decision_metrics="core")
    assert mismatched["recommended_unit"] == "A_smooth", mismatched
    assert matched["recommended_unit"] != mismatched["recommended_unit"]
    assert mismatched["footprint_ratio"] == 10.0


def test_confound_mechanism_reference_roughness_drops_with_extent():
    # The quantified mechanism: the reference's measured ruggedness is markedly
    # higher at the core extent than at the large extent (apron dilution).
    ref = _scene()["ref"]
    med = {}
    for ext in (_SMALL_EXTENT_M, _LARGE_EXTENT_M):
        subz, _ = mb.crop_center(ref, _DX, ext)
        agg, _ = sup.block_aggregate(subz, 3, _DX, min_valid=0.5)
        med[ext] = float(np.nanmedian(features.ruggedness(agg, window=5, dx=90.0, dy=90.0)))
    assert med[_SMALL_EXTENT_M] > 2.0 * med[_LARGE_EXTENT_M], med


def test_cell_is_json_serialisable_and_deterministic():
    scene = _scene()
    a = mb.matched_cell(scene, _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M)
    dumped = json.dumps(a)
    assert json.loads(dumped)["recommended_unit"] == "B_rough"
    b = mb.matched_cell(_scene(), _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M)
    assert a["recommended_unit"] == b["recommended_unit"]
    for key in ("mode", "extent_m", "support_m", "provenance", "pareto_layer1"):
        assert key in a


def test_extent_support_grid_shape_and_keys():
    grid = mb.extent_support_grid(_scene(), _DX, "ref",
                                  extents=[_SMALL_EXTENT_M, 2400.0],
                                  supports=[90.0, 150.0], decision_metrics="core")
    assert len(grid["cells"]) == 4
    for c in grid["cells"]:
        assert set(("extent_m", "support_m", "result_state", "recommended_unit",
                    "provenance")) <= set(c)
    assert json.loads(json.dumps(grid)) is not None


def test_default_study_hash_unchanged_by_this_module():
    # The harness WRAPS compare_units; it must not perturb the gated default study.
    from terratrace import study
    h = study.run_study()["package_hash"]
    assert len(h) == 64 and all(ch in "0123456789abcdef" for ch in h)
    assert study.run_study()["package_hash"] == h


def test_single_descriptor_baselines_agree_at_matched_footprint():
    # Naive slope-only and relief-only baselines, under the SAME matched footprint,
    # also pick the rough core -> the matched answer is not an artifact of the full
    # machinery. (What the full approach adds is confound detection + trade-offs.)
    scene = _scene()
    for descriptor in ("slope", "relief"):
        b = mb.single_descriptor_baseline(scene, _DX, "ref", _SMALL_EXTENT_M,
                                          _SUPPORT_M, descriptor=descriptor)
        assert b["closest"] == "B_rough", (descriptor, b)
        assert b["distances"]["B_rough"] < b["distances"]["A_smooth"], b


def test_lens_ablation_shape_and_core_recommendation():
    la = mb.lens_ablation_matched(_scene(), _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M)
    assert set(la) == {"core", "extended", "geomorphic", "landform", "texture", "hydro"}
    assert la["core"]["recommended_unit"] == "B_rough"
    for lens, v in la.items():
        assert set(("result_state", "recommended_unit", "pareto_layer1")) <= set(v)


def test_selection_adjusted_pvalue_is_conservative_and_bounded():
    assert mb.selection_adjusted_pvalue(0.02, 2) == 0.04      # Bonferroni over K=2
    assert mb.selection_adjusted_pvalue(0.6, 3) == 1.0        # clamped at 1
    assert mb.selection_adjusted_pvalue(0.05, 1) == 0.05      # K=1 -> unchanged
    assert np.isnan(mb.selection_adjusted_pvalue(float("nan"), 2))


def test_block_bootstrap_surfaces_through_harness():
    # Spatial-block resampling is the PRIMARY uncertainty treatment; it must flow
    # through the harness when requested, with a frequency per unit in [0, 1].
    cell = mb.matched_cell(_scene(), _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M,
                           decision_metrics="core", n_boot=80, bootstrap_method="block",
                           block_size=4)
    nd = cell.get("nondominated_freq")
    assert nd is not None and cell.get("bootstrap_method") == "block"
    assert all(0.0 <= f <= 1.0 for f in nd.values())
    assert nd[cell["recommended_unit"]] >= 0.5


# --------------------------------------------------------------------------- #
# Frontier pass-through: the cell carries the engine's FULL baseline frontier  #
# (every Pareto layer + the pairwise dominance matrix), additively.            #
# --------------------------------------------------------------------------- #
_PRE_EXISTING_CELL_KEYS = {"result_state", "recommended_unit", "pareto_layer1",
                           "package_hash", "mode", "extent_m", "support_m",
                           "decision_metrics", "reference_id", "provenance"}
_FRONTIER_KEYS = {"pareto_layers", "dominance_matrix"}


def _winner(dom, a, b):
    """Dominance-matrix entry for a pair (key = the two ids sorted, '|'-joined)."""
    return dom["|".join(sorted((a, b)))]


def test_matched_cell_passes_through_pareto_layers_and_dominance_matrix():
    scene = _scene()
    scene["C_mid"] = synthetic.rough_field((_N, _N), amplitude=12.0, seed=4)
    cell = mb.matched_cell(scene, _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M,
                           decision_metrics="core")
    # Additive only: the pre-existing keys are all still there, plus exactly two.
    assert set(cell) == _PRE_EXISTING_CELL_KEYS | _FRONTIER_KEYS, sorted(cell)
    layers, dom = cell["pareto_layers"], cell["dominance_matrix"]
    assert isinstance(layers, list) and all(isinstance(layer, list) for layer in layers)
    assert isinstance(dom, dict)
    assert layers and set(layers[0]) == set(cell["pareto_layer1"]), (layers, cell)
    cands = sorted(u for u in scene if u != "ref")
    # Every (eligible) candidate sits in exactly one layer; the reference in none.
    assert sorted(u for layer in layers for u in layer) == cands, layers
    # One entry per sorted candidate pair; each value is one of the pair or "~".
    pairs = {f"{a}|{b}" for i, a in enumerate(cands) for b in cands[i + 1:]}
    assert set(dom) == pairs, dom
    for key, v in dom.items():
        assert v in key.split("|") + ["~"], (key, v)
    # The matrix and the layers agree: nobody dominates a layer-1 unit, no unit
    # dominates another in its own layer, and every deeper unit is dominated by
    # some unit of the layer above (strict Pareto peeling).
    rank = {u: li for li, layer in enumerate(layers) for u in layer}
    for u in cands:
        beaten_by = [o for o in cands if o != u and _winner(dom, u, o) == o]
        assert all(rank[o] < rank[u] for o in beaten_by), (u, beaten_by, layers)
        if rank[u] == 0:
            assert beaten_by == [], (u, beaten_by)
        else:
            assert any(rank[o] == rank[u] - 1 for o in beaten_by), (u, beaten_by, layers)
    back = json.loads(json.dumps(cell, allow_nan=False))
    assert back["pareto_layers"] == layers and back["dominance_matrix"] == dom


def test_frontier_pass_through_empty_when_engine_builds_no_frontier():
    # One candidate -> the engine builds no frontier: empty list / dict (and the
    # pre-existing pareto_layer1 behaviour is unchanged: []).
    scene = _scene()
    cell = mb.matched_cell({"ref": scene["ref"], "B_rough": scene["B_rough"]}, _DX,
                           "ref", _SMALL_EXTENT_M, _SUPPORT_M)
    assert cell["pareto_layers"] == [] and cell["dominance_matrix"] == {}, cell
    assert cell["pareto_layer1"] == [], cell
    # The mismatched control carries the same pass-through (shared _run_compare).
    mism = mb.mismatched_cell(scene, _DX, "ref", _LARGE_EXTENT_M, _SMALL_EXTENT_M,
                              _SUPPORT_M, decision_metrics="core")
    assert set(mism["pareto_layers"][0]) == set(mism["pareto_layer1"]), mism
    assert set(mism["dominance_matrix"]) == {"A_smooth|B_rough"}, mism
    assert mism["dominance_matrix"]["A_smooth|B_rough"] in ("A_smooth", "B_rough", "~")
    # The lens ablation still exposes exactly its three keys per lens.
    la = mb.lens_ablation_matched(scene, _DX, "ref", _SMALL_EXTENT_M, _SUPPORT_M,
                                  lenses=("core",))
    assert set(la["core"]) == {"result_state", "recommended_unit", "pareto_layer1"}, la
