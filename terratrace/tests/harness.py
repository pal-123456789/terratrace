"""Test-harness conventions: a test that cannot run must SAY SO.

The dependency-free runner prints PASS or FAIL per test. That is not enough for a project with
optional geospatial dependencies and real datasets, because a test which quietly `return`s when
rasterio or a 40 MB product is absent also prints PASS — and a reader then cannot tell a verified
claim from an unexercised one. An external review asked for the distinction explicitly, and it is a
fair ask: "891 tests passing" must not be read as "891 things were verified".

So a test that cannot exercise what it claims raises ``Skip`` with a reason. The runner reports it
as SKIP, lists the reason, and counts it separately from both passes and failures. A skip is not a
pass and not a failure — it is a statement that this environment could not check the thing.

Usage:

    from harness import require, Skip
    require(tif.exists(), "the 41 MB LOLA product is not present; re-fetch with scripts/fetch_lola.py")
"""
from __future__ import annotations


class Skip(Exception):
    """This environment cannot exercise the test. Not a failure, and not a pass."""


def require(condition, reason):
    """Raise ``Skip`` unless ``condition`` holds, carrying the reason a reader needs."""
    if not condition:
        raise Skip(reason)


def optional_import(module, reason):
    """Import an optional dependency, or skip with a reason naming it."""
    try:
        return __import__(module)
    except Exception as exc:
        raise Skip(f"{reason} ({module} unavailable: {type(exc).__name__})") from exc
