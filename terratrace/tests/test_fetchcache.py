"""Fetch-cache + manifest fixtures (dependency-free, assert-based)."""
import hashlib
import os
import tempfile

from terratrace import fetchcache


def _write(data, dirpath=None):
    """Write bytes to a fresh temp file; return its path (caller cleans up)."""
    fd, path = tempfile.mkstemp(dir=dirpath)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path


def test_sha256_matches_hashlib():
    data = b"terratrace fetch cache test \x00\x01\x02"
    path = _write(data)
    try:
        assert fetchcache.sha256_file(path) == hashlib.sha256(data).hexdigest()
    finally:
        os.unlink(path)


def test_file_ok_true_false_cases():
    path = _write(b"not empty")
    try:
        assert fetchcache.file_ok(path) is True
    finally:
        os.unlink(path)
    assert fetchcache.file_ok("does/not/exist.tif") is False
    empty = _write(b"")
    try:
        assert fetchcache.file_ok(empty) is False  # 0 bytes < min_bytes=1
    finally:
        os.unlink(empty)


def test_needs_fetch_missing():
    need, reason = fetchcache.needs_fetch("does/not/exist.tif")
    assert need is True and reason == "missing or empty"


def test_needs_fetch_present_no_expected_hash():
    path = _write(b"II*\x00present")
    try:
        need, reason = fetchcache.needs_fetch(path)
        assert need is False and reason == "cached"
    finally:
        os.unlink(path)


def test_needs_fetch_wrong_checksum():
    path = _write(b"II*\x00present")
    try:
        need, reason = fetchcache.needs_fetch(path, expected_sha256="deadbeef")
        assert need is True and reason == "checksum mismatch"
    finally:
        os.unlink(path)


def test_needs_fetch_correct_checksum_case_insensitive():
    data = b"II*\x00present"
    path = _write(data)
    try:
        good = hashlib.sha256(data).hexdigest()
        need, reason = fetchcache.needs_fetch(path, expected_sha256=good)
        assert need is False and reason == "cached"
        # Comparison must be case-insensitive.
        need_u, reason_u = fetchcache.needs_fetch(path, expected_sha256=good.upper())
        assert need_u is False and reason_u == "cached"
    finally:
        os.unlink(path)


def test_record_entry_existing_file():
    data = b"a real-ish DEM payload" * 10
    path = _write(data)
    try:
        unit = {"id": "mars_a", "path": path, "body": "mars",
                "bbox": [10.0, 20.0, 11.0, 21.0]}
        e = fetchcache.record_entry(unit, source_id="mola_src")
        assert e["id"] == "mars_a"
        assert e["exists"] is True
        assert e["bytes"] == len(data) == os.path.getsize(path)
        assert e["sha256"] == fetchcache.sha256_file(path)
        assert e["bbox"] == [10.0, 20.0, 11.0, 21.0]
        assert e["source_id"] == "mola_src"
        assert e["body"] == "mars"
        assert isinstance(e["fetched_at"], str) and e["fetched_at"]
        assert e["fetched_at"].endswith("Z") or "+00:00" in e["fetched_at"]
    finally:
        os.unlink(path)


def test_record_entry_missing_path():
    unit = {"id": "earth_b", "path": "nope/missing.tif", "body": "earth",
            "bbox": [0, 0, 1, 1]}
    e = fetchcache.record_entry(unit)
    assert e["exists"] is False
    assert e["sha256"] is None
    assert e["bytes"] is None
    assert e["path"] == "nope/missing.tif"


def test_load_manifest_missing_returns_empty_shape():
    d = tempfile.mkdtemp()
    try:
        m = fetchcache.load_manifest(os.path.join(d, "no_manifest.json"))
        assert m == {"entries": {}, "updated_at": None}
    finally:
        os.rmdir(d)


def test_save_then_load_roundtrips_equal():
    d = tempfile.mkdtemp()
    mpath = os.path.join(d, "nested", "fetch_manifest.json")
    try:
        manifest = {"entries": {}, "updated_at": None}
        entry = {"id": "u1", "path": "/data/u1.tif", "source_id": "s1",
                 "body": "mars", "bbox": [1, 2, 3, 4], "exists": True,
                 "sha256": "abc123", "bytes": 42, "fetched_at": "2026-10-10T12:00:00Z"}
        manifest = fetchcache.update_manifest(manifest, entry)
        returned = fetchcache.save_manifest(mpath, manifest)
        assert returned == mpath and os.path.isfile(mpath)
        loaded = fetchcache.load_manifest(mpath)
        assert loaded == manifest
    finally:
        if os.path.isfile(mpath):
            os.unlink(mpath)
        os.rmdir(os.path.dirname(mpath))
        os.rmdir(d)


def test_update_manifest_insert_replace_preserve():
    manifest = {"entries": {}, "updated_at": None}
    e_a = {"id": "a", "sha256": "aaa", "bytes": 1}
    e_b = {"id": "b", "sha256": "bbb", "bytes": 2}
    manifest = fetchcache.update_manifest(manifest, e_a)
    manifest = fetchcache.update_manifest(manifest, e_b)
    assert set(manifest["entries"]) == {"a", "b"}
    assert manifest["updated_at"]  # refreshed to a non-empty timestamp

    # Replace "a", leave "b" untouched.
    e_a2 = {"id": "a", "sha256": "zzz", "bytes": 99}
    manifest = fetchcache.update_manifest(manifest, e_a2)
    assert set(manifest["entries"]) == {"a", "b"}
    assert manifest["entries"]["a"]["sha256"] == "zzz"
    assert manifest["entries"]["a"]["bytes"] == 99
    assert manifest["entries"]["b"] == e_b  # third/other entry preserved


def test_update_manifest_creates_entries_key_when_absent():
    manifest = {"updated_at": None}  # no "entries" key at all
    manifest = fetchcache.update_manifest(manifest, {"id": "x", "sha256": "x"})
    assert manifest["entries"]["x"]["sha256"] == "x"
