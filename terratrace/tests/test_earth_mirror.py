"""The Earth DEM from a second mirror: the claim, and the accident that almost became one.

Microsoft Planetary Computer (a NASA Space Apps Global Offer) hosts the same ESA Copernicus GLO-30
product TerraTrace reads from AWS, behind a public STAC API needing no account. The cross-check in
``scripts/verify_earth_mirror.py`` reads the same tile from both and compares the numbers.

It found something worth pinning. Every one of the tile's 12,960,000 elevation values is identical,
but the two *files* are not byte-identical — they differ by 360 bytes of container metadata. A weaker
check would have reported "the mirrors disagree" (it did, on the first run, because it compared
Content-Length) or a lazier one would have compared only filenames. Both are wrong, in opposite
directions, and these tests hold the line between them.

Everything here runs offline: the heavy comparison is gated on the recorded artifact, and the
decision rule is exercised directly as a pure function.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "artifacts" / "mirror_check" / "earth_cop30_mirror.json"


def _load():
    spec = importlib.util.spec_from_file_location(
        "verify_earth_mirror", ROOT / "scripts" / "verify_earth_mirror.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- the decision rule

def test_differing_values_are_a_failure():
    """The one thing that IS a disagreement: the elevations themselves differ."""
    m = _load()
    code, msg = m.verdict({"identical_every_value": False, "equal_file_content_length": True,
                           "max_abs_diff_m": 3.0, "file_size_delta_bytes": 0})
    assert code == 1, msg
    assert "DISAGREEMENT" in msg


def test_differing_file_sizes_are_reported_not_treated_as_a_data_disagreement():
    """The subtle case. Different containers, same elevations — it must pass, and must say so.

    This is the exact situation the real tile is in. Calling it a disagreement would be a false
    alarm; staying silent about it would let someone claim the files are byte-identical.
    """
    m = _load()
    code, msg = m.verdict({"identical_every_value": True, "equal_file_content_length": False,
                           "max_abs_diff_m": 0.0, "file_size_delta_bytes": -360})
    assert code == 0, f"a container-metadata difference must not fail the check: {msg}"
    assert "not byte-identical" in msg, "the container difference must be stated, not swallowed"
    assert "-360" in msg, "the size delta must be reported as a number"


def test_a_fully_identical_pair_reports_byte_identity():
    """And when nothing differs, the stronger claim is available and is made."""
    m = _load()
    code, msg = m.verdict({"identical_every_value": True, "equal_file_content_length": True,
                           "max_abs_diff_m": 0.0, "file_size_delta_bytes": 0})
    assert code == 0
    assert "byte-identical" in msg


def test_a_blocked_check_is_never_reported_as_agreement():
    """A network failure is not evidence of a match, and must not exit 0.

    The failure this prevents is the tempting one: catch the exception, print nothing, pass. A check
    that turns "could not look" into "looked and agreed" is worse than no check at all.
    """
    m = _load()

    def _boom(*a, **k):
        raise m.Blocked("simulated network failure")

    m.compare = _boom
    assert m.main([]) == 2, "a blocked check must exit non-zero and must not claim agreement"


# --------------------------------------------------------------------------- the record

def test_the_recorded_mirror_check_covers_the_whole_tile():
    """The claim recorded is about the full raster, not a window — a window is 4% of the tile."""
    assert ARTIFACT.exists(), (
        "artifacts/mirror_check/earth_cop30_mirror.json is committed (git add -f: the artifacts/ "
        "tree is ignored, and a small record backing a published claim is force-added on purpose). "
        "This used to return silently when absent, so the published cross-check had no test at all "
        "on a fresh clone — which is exactly what CI is."
    )
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["values_compared"] == 3600 * 3600, (
        f"the record covers {data['values_compared']} values, not the whole 3600x3600 tile"
    )
    assert "whole tile" in data["extent_compared"], data["extent_compared"]
    assert data["agreement"]["identical_every_value"] is True
    assert data["agreement"]["equal_values_sha256"] is True
    assert data["aws"]["values_sha256"] == data["azure"]["values_sha256"]


def test_the_record_names_the_real_tile_and_the_real_mirror():
    """The tile must be the one the engine itself would fetch, and the mirror must be named."""
    assert ARTIFACT.exists(), (
        "artifacts/mirror_check/earth_cop30_mirror.json is committed (git add -f: the artifacts/ "
        "tree is ignored, and a small record backing a published claim is force-added on purpose). "
        "This used to return silently when absent, so the published cross-check had no test at all "
        "on a fresh clone — which is exactly what CI is."
    )
    from terratrace import cop30_cog
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    want = cop30_cog.tile_name(36, -116)
    assert data["tile"] == want, f"record names {data['tile']}, engine would fetch {want}"
    assert data["aws"]["url"] == cop30_cog.tile_url(36, -116), (
        "the AWS side of the comparison is not the URL the engine actually reads"
    )
    assert "blob.core.windows.net" in data["azure"]["url"], "the second mirror is not identified"
    assert "planetarycomputer.microsoft.com" in data["azure"]["indexed_by"]
    assert "sas/v1/token" in data["azure"]["access"] or "SAS" in data["azure"]["access"].upper()


def test_the_record_does_not_overclaim_the_mirror():
    """The mirror is a copy of the same product, not an independent source, and the record says so.

    A second host for one dataset is a provenance fact. Dressing it as independent corroboration
    would be the same error the project already withdrew a Mars claim over.
    """
    assert ARTIFACT.exists(), (
        "artifacts/mirror_check/earth_cop30_mirror.json is committed (git add -f: the artifacts/ "
        "tree is ignored, and a small record backing a published claim is force-added on purpose). "
        "This used to return silently when absent, so the published cross-check had no test at all "
        "on a fresh clone — which is exactly what CI is."
    )
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    caveat = data["caveat"].lower()
    for phrase in ("not a validation of the dem's accuracy", "not an independent source"):
        assert phrase in caveat, f"the record dropped its {phrase!r} caveat"
    for banned in ("independent confirmation", "corroborat", "validates the dem"):
        assert banned not in caveat, f"the record overclaims the mirror: {banned!r}"
    # and the record must not claim the files are byte-identical
    assert data["agreement"]["equal_file_content_length"] is False, (
        "the record now says the containers match; if that is real, the 360-byte note is stale"
    )
    assert data["agreement"]["file_size_delta_bytes"] == -360, (
        "the recorded container difference changed; re-run the check and update the prose with it"
    )
