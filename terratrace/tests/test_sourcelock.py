"""Source-lock pure-helper fixtures."""
import hashlib
import os
import tempfile

from terratrace import sourcelock


def test_sha256_matches_hashlib():
    data = b"terratrace source lock test"
    with tempfile.NamedTemporaryFile(delete=False) as fh:
        fh.write(data)
        path = fh.name
    try:
        assert sourcelock.sha256_file(path) == hashlib.sha256(data).hexdigest()
    finally:
        os.unlink(path)


def test_citation_and_terms():
    assert "MOLA" in sourcelock.citation_for("mars")
    assert "Copernicus" in sourcelock.citation_for("earth")
    assert "attribution" in sourcelock.terms_for("earth").lower()
    for bad in ("moon", "venus"):
        for fn in (sourcelock.citation_for, sourcelock.terms_for):
            try:
                fn(bad)
                raised = False
            except ValueError:
                raised = True
            assert raised


def test_build_entry_missing_file():
    unit = {"id": "u1", "path": "does/not/exist.tif", "body": "mars",
            "native_posting_m": 463.0, "rights_status": "verified_allowed"}
    e = sourcelock.build_entry(unit)
    assert e["exists"] is False
    assert e["sha256"] is None and e["bytes"] is None
    assert "MOLA" in e["citation"]
