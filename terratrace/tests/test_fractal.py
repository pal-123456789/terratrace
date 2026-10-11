"""Tests for the differential box-counting (DBC) fractal-dimension descriptor
(``terratrace.fractal``, Sarkar & Chaudhuri 1994).

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with known qualitative behaviour, mirroring the style
of test_study.py / test_wavelet_roughness.py / test_hypsometry.py.
"""
import json

import numpy as np

from terratrace import fractal, synthetic


def _smooth_sinusoid(shape=(128, 128)):
    """A gentle single-period 2-D sinusoid -- very smooth, low complexity."""
    rows, cols = shape
    i, j = np.indices(shape)
    return 10.0 * np.sin(2.0 * np.pi * j / cols) * np.sin(2.0 * np.pi * i / rows)


def test_plane_dimension_two():
    # A tilted plane is a 2-D surface -> box-counting dimension ~ 2.0.
    z = synthetic.plane((128, 128), slope_x=0.08, slope_y=0.05)
    D = fractal.box_counting_dimension(z)
    assert abs(D - 2.0) < 0.2, D


def test_rough_greater_than_smooth():
    # A seeded rough (white-noise) field fills more of its bounding volume at
    # every scale than a gentle sinusoid, so its dimension is strictly greater.
    rough = synthetic.rough_field((128, 128), 1.0, seed=7)
    smooth = _smooth_sinusoid((128, 128))
    D_rough = fractal.box_counting_dimension(rough)
    D_smooth = fractal.box_counting_dimension(smooth)
    assert D_rough > D_smooth, (D_rough, D_smooth)


def test_white_noise_high_dimension():
    # Seeded white noise is near space-filling -> dimension well above 2.5.
    z = synthetic.rough_field((128, 128), 1.0, seed=3)
    D = fractal.box_counting_dimension(z)
    assert D > 2.5, D


def test_bounds_and_contract():
    z = synthetic.rough_field((96, 96), 2.0, seed=11)
    D = fractal.box_counting_dimension(z)
    assert 2.0 <= D <= 3.0, D
    sig = fractal.fractal_signature(z)
    assert set(sig) == {"box_count_dimension", "r2", "n_scales"}, set(sig)
    assert type(sig["box_count_dimension"]) is float
    assert type(sig["r2"]) is float
    assert type(sig["n_scales"]) is int
    assert 2.0 <= sig["box_count_dimension"] <= 3.0, sig["box_count_dimension"]
    assert 0.0 <= sig["r2"] <= 1.0, sig["r2"]
    assert sig["n_scales"] >= 3, sig["n_scales"]
    dumped = json.dumps(sig)                              # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert fractal.fractal_signature(z) == sig            # deterministic


def test_monotone_amplitude():
    # Adding progressively more roughness to a fixed plane cannot DECREASE the
    # dimension (the normalisation makes a pure scalar rescale a no-op, so this
    # exercises genuine added complexity). Allow equality within 0.05.
    base = synthetic.plane((128, 128), slope_x=0.1, slope_y=0.03)
    noise = synthetic.rough_field((128, 128), 1.0, seed=5)
    dims = [fractal.box_counting_dimension(base + a * noise)
            for a in (0.3, 1.0, 3.0, 9.0)]
    for lo, hi in zip(dims, dims[1:]):
        assert hi >= lo - 0.05, (lo, hi, dims)


def test_degenerate_and_nan_safe():
    # A relief-free (constant) grid has no surface structure -> D == 2.0 exactly.
    const = synthetic.constant((64, 64), 7.0)
    assert fractal.box_counting_dimension(const) == 2.0
    sig_c = fractal.fractal_signature(const)
    assert sig_c["box_count_dimension"] == 2.0
    assert 0.0 <= sig_c["r2"] <= 1.0

    # A few NaNs are filled with the finite mean -> no raise, finite dimension.
    z = synthetic.rough_field((64, 64), 1.0, seed=2)
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 2] = np.nan
    D = fractal.box_counting_dimension(z)
    assert np.isfinite(D) and 2.0 <= D <= 3.0, D
    sig = fractal.fractal_signature(z)
    assert np.isfinite(sig["box_count_dimension"])
    assert json.loads(json.dumps(sig)) is not None
