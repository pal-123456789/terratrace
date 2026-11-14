"""The common grid: the invariants that make a comparison a comparison.

These tests exist because the first lunar panel published "exact common support and matched
footprint" while running 16.000 km of Moon against 15.810 km of Earth, at 500 m against 510 m, and
recording `cells=[32, 32], support_m=500.0` for a grid that was 31 x 31. Every one of those numbers
is reproduced below as a *rejected* case, so the defect cannot come back quietly.

The pure half needs nothing but NumPy, so it runs on the CI interpreters. The half that touches
rasterio or the 40 MB products raises `Skip` with a reason when they are absent — it is not counted
as a pass, because "the suite is green" must not be read as "the real-data path was exercised".
"""
import pathlib
import sys
import tempfile

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))
from harness import require                                    # noqa: E402

from terratrace import common_grid as cg                       # noqa: E402

F = cg.DEFAULT_FOOTPRINT_M
MOON_TIF = _ROOT / "data" / "moon" / "Site01_surf.tif"
EARTH_TIF = _ROOT / "data" / "earth" / "nevada_basin_cop30.tif"
EARTH_LONLAT = (-115.6, 36.2)
MOON_LONLAT = (-137.4896, -89.4632)     # Site01 window centre, in the Moon's own geographic CRS


def _rasterio():
    try:
        import rasterio                                         # noqa: F401
        return rasterio
    except Exception as exc:
        raise cg.ComparabilityError(f"rasterio unavailable: {exc}") from exc


# ------------------------------------------------------------------ plan: whole cells or refuse

def test_plan_accepts_only_whole_numbers_of_cells():
    """A footprint that is not a whole number of cells is two different ground areas. Refused."""
    assert cg.plan(9000.0, 500.0) == 18
    assert cg.plan(9000.0, 750.0) == 12
    assert cg.plan(9000.0, 1000.0) == 9
    for footprint, support in ((9000.0, 700.0), (10000.0, 750.0), (9000.0, 400.0), (16000.0, 750.0)):
        try:
            cg.plan(footprint, support)
        except cg.ComparabilityError:
            continue
        raise AssertionError(f"plan({footprint}, {support}) was accepted; it is not exact")


def test_plan_refuses_nonsense_supports():
    for footprint, support in ((9000.0, 0.0), (9000.0, -500.0), (0.0, 500.0)):
        try:
            cg.plan(footprint, support)
        except cg.ComparabilityError:
            continue
        raise AssertionError(f"plan({footprint}, {support}) was accepted")


# ------------------------------------------------------------------ the grid itself

def test_destination_grid_is_centred_exact_and_square():
    """The transform must describe exactly n cells of the requested support, centred on the point.

    It must also be plain arithmetic: this is the pure half of the module, and it has to run on the
    NumPy-only CI interpreter. The first version returned an ``affine.Affine`` and imported that
    library directly — an undeclared transitive dependency of rasterio — which turned three green
    CI interpreters red. The type assertions below are the guard, not decoration: an Affine has no
    ``len()``, so reintroducing one fails here.
    """
    for support in (500.0, 750.0, 1000.0):
        n = cg.plan(F, support)
        crs, coefficients, half = cg.destination_grid(36.2, -115.6, "earth", support, n)
        assert isinstance(coefficients, tuple) and len(coefficients) == 6, (
            f"destination_grid returned {type(coefficients).__name__}, not a 6-tuple of numbers; "
            f"the pure half of this module must not need a third-party transform class")
        assert all(isinstance(v, float) for v in coefficients), coefficients
        a, b, c, d, e, f = coefficients
        assert abs(a - support) < 1e-9 and abs(e + support) < 1e-9, \
            "the cell size in the transform is not the requested support"
        assert abs(c + half) < 1e-6 and abs(f - half) < 1e-6, \
            "the grid is not centred on the projection origin"
        assert b == 0.0 and d == 0.0, "the grid is rotated relative to its own east/north frame"
        assert abs(half - n * support / 2.0) < 1e-9
        assert n * support == F, "the footprint is not n * support"
        assert "aeqd" in str(crs), "the destination must be azimuthal equidistant (ground metres)"


# ------------------------------------------------------------------ the comparability gate

def _rec(n=18, support=500.0, **over):
    r = {"cells": [n, n], "support_m_requested": support,
         "support_m_achieved": [support, support],
         "footprint_m": [n * support, n * support], "exact": True}
    r.update(over)
    return r


