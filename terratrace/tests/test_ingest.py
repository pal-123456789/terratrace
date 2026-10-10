"""Ingest helpers that are testable without rasterio or the network.

The real fetch/read paths need rasterio + outbound HTTP (run on a networked
machine). What we CAN pin here is the byte-level guard that stops an ArcGIS
error-JSON (served as HTTP 200) from being mistaken for a GeoTIFF.
"""
import contextlib
import os
import tempfile

from terratrace import ingest


def _write(data):
    fd, path = tempfile.mkstemp(suffix=".tif")
    os.close(fd)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def test_is_tiff_accepts_both_endian_magics():
    le = _write(b"II*\x00rest-of-a-little-endian-tiff")
    be = _write(b"MM\x00*rest-of-a-big-endian-tiff")
    try:
        assert ingest._is_tiff(le) is True
        assert ingest._is_tiff(be) is True
    finally:
        os.remove(le)
        os.remove(be)


def test_is_tiff_rejects_error_json():
    # This is exactly what the 3DEP ImageServer sends on a bad request (HTTP 200).
    bad = _write(b'{"error":{"code":400,"message":"Unable to complete operation"}}')
    try:
        assert ingest._is_tiff(bad) is False
    finally:
        os.remove(bad)


# --- Retry/backoff tests for _stream (no real network) -----------------------

class _FakeResp:
    """Minimal requests-like response supporting the context-manager protocol."""

    def __init__(self, status_code, body=b"", headers=None, text=None):
        self.status_code = status_code
        self.headers = dict(headers or {})
        self._body = body
        if text is not None:
            self.text = text
        else:
            try:
                self.text = body.decode("utf-8", "replace")
            except Exception:
                self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, chunk_size=1):
        yield self._body


class _FakeSession:
    """Returns scripted _FakeResp objects (or raises scripted exceptions)."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    def get(self, url, params=None, stream=False, timeout=None):
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item()
        return item


@contextlib.contextmanager
def _recording_sleep():
    """Patch ingest.time.sleep to record durations; restore it afterwards."""
    sleeps = []
    original = ingest.time.sleep
    ingest.time.sleep = lambda s: sleeps.append(s)
    try:
        yield sleeps
    finally:
        ingest.time.sleep = original


def _tmp_out():
    d = tempfile.mkdtemp()
    return d, os.path.join(d, "dem.tif")


def _cleanup(d, out):
    for p in (out, out + ".part"):
        if os.path.exists(p):
            os.remove(p)
    if os.path.isdir(d):
        os.rmdir(d)


def test_stream_retries_transient_then_succeeds():
    sess = _FakeSession([
        _FakeResp(503, text="busy"),
        _FakeResp(503, text="busy"),
        _FakeResp(200, body=b"II*\x00ok"),
    ])
    d, out = _tmp_out()
    try:
        with _recording_sleep() as sleeps:
            res = ingest._stream("http://x", None, out, retries=4,
                                 backoff=0.01, max_sleep=0.05, session=sess)
        assert res == out
        with open(out, "rb") as fh:
            assert fh.read() == b"II*\x00ok"
        assert sess.calls == 3
        assert len(sleeps) == 2
    finally:
        _cleanup(d, out)


def test_stream_permanent_404_fails_fast():
    sess = _FakeSession([_FakeResp(404, text="Bad bbox")])
    d, out = _tmp_out()
    try:
        raised = None
        with _recording_sleep() as sleeps:
            try:
                ingest._stream("http://x", None, out, retries=4,
                               backoff=0.01, session=sess)
            except RuntimeError as exc:
                raised = exc
        assert raised is not None
        assert "404" in str(raised)
        assert sess.calls == 1
        assert sleeps == []
        assert not os.path.exists(out)
        assert not os.path.exists(out + ".part")
    finally:
        _cleanup(d, out)


def test_stream_honors_retry_after():
    sess = _FakeSession([
        _FakeResp(429, headers={"Retry-After": "7"}, text="rate limited"),
        _FakeResp(200, body=b"MM\x00*ok"),
    ])
    d, out = _tmp_out()
    try:
        with _recording_sleep() as sleeps:
            res = ingest._stream("http://x", None, out, retries=4,
                                 backoff=0.01, max_sleep=1000.0, session=sess)
        assert res == out
        with open(out, "rb") as fh:
            assert fh.read() == b"MM\x00*ok"
        assert sess.calls == 2
        assert len(sleeps) == 1
        assert sleeps[0] == 7
    finally:
        _cleanup(d, out)


def test_stream_exhausts_retries():
    sess = _FakeSession([_FakeResp(503, text="busy") for _ in range(5)])
    d, out = _tmp_out()
    try:
        raised = None
        with _recording_sleep() as sleeps:
            try:
                ingest._stream("http://x", None, out, retries=4,
                               backoff=0.01, max_sleep=0.05, session=sess)
            except RuntimeError as exc:
                raised = exc
        assert raised is not None
        assert sess.calls == 5
        assert len(sleeps) == 4
        assert not os.path.exists(out)
        assert not os.path.exists(out + ".part")
    finally:
        _cleanup(d, out)


def test_stream_retries_transport_error_then_succeeds():
    sess = _FakeSession([
        ingest._ReqConnErr("boom"),
        _FakeResp(200, body=b"II*\x00ok"),
    ])
    d, out = _tmp_out()
    try:
        with _recording_sleep() as sleeps:
            res = ingest._stream("http://x", None, out, retries=4,
                                 backoff=0.01, max_sleep=0.05, session=sess)
        assert res == out
        with open(out, "rb") as fh:
            assert fh.read() == b"II*\x00ok"
        assert sess.calls == 2
        assert len(sleeps) == 1
    finally:
        _cleanup(d, out)
