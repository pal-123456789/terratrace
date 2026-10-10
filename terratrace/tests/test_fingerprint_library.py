"""Tests for the cross-body terrain-fingerprint library + similarity search.

Dependency-free, assert-based (no pytest), small fixed-seed synthetic
fixtures -- mirrors the plain ``def test_*()`` style of test_fingerprint.py:
no network, known-ordering assertions over distinct synthetic processes.
Covers the cross-BODY case (rank Earth candidates against planetary
references). Morphological resemblance only; not a classification claim.
"""
import numpy as np

from terratrace import fingerprint_library as FL, synthetic

FIELDS = FL.fingerprint.FINGERPRINT_FIELDS
SHAPE = (48, 48)


def _rough(amplitude, seed, shape=SHAPE):
    return synthetic.rough_field(shape, amplitude=amplitude, seed=seed)


def _mars_like(seed):
    """Rough, tilted plain -- a high-roughness Mars-like reference process."""
    return synthetic.plane(SHAPE, slope_x=0.2, slope_y=0.1) + _rough(5.0, seed)


def _moon_like(seed):
    """Smooth, broad cratered-ish field -- a low-roughness Moon-like process."""
    return synthetic.gaussian_hill(SHAPE, amplitude=15.0, sigma=14.0) + _rough(0.3, seed)


def test_build_library_fingerprints_each_named_terrain():
    terrains = {
        "flat": synthetic.plane(SHAPE, slope_x=0.0, slope_y=0.0),
        "hill": synthetic.gaussian_hill(SHAPE, amplitude=10.0, sigma=10.0),
        "rough": _rough(4.0, seed=11),
    }
    lib = FL.build_library(terrains)
    # one fingerprint per named terrain, keys preserved exactly
    assert set(lib) == set(terrains)
    for name, fp in lib.items():
        assert isinstance(fp, dict), (name, type(fp))
        # exactly the documented fingerprint field set, in order
        assert tuple(fp.keys()) == FIELDS, (name, tuple(fp.keys()))
        assert all(type(v) is float for v in fp.values()), name
    # equals a direct fingerprint of the same array
    assert lib["rough"] == FL.fingerprint.terrain_fingerprint(terrains["rough"])


def test_search_ranks_matching_process_first():
    base_hill = synthetic.gaussian_hill(SHAPE, amplitude=12.0, sigma=12.0)
    terrains = {
        "smooth_plane": synthetic.plane(SHAPE, slope_x=0.05, slope_y=0.0),
        "moderate_hill": base_hill + _rough(0.8, seed=1),
        "very_rough": _rough(10.0, seed=2),
    }
    lib = FL.build_library(terrains)
    # a NEW draw of the moderate-hill process (same base hill, new noise seed)
    query = base_hill + _rough(0.8, seed=777)
    ranked = FL.search(query, lib)
    assert ranked[0][0] == "moderate_hill", ranked
    # full ranking: descending, every entry present exactly once
    sims = [s for _, s in ranked]
    assert sims == sorted(sims, reverse=True), sims
    assert {name for name, _ in ranked} == set(terrains)
    # top=k truncates to the k best, order preserved
    assert FL.search(query, lib, top=1) == ranked[:1]
    assert FL.search(query, lib, top=2) == ranked[:2]


def test_cross_body_table_maps_candidates_to_matching_reference():
    references = {"mars_like": _mars_like(seed=11), "moon_like": _moon_like(seed=12)}
    candidates = {
        "earth_rough": _mars_like(seed=101),    # same process as mars_like
        "earth_smooth": _moon_like(seed=202),   # same process as moon_like
        "earth_other": synthetic.plane(SHAPE, slope_x=0.02) + _rough(1.5, seed=303),
    }
    table = FL.cross_body_table(references, candidates)
    # deterministic sorted name lists
    assert table["references"] == ["mars_like", "moon_like"]
    assert table["candidates"] == ["earth_other", "earth_rough", "earth_smooth"]
    # a similarity entry for EVERY (candidate, reference) pair
    for cand in candidates:
        assert set(table["similarity"][cand]) == set(references), cand
        for ref in references:
            assert isinstance(table["similarity"][cand][ref], float)
    # each matching candidate most resembles the right planetary reference
    assert table["best_reference"]["earth_rough"][0] == "mars_like", table["best_reference"]
    assert table["best_reference"]["earth_smooth"][0] == "moon_like", table["best_reference"]
    # best_reference similarity is exactly the max over that candidate's row
    for cand in candidates:
        best_ref, best_sim = table["best_reference"][cand]
        assert best_sim == max(table["similarity"][cand].values()), cand
        assert table["similarity"][cand][best_ref] == best_sim, cand


def test_cross_body_table_is_deterministic():
    references = {"mars_like": _mars_like(seed=11), "moon_like": _moon_like(seed=12)}
    candidates = {"earth_rough": _mars_like(seed=101), "earth_smooth": _moon_like(seed=202)}
    assert FL.cross_body_table(references, candidates) == \
        FL.cross_body_table(references, candidates)


def test_library_scales_from_passthrough():
    terrains = {
        "a": synthetic.plane(SHAPE, slope_x=0.1, slope_y=0.0),
        "b": synthetic.gaussian_hill(SHAPE, amplitude=8.0, sigma=10.0),
        "c": _rough(3.0, seed=7),
    }
    scales = FL.library_scales_from(terrains)
    assert len(scales) == len(FIELDS)
    assert all(type(s) is float and np.isfinite(s) and s > 0.0 for s in scales), scales
    # pure passthrough to fingerprint.library_scales
    assert scales == FL.fingerprint.library_scales(terrains)
    # usable as scales in a search over the same library (self ranks first)
    lib = FL.build_library(terrains)
    ranked = FL.search(terrains["b"], lib, scales=scales)
    assert {n for n, _ in ranked} == set(terrains)
    assert ranked[0][0] == "b"
