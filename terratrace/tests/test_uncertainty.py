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
    # distance CI exists for the 3 distributional axes, ordered lo<=med<=hi
    ci = out["units"]["close"]["distance_ci"]
    assert set(ci) == {"slope", "relief", "ruggedness"}
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


# --- spatial block bootstrap (honest, autocorrelation-respecting) -----------

def _ac_field(n=40, amp=40.0, sigma=9.0, noise=0.5, seed=0):
    """A spatially autocorrelated field: a smooth hill plus a little noise."""
    from terratrace import synthetic
    return synthetic.gaussian_hill((n, n), amplitude=amp, sigma=sigma) + \
        synthetic.rough_field((n, n), amplitude=noise, seed=seed)


def test_block_resample_2d_properties():
    rng = np.random.default_rng(1)
    f = np.arange(64.0).reshape(8, 8)
    r = uncertainty.block_resample_2d(f, 4, rng)
    assert r.shape == f.shape
    assert set(np.unique(r)).issubset(set(np.unique(f)))      # only real source values
    const = np.full((8, 8), 5.0)
    assert np.all(uncertainty.block_resample_2d(const, 3, rng) == 5.0)
    # deterministic for a given rng seed
    a = uncertainty.block_resample_2d(f, 4, np.random.default_rng(2))
    b = uncertainty.block_resample_2d(f, 4, np.random.default_rng(2))
    assert np.array_equal(a, b)
    # block larger than the grid is clamped, not an error
    assert uncertainty.block_resample_2d(f, 99, np.random.default_rng(3)).shape == f.shape


def _maps(z, L=10.0):
    from terratrace import features
    s = features.slope_deg(z, L, L)
    conn, _ = features.low_slope_connectivity(s, 15.0)
    return {"slope": s, "relief": features.relief(z, 5, 0.0),
            "ruggedness": features.ruggedness(z, 5, L, L), "connectivity_scalar": conn}


def test_block_bootstrap_closer_unit_and_report_shape():
    ref = _maps(_ac_field(seed=1))
    near = _maps(_ac_field(noise=0.6, seed=2))
    far = _maps((__import__("terratrace.synthetic", fromlist=["x"]).plane((40, 40), 0.2, dx=10.0))
                + __import__("terratrace.synthetic", fromlist=["x"]).rough_field((40, 40), 3.0, seed=3))
    out = uncertainty.block_bootstrap_pareto(ref, {"near": near, "far": far},
                                             block=6, n_boot=120, seed=0)
    assert out["method"] == "block" and out["block"] == 6
    assert out["units"]["near"]["nondominated_freq"] >= out["units"]["far"]["nondominated_freq"]
    ci = out["units"]["near"]["distance_ci"]
    assert set(ci) == {"slope", "relief", "ruggedness"}
    assert 0.0 <= out["decisive_freq"] <= 1.0


def test_block_bootstrap_cis_wider_than_independent_on_autocorrelated_field():
    # The scientific point: on autocorrelated terrain, independent-pixel CIs are
    # optimistically narrow; the block bootstrap (block >= correlation length)
    # yields wider, more honest CIs.
    z_ref, z_cand = _ac_field(seed=1), _ac_field(noise=0.6, seed=2)
    m_ref, m_cand = _maps(z_ref), _maps(z_cand)
    f_ref = {k: (v.ravel() if hasattr(v, "ravel") else v) for k, v in m_ref.items()}
    f_cand = {k: (v.ravel() if hasattr(v, "ravel") else v) for k, v in m_cand.items()}
    ind = uncertainty.bootstrap_pareto(f_ref, {"c": f_cand}, n_boot=150, seed=0)
    blk = uncertainty.block_bootstrap_pareto(m_ref, {"c": m_cand}, block=6, n_boot=150, seed=0)

    def total_width(rep):
        ci = rep["units"]["c"]["distance_ci"]
        return sum(hi - lo for (lo, _med, hi) in ci.values())
    assert total_width(blk) > total_width(ind), (total_width(blk), total_width(ind))


def test_compare_units_block_bootstrap_wires_through():
    from terratrace import study, synthetic
    L, n = 10.0, 40
    hill = synthetic.gaussian_hill((n, n), amplitude=40, sigma=9, dx=L, dy=L)
    raw = {"ref": hill + synthetic.rough_field((n, n), 0.5, seed=1),
           "near": hill + synthetic.rough_field((n, n), 0.6, seed=2)}
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, L, reference_id="ref", target_support_m=L,
                              n_boot=60, bootstrap_method="block", block_size=6)
    assert pkg["bootstrap"]["method"] == "block" and pkg["bootstrap"]["block"] == 6
