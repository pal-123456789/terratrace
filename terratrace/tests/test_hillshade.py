"""Tests for the pure-stdlib hillshade / PNG data-URI visualisation module.

No PIL or other image library is used: PNG validity is proven by parsing the
chunk structure and zlib-decompressing the IDAT stream directly.
"""
import base64
import struct
import zlib

import numpy as np

from terratrace import hillshade, synthetic


def _iter_chunks(data):
    """Yield (tag, payload) for each PNG chunk after the 8-byte signature."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    i = 8
    while i < len(data):
        (length,) = struct.unpack(">I", data[i:i + 4])
        tag = data[i + 4:i + 8]
        payload = data[i + 8:i + 8 + length]
        yield tag, payload
        i += 12 + length  # length(4) + type(4) + data + crc(4)


def _idat(data):
    """Concatenated IDAT payload bytes of a PNG."""
    return b"".join(payload for tag, payload in _iter_chunks(data) if tag == b"IDAT")


def test_hillshade_dtype_shape_and_value_range():
    z = synthetic.gaussian_hill((64, 64), amplitude=20.0, sigma=10.0)
    gray = hillshade.hillshade(z)
    assert gray.dtype == np.uint8
    assert gray.shape == z.shape
    assert int(gray.min()) >= 0 and int(gray.max()) <= 255
    # A hill is illuminated unevenly -> a genuine range of grey values.
    assert int(gray.max()) > int(gray.min())


def test_flat_field_is_uniform():
    flat = synthetic.constant((32, 32), value=5.0)
    gray = hillshade.hillshade(flat)
    assert gray.shape == flat.shape
    # Zero slope everywhere -> every pixel shaded identically.
    assert int(gray.max()) - int(gray.min()) == 0


def test_nan_cells_render_black():
    z = synthetic.with_nodata_wedge(
        synthetic.gaussian_hill((48, 48), amplitude=15.0, sigma=8.0))
    gray = hillshade.hillshade(z)
    assert gray.dtype == np.uint8
    assert gray.shape == z.shape
    # The nodata wedge must contain black (0) pixels.
    assert int(gray.min()) == 0


def test_png_signature_and_ihdr_dimensions():
    gray = hillshade.hillshade(synthetic.gaussian_hill((40, 56), amplitude=10.0))
    data = hillshade.to_png_bytes(gray)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert width == gray.shape[1]
    assert height == gray.shape[0]


def test_png_idat_is_a_wellformed_stream():
    gray = hillshade.hillshade(synthetic.gaussian_hill((32, 48), amplitude=12.0))
    height, width = gray.shape
    data = hillshade.to_png_bytes(gray)
    raw = zlib.decompress(_idat(data))
    # One filter byte per scanline + width pixel bytes per row.
    assert len(raw) == height * (width + 1)
    # And every filter byte is 0x00 (the filter type we wrote).
    assert all(raw[r * (width + 1)] == 0 for r in range(height))


def test_data_uri_prefix_and_payload_is_png():
    gray = hillshade.hillshade(synthetic.gaussian_hill((32, 32), amplitude=9.0))
    uri = hillshade.to_data_uri(gray)
    assert uri.startswith("data:image/png;base64,")
    payload = base64.b64decode(uri[len("data:image/png;base64,"):])
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload == hillshade.to_png_bytes(gray)


def test_png_bytes_are_deterministic():
    z = synthetic.gaussian_hill((48, 48), amplitude=14.0, sigma=7.0)
    gray = hillshade.hillshade(z)
    a = hillshade.to_png_bytes(gray)
    b = hillshade.to_png_bytes(gray)
    assert a == b
    # The full pipeline is deterministic too.
    assert hillshade.hillshade_data_uri(z) == hillshade.hillshade_data_uri(z)


def test_hillshade_data_uri_downsamples_below_max_size():
    z = synthetic.gaussian_hill((300, 220), amplitude=25.0, sigma=40.0)
    uri = hillshade.hillshade_data_uri(z, max_size=64)
    assert uri.startswith("data:image/png;base64,")
    data = base64.b64decode(uri[len("data:image/png;base64,"):])
    width, height = struct.unpack(">II", data[16:24])
    assert max(width, height) <= 64
    # Striding by step = ceil(300/64) = 5 -> ceil(300/5)=60 rows, ceil(220/5)=44 cols.
    step = int(np.ceil(300 / 64.0))
    assert (height, width) == z[::step, ::step].shape
    # The downsampled stream is still a valid PNG.
    assert len(zlib.decompress(_idat(data))) == height * (width + 1)


def test_hillshade_data_uri_small_input_not_upsampled():
    z = synthetic.gaussian_hill((40, 40), amplitude=12.0, sigma=8.0)
    uri = hillshade.hillshade_data_uri(z, max_size=256)
    data = base64.b64decode(uri[len("data:image/png;base64,"):])
    width, height = struct.unpack(">II", data[16:24])
    assert (height, width) == z.shape  # already small -> no striding
