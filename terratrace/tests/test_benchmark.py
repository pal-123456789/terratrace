"""Reproducibility + performance benchmark harness fixtures.

Fast by construction: every call uses tiny grid sizes (16-32) so the pinned
invariant battery, hash-stability check and scaling profile all finish in a
couple of seconds. We assert structural facts (counts, keys, state names,
monotonic cell counts) and never an absolute wall-clock time, which is
host-dependent.
"""
from terratrace import benchmark

_SCENARIO_NAMES = {"clear_winner", "water_blocked", "synthetic_study", "hash_stability"}

_CACHE = {}


def _report():
    """Run the benchmark once at tiny sizes and reuse it across assertions."""
    if "report" not in _CACHE:
        _CACHE["report"] = benchmark.run_benchmark(sizes=(16, 24), repeats=1)
    return _CACHE["report"]


def test_run_benchmark_passes_cleanly():
    r = _report()
    assert r["all_passed"] is True, r
    assert r["passed"] == 4, r["passed"]
    assert r["failed"] == 0, r["failed"]
    assert len(r["scenarios"]) == 4, len(r["scenarios"])
    assert isinstance(r["package_hash"], str) and r["package_hash"], r["package_hash"]


def test_scenarios_have_expected_names_keys_and_pass():
    scenarios = _report()["scenarios"]
    names = {s["name"] for s in scenarios}
    assert names == _SCENARIO_NAMES, names
    for s in scenarios:
        for key in ("name", "passed", "detail"):
            assert key in s, (key, s)
        assert s["passed"] is True, s


def test_scaling_has_one_row_per_size():
    scaling = _report()["scaling"]
    assert len(scaling) == 2, scaling
    for row in scaling:
        assert row["cells"] == row["size"] * row["size"], row
        assert isinstance(row["seconds"], (int, float)) and row["seconds"] >= 0, row
        assert isinstance(row["state"], str) and row["state"], row


def test_package_hash_is_deterministic():
    a = benchmark.run_benchmark(sizes=(16, 24), repeats=1)["package_hash"]
    b = benchmark.run_benchmark(sizes=(16, 24), repeats=1)["package_hash"]
    assert a == b, (a, b)


def test_scaling_profile_cells_strictly_increase():
    rows = benchmark.scaling_profile(sizes=(16, 24, 32))
    cells = [r["cells"] for r in rows]
    assert cells == [256, 576, 1024], cells
    assert all(x < y for x, y in zip(cells, cells[1:])), cells
    for r in rows:
        assert isinstance(r["seconds"], (int, float)), r
