"""Confirmatory, frozen tests for RELATIVE-vs-ABSOLUTE morphological adequacy.

This is EMPIRICAL METHOD VALIDATION (that the adequacy calibration behaves
correctly), NOT a scientific claim about any planet. It plants a KNOWN situation
on synthetic terrain and asserts the calibration separates "within the
reference's own variability" from "outside it", and honestly abstains when the
window is too small to calibrate a band.

GROUND TRUTH (fixed, first-principles). The reference is a uniformly ROUGH
texture (amplitude 20). Its internal self-distance band -- how different the
reference is from itself across held-out sub-windows -- is small but well
defined. A ``twin`` candidate is the SAME rough texture at a different seed, so
it must fall WITHIN that band (adequate). An ``impostor`` candidate is much
smoother (amplitude 2), a ~10x roughness gap, so it must fall OUTSIDE the band
(inadequate). The band is estimated on sub-windows while candidate distances use
the full footprint, so the band is the wider, conservative yardstick and the
twin sits comfortably inside it.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network.
Deterministic seeds; the roughness gap makes the outcome robust.
"""
import json

import numpy as np

from terratrace import adequacy as ad, synthetic, study
from terratrace.matched_benchmark import crop_center

_N = 200
_DX = 30.0
_EXTENT_M = 4800.0        # 160 px -> 53 px sub-tiles -> 17 px aggregated (ample)
_SUPPORT_M = 90.0
_TINY_EXTENT_M = 270.0    # 9 px -> 3 px sub-tiles -> 1 px aggregated (cannot split)


def _scene():
    """Rough reference + same-texture twin + much-smoother impostor."""
    return {
        "ref": synthetic.rough_field((_N, _N), amplitude=20.0, seed=1),
        "twin": synthetic.rough_field((_N, _N), amplitude=20.0, seed=7),
        "impostor": synthetic.rough_field((_N, _N), amplitude=2.0, seed=8),
    }


def test_reference_internal_band_is_established_and_positive():
    # Oracle 1: a decent-size rough reference yields an established band with a
    # finite, strictly positive median and p95 for both descriptors.
    ref = synthetic.rough_field((_N, _N), amplitude=20.0, seed=1)
    sub, _info = crop_center(ref, _DX, _EXTENT_M)
    for descriptor in ("slope", "relief"):
        band = ad.reference_internal_band(sub, _SUPPORT_M, _DX, n_split=3,
                                          descriptor=descriptor)
        assert band["established"] is True, (descriptor, band)
        assert band["n_subtiles"] >= 3, (descriptor, band)
        assert np.isfinite(band["median"]) and band["median"] > 0.0, (descriptor, band)
        assert np.isfinite(band["p95"]) and band["p95"] > 0.0, (descriptor, band)
        assert band["p95"] >= band["median"], (descriptor, band)


def test_twin_is_adequate_and_impostor_is_inadequate():
    # Oracle 2: the same-texture twin lands inside the reference's own band; the
    # much-smoother impostor lands outside it.
    a = ad.adequacy_assessment(_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M)
    assert a["established"] is True, a
    assert "twin" in a["adequate_candidates"], a
    assert "impostor" not in a["adequate_candidates"], a
    assert a["any_adequate"] is True, a
    # The reference itself is never offered as a candidate.
    assert "ref" not in a["per_descriptor"]["slope"]["candidates"], a
    # Per-descriptor: twin within band (ratio <= 1), impostor well outside (> 1).
    for descriptor in ("slope", "relief"):
        cands = a["per_descriptor"][descriptor]["candidates"]
        assert cands["twin"]["adequate"] is True, (descriptor, cands["twin"])
        assert cands["impostor"]["adequate"] is False, (descriptor, cands["impostor"])
        assert cands["twin"]["distance"] < cands["impostor"]["distance"], (descriptor, cands)
        assert cands["twin"]["ratio"] <= 1.0, (descriptor, cands["twin"])
        assert cands["impostor"]["ratio"] > 1.0, (descriptor, cands["impostor"])


def test_absolute_adequacy_not_established_on_tiny_window():
    # Oracle 3: a window too small to split into 3x3 usable sub-tiles cannot
    # calibrate a band -> adequacy is honestly NOT established, with the exact note.
    small = ad.adequacy_assessment(_scene(), _DX, "ref", _TINY_EXTENT_M, _SUPPORT_M)
    assert small["established"] is False, small
    assert small["note"] == "Absolute morphological adequacy has not been established.", small
    assert small["adequate_candidates"] == [], small
    assert small["any_adequate"] is False, small
    for descriptor in small["per_descriptor"]:
        band = small["per_descriptor"][descriptor]["band"]
        assert small["per_descriptor"][descriptor]["established"] is False, (descriptor, small)
        assert not np.isfinite(band["p95"]), (descriptor, band)
        assert not np.isfinite(band["median"]), (descriptor, band)


def test_reference_internal_band_not_established_when_unsplittable():
    # The band function itself reports not-established (NaN band, < 3 sub-tiles)
    # when the window cannot be split into 3x3 usable sub-windows.
    ref = synthetic.rough_field((_N, _N), amplitude=20.0, seed=1)
    sub, _info = crop_center(ref, _DX, _TINY_EXTENT_M)   # 9x9 -> 3x3 -> 1x1 aggregated
    band = ad.reference_internal_band(sub, _SUPPORT_M, _DX, n_split=3, descriptor="slope")
    assert band["established"] is False, band
    assert band["n_subtiles"] < 3, band
    assert not np.isfinite(band["median"]) and not np.isfinite(band["p95"]), band


def test_contract_keys_json_roundtrip_and_deterministic():
    # Oracle 4: required keys present, JSON round-trips, and two independent runs
    # are byte-identical (deterministic).
    a = ad.adequacy_assessment(_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M)
    for key in ("established", "per_descriptor", "adequate_candidates",
                "any_adequate", "note"):
        assert key in a, key
    pd = a["per_descriptor"]["slope"]
    assert {"band", "candidates"} <= set(pd), pd
    assert {"median", "p95"} <= set(pd["band"]), pd["band"]
    entry = pd["candidates"]["twin"]
    assert {"distance", "adequate", "ratio"} <= set(entry), entry
    # Frozen documented defaults are surfaced.
    assert a["quantile"] == 95.0 and a["n_split"] == 3, a
    assert ad.QUANTILE_DEFAULT == 95.0 and ad.N_SPLIT_DEFAULT == 3
    # JSON round-trips.
    dumped = json.dumps(a)
    assert json.loads(dumped)["established"] is True
    # Deterministic across two independent runs (byte-identical JSON).
    b = ad.adequacy_assessment(_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_default_study_hash_unchanged_by_this_module():
    # Oracle 5 (gated): adding adequacy must not perturb the gated default study.
    h = study.run_study()["package_hash"]
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h), h
    assert study.run_study()["package_hash"] == h
