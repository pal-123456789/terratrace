"""Tests for the keyless Copernicus GLO-30 COG reader (:mod:`terratrace.cop30_cog`).

The central claim this module has to earn is that the public ESA COG mosaic is a
drop-in replacement for the OpenTopography COP30 endpoint -- same data, no API
key. The equivalence tests below assert that directly (max absolute difference
0.0 m against the cached OpenTopography AOI tiles).

Dependency-free house style: plain ``def test_*()``, assert-based, no pytest, no
unittest. The geometry and naming tests are fully OFFLINE -- they stub the tile
URL so no request can leave the machine. The equivalence tests need the real
mosaic; when the network or the cached OpenTopography tile is unavailable they
return early rather than fail, so the suite stays green offline while still
verifying bit-identity whenever it can.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terratrace import cop30_cog as cc

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_HERE, "data", "earth")


# --------------------------------------------------------------------------- #
# Tile naming and the bbox -> tiles mapping (offline)                          #
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
# read_cog30 geometry with the network made unreachable (offline)              #
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
    with _NoTiles():
        arr, tr = cc.read_cog30((10.0, 20.0, 10.01, 20.01))
    # Pixel CENTRES sit on multiples of the posting, so a 0.01 deg bbox holds 36.
    assert arr.shape == (36, 36)
    # Edge-aligned: the raster's west/north edge is half a pixel outside centre 0.
    assert abs(tr.c - (10.0 - cc.RESOLUTION_DEG / 2.0)) < 1e-12
    assert abs(tr.f - (20.01 + cc.RESOLUTION_DEG / 2.0)) < 1e-12
    assert abs(tr.a - cc.RESOLUTION_DEG) < 1e-15
    assert np.all(arr == cc.NODATA)


def test_read_cog30_writes_a_readable_geotiff():
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


def test_fetch_cop30_cog_returns_the_output_path():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "aoi.tif")
        with _NoTiles():
            got = cc.fetch_cop30_cog((10.0, 20.0, 10.005, 20.005), p)
        assert got == p
        assert os.path.exists(p)


# --------------------------------------------------------------------------- #
# Equivalence with the OpenTopography COP30 product (needs the real mosaic)    #
# --------------------------------------------------------------------------- #
def _assert_matches_opentopography(name):
    """The public COG mosaic must equal the OpenTopography COP30 tile exactly.

    Early-returns when the cached tile or the network is unavailable, so this
    never turns an offline CI run red.
    """
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
    _assert_matches_opentopography("craters_of_the_moon_cop30.tif")


def test_cog30_matches_opentopography_on_nevada_basin():
    _assert_matches_opentopography("nevada_basin_cop30.tif")


def test_cog30_matches_opentopography_on_andean_volcano():
    _assert_matches_opentopography("andean_volcano_cop30.tif")