def test_the_gate_accepts_two_units_on_the_same_ground():
    cg.assert_comparable({"moon": _rec(), "earth": _rec()}, label="ok")


def test_the_gate_rejects_a_support_mismatch():
    """The measured defect: Moon 500 m against Earth 510 m."""
    try:
        cg.assert_comparable({"moon": _rec(support=500.0), "earth": _rec(support=510.0)},
                             label="lunar 500 m")
    except cg.ComparabilityError as exc:
        assert "support_m_requested" in str(exc), exc
        return
    raise AssertionError("a 500 m vs 510 m comparison was allowed")


def test_the_gate_rejects_a_footprint_mismatch_even_at_equal_support():
    """The other half of the measured defect: equal cells and support, different ground covered.

    Footprint is derived as ``n * support``, so this can only arise from an inconsistent record —
    which is exactly the kind of record the published artifact was carrying, and the gate must
    catch it rather than trust the arithmetic.
    """
    a = _rec()
    b = _rec(footprint_m=[15500.0, 15500.0])          # same cells, same support, different ground
    try:
        cg.assert_comparable({"moon": a, "earth": b}, label="lunar footprint")
    except cg.ComparabilityError as exc:
        assert "footprint_m" in str(exc), exc
        return
    raise AssertionError("a 9.000 km vs 15.500 km comparison was allowed")


def test_the_gate_rejects_a_cell_count_mismatch():
    try:
        cg.assert_comparable({"moon": _rec(n=32), "earth": _rec(n=31)}, label="cells")
    except cg.ComparabilityError as exc:
        assert "cells" in str(exc), exc
        return
    raise AssertionError("32 x 32 against 31 x 31 was allowed")


def test_the_gate_rejects_a_record_that_admits_it_is_not_exact():
    try:
        cg.assert_comparable({"moon": _rec(), "earth": _rec(exact=False)}, label="inexact")
    except cg.ComparabilityError as exc:
        assert "exact" in str(exc), exc
        return
    raise AssertionError("a grid flagged as inexact was still ranked")


def test_the_gate_rejects_an_empty_comparison():
    try:
        cg.assert_comparable({}, label="empty")
    except cg.ComparabilityError:
        return
    raise AssertionError("an empty comparison was allowed")


def test_the_published_defect_replayed_end_to_end_is_refused():
    """The exact numbers from the shipped artifact, as a single regression test.

    The published panel compared, at a requested 500 m:
        Moon  500 m, 32 x 32 cells, 16.000 km
        Earth 510 m, 31 x 31 cells, 15.810 km
    and recorded cells=[32, 32] and support_m=500.0 for both. This asserts that shape is refused.
    """
    moon = {"cells": [32, 32], "support_m_requested": 500.0, "support_m_achieved": [500.0, 500.0],
            "footprint_m": [16000.0, 16000.0], "exact": True}
    earth = {"cells": [31, 31], "support_m_requested": 510.0, "support_m_achieved": [510.0, 510.0],
             "footprint_m": [15810.0, 15810.0], "exact": True}
    try:
        cg.assert_comparable({"LUNAR_Site01": moon, "earth_nevada_basin": earth}, label="as published")
    except cg.ComparabilityError:
        pass
    else:
        raise AssertionError("the published (defective) comparison would still be ranked")


def test_the_resolution_gate_enforces_the_source_floor_before_descriptors():
    """A support below 3x the source posting cannot be compared there, and says so."""
    ok = {"support_m_requested": 500.0, "source_posting_m": 30.0, "source_floor_m": 90.0}
    cg.resolution_gate(ok, label="earth 500 m")
    bad = {"support_m_requested": 30.0, "source_posting_m": 30.0, "source_floor_m": 90.0}
    try:
        cg.resolution_gate(bad, label="earth 30 m")
    except cg.ComparabilityError as exc:
        assert "floor" in str(exc), exc
        return
    raise AssertionError("a support below the source floor was allowed into a comparison")


# ------------------------------------------------------------------ real grids (gated)

