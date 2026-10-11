"""Offline tests for terratrace.multiscale (scale-resolved analog analysis).

Dependency-free (plain top-level ``test_*`` + ``assert``), strictly OFFLINE and
yaml-free: multiscale only re-runs the proven ``study.compare_units`` at a sweep
of supports, so no PyYAML, rasterio, or network is needed. The verify command
runs this module with ``sys.modules['yaml'] = None`` to prove it has no
accidental top-level ``import yaml``. Grids are 80x80 and the sweeps are short so
the whole module runs in a couple of seconds.
"""
import json

import numpy as np

from terratrace import multiscale, synthetic

_NATIVE = 1000.0
_SHAPE = (80, 80)


def _scene(ref_amp=5.0):
    """A 3-unit scene: reference; an identical twin; and a FAR unit carrying a
    large, scale-persistent structure (a much steeper plane + roughness)."""
    base = synthetic.plane(_SHAPE, slope_x=0.02, dx=_NATIVE)
    ref = base + synthetic.rough_field(_SHAPE, amplitude=ref_amp, seed=1)
    twin = ref.copy()                                   # identical candidate
    far = (ref + synthetic.plane(_SHAPE, slope_x=0.4, dx=_NATIVE)
           + synthetic.rough_field(_SHAPE, amplitude=15.0, seed=3))
    raw = {"ref": ref, "twin": twin, "far": far}
    rights = {u: "verified_allowed" for u in raw}
    return raw, rights


def test_scale_profile_shape_and_ascending():
    raw, rights = _scene()
    prof = multiscale.scale_profile(raw, rights, _NATIVE, "ref",
                                    supports=[2000.0, 1000.0, 1500.0])  # unsorted in
    assert prof["supports"] == sorted(prof["supports"]), prof["supports"]
    assert prof["supports"] == [1000.0, 1500.0, 2000.0], prof["supports"]
    assert prof["reference_id"] == "ref"
    assert set(prof["candidates"]) == {"twin", "far"}
    n = len(prof["supports"])
    for c in prof["candidates"]:
        assert len(prof["per_candidate"][c]["distance"]) == n, c
        assert len(prof["per_candidate"][c]["layer"]) == n, c
    assert len(prof["best_by_support"]) == n
    assert len(prof["result_by_support"]) == n


def test_identical_twin_is_layer1_at_all_scales():
    raw, rights = _scene()
    prof = multiscale.scale_profile(raw, rights, _NATIVE, "ref",
                                    supports=[1000.0, 1500.0, 2000.0])
    band = multiscale.analog_scale_band(prof, "twin")
    assert band["fraction_layer1"] == 1.0, band
    assert band["band"] == (1000.0, 2000.0), band
    assert band["supports_layer1"] == [1000.0, 1500.0, 2000.0], band
    # A twin identical to the reference has ~zero distance at every scale.
    for d in prof["per_candidate"]["twin"]["distance"]:
        assert d < 1e-6, d
    # The far unit is dominated at the finest support (not layer 1).
    assert prof["per_candidate"]["far"]["layer"][0] != 1, prof["per_candidate"]["far"]


def test_best_analog_by_scale_one_entry_per_support():
    raw, rights = _scene()
    prof = multiscale.scale_profile(raw, rights, _NATIVE, "ref",
                                    supports=[1000.0, 1500.0, 2000.0])
    best = multiscale.best_analog_by_scale(prof)
    assert len(best) == len(prof["supports"])
    for (s, unit), s_expected in zip(best, prof["supports"]):
        assert s == s_expected
        assert unit is None or unit in raw


def test_signature_is_json_serialisable():
    raw, rights = _scene()
    prof = multiscale.scale_profile(raw, rights, _NATIVE, "ref",
                                    supports=[1000.0, 2000.0])
    sig = multiscale.scale_profile_signature(prof)
    dumped = json.dumps(sig)                            # must not raise
    assert isinstance(dumped, str) and dumped
    assert isinstance(sig["scale_stable"], bool)
    for c in prof["candidates"]:
        assert "fraction_layer1" in sig["per_candidate"][c]
        assert "band" in sig["per_candidate"][c]
    json.dumps(prof)                                    # whole profile round-trips too


def test_fine_noise_averages_out_with_coarser_support():
    """A candidate that is reference + FINE white noise sits CLOSER to the smooth
    reference at a COARSE support than at the finest one: block aggregation
    averages the fine noise away. This proves the profile captures real scale
    sensitivity (not a constant distance at every support)."""
    base = synthetic.plane(_SHAPE, slope_x=0.02, dx=_NATIVE)
    ref = base.copy()
    noisy = ref + synthetic.rough_field(_SHAPE, amplitude=20.0, seed=7)
    raw = {"ref": ref, "noisy": noisy}
    rights = {u: "verified_allowed" for u in raw}
    prof = multiscale.scale_profile(raw, rights, _NATIVE, "ref",
                                    supports=[1000.0, 4000.0])  # finest, coarsest
    d = prof["per_candidate"]["noisy"]["distance"]
    assert np.isfinite(d[0]) and np.isfinite(d[1]), d
    assert d[-1] < d[0], f"coarse {d[-1]} should be < fine {d[0]} (noise averages out)"


if __name__ == "__main__":
    for _name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[_name]()
    print("OK")
