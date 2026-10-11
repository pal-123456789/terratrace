"""Tests for the two-scale (multi-scale) Weiss (2001) TPI slope-position module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring test_slope_area.py /
test_tpi_landform.py.

These exercise a purely GEOMETRIC, two-scale topographic-POSITION classification
of the sampled surface (nested slope position); nothing here is a geological-unit,
process, hazard, traversability, or mission claim on any body.
"""
import json

import numpy as np

from terratrace import multiscale_tpi as mstpi
from terratrace import synthetic

_NAMES = {
    "valley", "lower_slope_channel", "lower_slope", "flat_midslope",
    "upper_slope", "upper_slope_ridge", "hilltop",
}
_HIGH_POSITION = {"hilltop", "upper_slope_ridge", "upper_slope"}
_LOW_POSITION = {"valley", "lower_slope_channel"}


def _radial(shape=(81, 81)):
    """Radial distance ``r`` from the grid centre (for cone / bowl oracles)."""
    rows, cols = shape
    ii, jj = np.indices(shape)
    return np.hypot(ii - (rows - 1) / 2.0, jj - (cols - 1) / 2.0)


def test_cone_peak_is_high_position():
    # Oracle 1: z = -r is a single peak at the centre (a local AND regional high),
    # so the centre cell must land in a HIGH slope-position class.
    r = _radial((81, 81))
    classes = mstpi.multiscale_tpi_classes(-r)
    code = int(classes[40, 40])
    assert code >= 0, code
    assert mstpi.CODE_TO_NAME[code] in _HIGH_POSITION, mstpi.CODE_TO_NAME[code]


def test_bowl_pit_is_low_position():
    # Oracle 2: z = +r is a single pit at the centre (a local AND regional low),
    # so the centre cell must land in a LOW slope-position class.
    r = _radial((81, 81))
    classes = mstpi.multiscale_tpi_classes(r)
    code = int(classes[40, 40])
    assert code >= 0, code
    assert mstpi.CODE_TO_NAME[code] in _LOW_POSITION, mstpi.CODE_TO_NAME[code]


def test_plane_dominated_by_flat_midslope():
    # Oracle 3: a constant-gradient plane has ~0 TPI at every interior cell and
    # at both scales, so the grid is dominated by the flat_midslope class.
    z = synthetic.plane((80, 80), slope_x=0.03, dx=10.0)
    sig = mstpi.multiscale_tpi_signature(z)
    assert sig["dominant_class"] == "flat_midslope", sig


def test_signature_contract():
    # Oracle 4: exactly the 7 class keys, float fractions summing to ~1 over the
    # classified cells, a valid dominant name, JSON round-trip, determinism.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = mstpi.multiscale_tpi_signature(z)
    comp = sig["composition"]
    assert set(comp) == _NAMES, set(comp)
    assert all(type(v) is float for v in comp.values())
    assert abs(sum(comp.values()) - 1.0) < 1e-6, sum(comp.values())
    assert sig["dominant_class"] in _NAMES, sig["dominant_class"]
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert json.dumps(mstpi.multiscale_tpi_signature(z)) == dumped  # deterministic


def test_nan_safe():
    # Oracle 5: a few NaN cells raise nothing; a NaN cell -> sentinel; the
    # signature stays valid and JSON round-trips.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    classes = mstpi.multiscale_tpi_classes(z)                  # must not raise
    assert classes.shape == z.shape
    assert int(classes[5, 5]) == mstpi.SENTINEL                # NaN cell -> -1
    sig = mstpi.multiscale_tpi_signature(z)                    # must not raise
    assert set(sig["composition"]) == _NAMES
    assert abs(sum(sig["composition"].values()) - 1.0) < 1e-6
    assert json.loads(json.dumps(sig)) is not None