def test_real_moon_and_earth_build_identical_exact_grids():
    """The whole point, on the actual data: same cells, same support, same ground, both bodies."""
    require(MOON_TIF.exists(), "the 39 MB LOLA Site01 product is absent; re-fetch with "
                              "scripts/fetch_lola.py")
    require(EARTH_TIF.exists(), "the Copernicus Nevada AOI is absent; re-fetch with "
                                "scripts/fetch_real_dems.py")
    from harness import Skip
    try:
        import rasterio                                          # noqa: F401
    except Exception as exc:
        raise Skip(f"rasterio is not installed in this interpreter: {exc}") from exc

    for support in (500.0, 750.0, 1000.0):
        n = cg.plan(F, support)
        _, m = cg.read_exact(str(MOON_TIF), MOON_LONLAT[1], MOON_LONLAT[0], "moon", support, n)
        e_lon, e_lat = EARTH_LONLAT
        _, e = cg.read_exact(str(EARTH_TIF), e_lat, e_lon, "earth", support, n,
                             source_posting_m=30.0)
        cg.assert_comparable({"LUNAR_Site01": m, "earth_nevada_basin": e}, label=f"{support:.0f} m")
        assert m["support_m_achieved"] == e["support_m_achieved"] == [support, support]
        assert m["footprint_m"] == e["footprint_m"] == [F, F]
        assert m["cells"] == e["cells"] == [n, n]
        # the achieved support must equal the requested one, not merely be close to it
        assert m["support_m_requested"] == m["support_m_achieved"][0]
        assert e["support_m_requested"] == e["support_m_achieved"][0]


def test_a_geographic_source_must_declare_its_metric_posting():
    """Silently reading a degree posting as metres would switch the resolution floor off."""
    require(EARTH_TIF.exists(), "the Copernicus Nevada AOI is absent")
    try:
        import rasterio                                          # noqa: F401
    except Exception as exc:
        from harness import Skip
        raise Skip(f"rasterio is not installed in this interpreter: {exc}") from exc
    try:
        cg.read_exact(str(EARTH_TIF), EARTH_LONLAT[1], EARTH_LONLAT[0], "earth", 500.0, 18)
    except cg.ComparabilityError as exc:
        assert "source_posting_m" in str(exc), exc
    else:
        raise AssertionError("a geographic source was accepted without a metric posting")


# ------------------------------------------------------------------ synthetic coverage (gated)

def _write_synthetic(path, nodata_east_half=False):
    """A 1-degree tile of constant elevation at 2 arc-second (60 m) cells.

    The tile covers lon [-116, -115] and lat [36, 37], so the sampled window centred on
    (-115.5, 36.5) sits inside it — a fixture that misses the window returns all-nodata and looks
    like a broken grid rather than a broken test.
    """
    rasterio = _rasterio()
    from rasterio.transform import from_origin
    n = 1800
    arr = np.full((n, n), 100.0, dtype="float32")
    if nodata_east_half:
        arr[:, n // 2:] = -9999.0
    with rasterio.open(path, "w", driver="GTiff", height=n, width=n, count=1,
                       dtype="float32", crs="EPSG:4326",
                       transform=from_origin(-116.0, 37.0, 2.0 / 3600, 2.0 / 3600),
                       nodata=-9999.0) as ds:
        ds.write(arr, 1)


SYNTH_POSTING_M = 60.0
SYNTH_CENTRE = (36.5, -115.5)


def test_fully_covered_source_reports_full_validity():
    try:
        import rasterio                                          # noqa: F401
    except Exception as exc:
        from harness import Skip
        raise Skip(f"rasterio is not installed in this interpreter: {exc}") from exc
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "flat.tif"
        _write_synthetic(p)
        lat, lon = SYNTH_CENTRE
        _, rec = cg.read_exact(str(p), lat, lon, "earth", 500.0, 18,
                               source_posting_m=SYNTH_POSTING_M)
        assert rec["cells"] == [18, 18]
        assert rec["valid_fraction"] == 1.0, rec["valid_fraction"]
        assert rec["n_empty_cells"] == 0


def test_a_half_nodata_source_cannot_quietly_look_fully_valid():
    """Nodata must change the recorded valid fraction, not vanish into the average."""
    try:
        import rasterio                                          # noqa: F401
    except Exception as exc:
        from harness import Skip
        raise Skip(f"rasterio is not installed in this interpreter: {exc}") from exc
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "half.tif"
        _write_synthetic(p, nodata_east_half=True)
        lat, lon = SYNTH_CENTRE
        _, rec = cg.read_exact(str(p), lat, lon, "earth", 500.0, 18,
                               source_posting_m=SYNTH_POSTING_M)
        # the window straddles the boundary, so roughly half the cells carry data
        assert 0.2 < rec["valid_fraction"] < 0.8, (
            f"a half-nodata source reported valid_fraction {rec['valid_fraction']}; nodata is "
            f"being absorbed instead of recorded")
        assert rec["n_empty_cells"] > 0
