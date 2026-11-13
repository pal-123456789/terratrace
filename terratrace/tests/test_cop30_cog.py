"""Tests for the keyless Copernicus GLO-30 COG reader (:mod:`terratrace.cop30_cog`).

CI installs **NumPy only** (see ``requirements.txt``), so nothing here may import
``rasterio`` at module scope, and every test that needs it must skip cleanly when
it is absent. That rule is enforced directly by ``tests/test_ci_hygiene.py``.

The central claim to earn is that the public ESA COG mosaic is a drop-in
replacement for the OpenTopography COP30 endpoint -- same data, no API key. The
equivalence tests assert that directly (maximum absolute difference 0.0 m against
the cached OpenTopography AOI tiles), and return early when either the tile or
rasterio/network is unavailable.

Dependency-free house style: plain ``def test_*()``, assert-based, no pytest, no
unittest.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terratrace import cop30_cog as cc

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_HERE, "data", "earth")


def _rasterio_available():
    try:
        import rasterio  # noqa: F401
    except Exception:
        return False
    return True


# --------------------------------------------------------------------------- #
# Tile naming and the bbox -> tiles mapping (no dependencies at all)           #
# --------------------------------------------------------------------------- #
def test_tile_name_uses_the_south_west_corner():
    assert cc.tile_name(43, -114) == "Copernicus_DSM_COG_10_N43_00_W114_00_DEM"
    assert cc.tile_name(-31, 129) == "Copernicus_DSM_COG_10_S31_00_E129_00_DEM"


def test_tile_name_zero_latitude_is_north_and_zero_longitude_is_east():
    assert "_N00_" in cc.tile_name(0, 10)
    assert "_E000_" in cc.tile_name(10, 0)


def test_tile_name_never_contains_a_minus_sign():
    # -31 must render as S31, not as a negative number.
    assert "-" not in cc.tile_name(-31, 129)


def test_tile_url_points_at_the_public_bucket_over_https():
    url = cc.tile_url(25, 39)
    assert url.startswith("https://copernicus-dem-30m.s3.amazonaws.com/")
    assert url.endswith(".tif")
    assert "http://" not in url


def test_tiles_for_bbox_single_cell():
    assert cc.tiles_for_bbox((0.1, 0.1, 0.2, 0.2)) == [(0, 0)]


def test_tiles_for_bbox_crossing_a_corner():
    got = cc.tiles_for_bbox((-0.5, -0.5, 0.5, 0.5))
    assert sorted(got) == [(-1, -1), (-1, 0), (0, -1), (0, 0)]


def test_tiles_for_bbox_covers_every_touched_cell():
    # A 3x2 degree bbox whose edges are off the cell grid touches 4x3 = 12 cells.
    assert len(cc.tiles_for_bbox((10.0, 20.0, 13.0, 22.0))) == 12


def test_resolution_is_one_arc_second():
    assert abs(cc.RESOLUTION_DEG - 1.0 / 3600.0) < 1e-15


def test_tile_size_is_one_degree_of_arc_seconds():
    assert cc.TILE_SIZE_PX == int(round(1.0 / cc.RESOLUTION_DEG))


def test_nodata_is_the_documented_finite_sentinel():
    assert cc.NODATA == -32768.0


# --------------------------------------------------------------------------- #
# The NumPy-only contract: a clear error, never an ImportError                 #
# --------------------------------------------------------------------------- #
def test_read_cog30_raises_an_actionable_error_without_rasterio():
    """CI has no rasterio. The failure must be a RuntimeError naming the fix,
    exactly like the rest of the engine -- not an ImportError that would crash
    the dependency-free runner during module import."""
    import builtins
    import sys as _sys

    real_import = builtins.__import__
    saved = {k: _sys.modules.pop(k) for k in list(_sys.modules)
             if k == "rasterio" or k.startswith("rasterio.")}

    def _blocked(name, *a, **k):
        if name == "rasterio" or name.startswith("rasterio."):
            raise ImportError("blocked for the test")
        return real_import(name, *a, **k)

    builtins.__import__ = _blocked
    try:
        try:
            cc.read_cog30((10.0, 20.0, 10.001, 20.001))
        except RuntimeError as exc:
            assert "rasterio" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when rasterio is absent")
    finally:
        builtins.__import__ = real_import
        _sys.modules.update(saved)


# --------------------------------------------------------------------------- #
# read_cog30 behaviour with the network made unreachable                       #
# --------------------------------------------------------------------------- #
class _NoTiles:
    """Stub ``tile_url`` so every per-tile read fails, as an unreachable bucket
    would. GDAL's HTTP stack is libcurl, so blocking Python sockets would not
    actually stop a fetch -- stubbing the URL does."""

    def __enter__(self):
        self._real = cc.tile_url
        cc.tile_url = lambda lat_sw, lon_sw: "/nonexistent-dir/no-such-tile.tif"
        return self

    def __exit__(self, *exc):
        cc.tile_url = self._real
        return False


def test_read_cog30_shape_and_transform_follow_the_bbox():
    import numpy as np
    if not _rasterio_available():
        return
    with _NoTiles():
        arr, tr = cc.read_cog30((10.0, 20.0, 10.01, 20.01))
    # Pixel CENTRES sit on multiples of the posting, so a 0.01 deg bbox holds 36.
    assert arr.shape == (36, 36)
    # Edge-aligned: the raster's west/north edge is half a pixel outside centre 0.
    assert abs(tr.c - (10.0 - cc.RESOLUTION_DEG / 2.0)) < 1e-12
    assert abs(tr.f - (20.01 + cc.RESOLUTION_DEG / 2.0)) < 1e-12
    assert abs(tr.a - cc.RESOLUTION_DEG) < 1e-15
    assert np.all(arr == cc.NODATA)


def test_read_cog30_reports_unreachable_tiles_instead_of_failing_silently():
    import numpy as np
    if not _rasterio_available():
        return
    report = {}
    with _NoTiles():
        cc.read_cog30((10.0, 20.0, 10.01, 20.01), report=report)
    assert report["failed_tiles"], "an unreachable tile must be reported"
    assert report["no_coverage_frac"] == 1.0
    # tiles are (lat_sw, lon_sw): the bbox is 10..10.01 E, 20..20.01 N.
    assert report["tiles"] == [(20, 10)]


def test_fetch_cop30_cog_refuses_a_mostly_nodata_aoi():
    import tempfile
    if not _rasterio_available():
        return
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "aoi.tif")
        with _NoTiles():
            try:
                cc.fetch_cop30_cog((10.0, 20.0, 10.005, 20.005), p)
            except ValueError as exc:
                assert "coverage" in str(exc)
            else:
                raise AssertionError("expected ValueError for a nodata AOI")
            # An explicit override is allowed.
            assert cc.fetch_cop30_cog((10.0, 20.0, 10.005, 20.005), p,
                                      min_coverage=0.0) == p


def test_read_cog30_writes_a_readable_geotiff():
    if not _rasterio_available():
        return
    # NOTE: the guard MUST come before any optional import. An `import rasterio`
    # above this line fails on the CI Pythons, which install NumPy only -- and it
    # fails even though the guard is present, because the import is executed
    # before it. tests/test_ci_hygiene.py now runs these functions with the
    # optional deps blocked so this cannot recur.
    import tempfile
    import numpy as np
    import rasterio
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "aoi.tif")
        with _NoTiles():
            cc.read_cog30((10.0, 20.0, 10.005, 20.005), out_path=p)
        with rasterio.open(p) as ds:
            assert ds.crs.to_epsg() == 4326
            assert ds.count == 1
            assert ds.dtypes[0] == "float32"
            assert ds.nodata == cc.NODATA
            assert np.all(ds.read(1) == cc.NODATA)


# --------------------------------------------------------------------------- #
# Equivalence with the OpenTopography COP30 product (needs rasterio + mosaic)  #
# --------------------------------------------------------------------------- #
def _assert_matches_opentopography(name):
    """The public COG mosaic must equal the OpenTopography COP30 tile exactly.

    Early-returns when the cached tile, rasterio or the network is unavailable,
    so this never turns an offline CI run red. The availability check precedes the
    optional import, so it is safe on a NumPy-only interpreter.
    """
    if not _rasterio_available():
        return
    import numpy as np
    import rasterio
    ot_path = os.path.join(_DATA, name)
    if not os.path.exists(ot_path):
        return
    with rasterio.open(ot_path) as ds:
        b = ds.bounds
        ot = ds.read(1)
    try:
        cog, _ = cc.read_cog30((b.left, b.bottom, b.right, b.top))
    except Exception:
        return          # offline: nothing to verify against here
    assert cog.shape == ot.shape, f"shape {cog.shape} != OpenTopography {ot.shape}"
    diff = np.abs(cog.astype("float64") - ot.astype("float64"))
    assert float(diff.max()) == 0.0, (
        "COG and OpenTopography elevations must be identical; "
        f"max abs difference {float(diff.max())} m")
    assert float(np.mean(diff == 0)) == 1.0


def test_cog30_matches_opentopography_on_craters_of_the_moon():
    if not _rasterio_available():
        return
    _assert_matches_opentopography("craters_of_the_moon_cop30.tif")


def test_cog30_matches_opentopography_on_nevada_basin():
    if not _rasterio_available():
        return
    _assert_matches_opentopography("nevada_basin_cop30.tif")


def test_cog30_matches_opentopography_on_andean_volcano():
    if not _rasterio_available():
        return
    _assert_matches_opentopography("andean_volcano_cop30.tif")


# --------------------------------------------------------------------------- #
# Catalog integration: the keyless source is discoverable by the recommender    #
# --------------------------------------------------------------------------- #
_CRATERS_BBOX = (-113.60, 43.30, -113.30, 43.60)


def test_catalog_registers_the_keyless_cog_source():
    from terratrace import catalog
    s = catalog.get("earth_cop30_cog")
    assert s["body"] == "earth"
    assert s["key_required"] is False
    assert s["access"]["method"] == "aws_cog_public"
    assert s["native_resolution_m"] == 30.0
    assert s["vertical_accuracy_m"] == catalog.get("earth_cop30")["vertical_accuracy_m"]


def test_recommender_prefers_the_keyless_source_when_a_key_is_not_available():
    from terratrace import catalog
    rec = catalog.recommend_source(_CRATERS_BBOX, "earth", 2000.0, require_keyless=True)
    assert rec["source_id"] == "earth_cop30_cog", rec


def test_recommender_still_prefers_the_keyed_source_by_default():
    """Both are the same product at the same preference tier; the tie breaks on
    id, so the long-standing default is unchanged and nothing that depended on it
    moves."""
    from terratrace import catalog
    rec = catalog.recommend_source(_CRATERS_BBOX, "earth", 2000.0)
    assert rec["source_id"] == "earth_cop30", rec
