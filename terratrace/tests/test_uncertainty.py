"""Bootstrap-uncertainty fixtures."""
import numpy as np
from terratrace import uncertainty


def _feats(slope_mu, slope_sd, relief_mu, rug_mu, conn, seed):
    rng = np.random.default_rng(seed)
    return {
        "slope": rng.normal(slope_mu, slope_sd, 500),
        "relief": rng.normal(relief_mu, 2.0, 500),
        "ruggedness": rng.normal(rug_mu, 1.0, 500),
        "connectivity_scalar": conn,
    }


def test_closer_unit_has_higher_nondominated_frequency():
    ref = _feats(10, 2, 20, 5, 0.30, 1)
    close = _feats(10, 2, 20, 5, 0.30, 2)      # same distributions as ref
    far = _feats(26, 5, 40, 12, 0.08, 3)        # clearly different
    out = uncertainty.bootstrap_pareto(ref, {"close": close, "far": far}, n_boot=120, seed=0)
    uc = out["units"]["close"]["nondominated_freq"]
    uf = out["units"]["far"]["nondominated_freq"]
    assert uc > uf, (uc, uf)
    assert uc > 0.8, uc
    # distance CI exists for all four axes and is ordered lo<=med<=hi
    ci = out["units"]["close"]["distance_ci"]
    assert set(ci) == {"slope", "relief", "ruggedness", "connectivity"}
    for nm, (lo, med, hi) in ci.items():
        assert lo <= med <= hi, (nm, lo, med, hi)


def test_bootstrap_is_deterministic_with_seed():
    ref = _feats(10, 2, 20, 5, 0.30, 1)
    a = _feats(10, 2, 20, 5, 0.30, 2)
    b = _feats(18, 4, 30, 9, 0.15, 3)
    o1 = uncertainty.bootstrap_pareto(ref, {"a": a, "b": b}, n_boot=80, seed=7)
    o2 = uncertainty.bootstrap_pareto(ref, {"a": a, "b": b}, n_boot=80, seed=7)
    assert o1 == o2


def test_decisive_freq_in_range():
    ref = _feats(10, 2, 20, 5, 0.30, 1)
    a = _feats(10, 2, 20, 5, 0.30, 2)
    b = _feats(26, 5, 40, 12, 0.08, 3)
    out = uncertainty.bootstrap_pareto(ref, {"a": a, "b": b}, n_boot=100, seed=0)
    assert 0.0 <= out["decisive_freq"] <= 1.0


def test_extra_dims_can_flip_a_core_winner_into_a_tie():
    ref = _feats(10, 2, 20, 5, 0.30, 1)
    # 'b' dominates 'a' on the 4 core axes...
    a = _feats(20, 4, 34, 10, 0.14, 2)
    b = _feats(10, 2, 20, 5, 0.30, 3)
    core = uncertainty.bootstrap_pareto(ref, {"a": a, "b": b}, n_boot=120, seed=0)
    assert core["units"]["b"]["nondominated_freq"] > core["units"]["a"]["nondominated_freq"]
    # ...but a strong extra dimension favouring 'a' makes neither dominate -> both non-dominated
    extra = {"a": (0.0,), "b": (5.0,)}
    ext = uncertainty.bootstrap_pareto(ref, {"a": a, "b": b}, n_boot=120, seed=0, extra_dims=extra)
    assert ext["units"]["a"]["nondominated_freq"] == 1.0
    assert ext["units"]["b"]["nondominated_freq"] == 1.0
