"""The lunar half: real LOLA terrain, and the claims made about it.

The engine has always been lunar-capable; what changed is that a real lunar product was ingested.
These tests protect the two things that can rot now that a number exists:

1. the *engine path* the demonstration relies on — body-aware geometry and aggregation down to a
   declared support, on a synthetic surface, with no data file and no rasterio (CI is NumPy-only);
2. the *published claims* — the exploratory result must stay labelled exploratory, the one frozen
   artifact's Pareto membership must be recomputable from its own stored numbers, and no page may
   quietly promote the result to confirmatory or to a base-suitability claim.

The heavy real-data assertion is gated on the 41 MB product being present, so a fresh clone runs
green and a machine holding the data additionally verifies the headline numbers against the raster.
"""
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARTIFACT = ROOT / "artifacts" / "lunar_site01" / "lunar_site01_exploratory.json"
MOON_TIF = ROOT / "data" / "moon" / "Site01_surf.tif"

AXES = ("mean_slope_deg", "mean_relief3_m", "elev_std_m")


# --------------------------------------------------------------------------- catalog

def test_lunar_pgda_product_is_catalogued_with_real_metadata():
    """The Goddard 5 m/px south-polar product is a first-class, described source."""
    from terratrace import catalog

    src = catalog.SOURCES["moon_lola_pgda_5mpp"]
    assert src["body"] == "moon"
    assert float(src["native_resolution_m"]) == 5.0
    assert "pgda.gsfc.nasa.gov" in src["access"]["endpoint"]
    assert src["coverage"]["complete"] is False, (
        "the product covers six south-polar regions, not the whole body; calling it complete "
        "would let a study treat it as globally available"
    )
    # and the registry must say so in words, not only in a boolean
    cov = catalog.source_covers("moon_lola_pgda_5mpp", (0.0, -89.0, 1.0, -88.0), "moon")
    assert cov["covered"] is True and cov["complete"] is False
    assert "whole planet" not in cov["reason"], cov["reason"]


def test_lunar_and_mars_sources_have_different_effective_floors():
    """Mars cannot enter the lunar regime: MOLA's floor is above every support used there.

    This is the reason the lunar panel excludes Mars, so it is asserted rather than asserted-in-prose.
    """
    from terratrace import catalog

    mars = catalog.SOURCES["mars_mola_usgs_463m"]
    lunar = catalog.SOURCES["moon_lola_pgda_5mpp"]
    mars_floor = 3.0 * float(mars["native_resolution_m"])
    lunar_floor = 3.0 * float(lunar["native_resolution_m"])
    assert mars_floor > 1000.0, f"Mars floor {mars_floor} m should exceed the lunar panel's supports"
    assert lunar_floor <= 500.0, f"Moon floor {lunar_floor} m should sit below them"


# --------------------------------------------------------------------------- engine path

def _synthetic_lunar_surface(n=96, dx=5.0, relief_m=400.0, seed=7):
    """A rough surface at lunar posting: not a 'Moon', just a stand-in with a known dynamic range."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0, 1.0, (n, n))
    # smooth it into landform-like structure, then rescale to the site's order of relief
    for _ in range(3):
        base = 0.25 * (np.roll(base, 1, 0) + np.roll(base, -1, 0)
                       + np.roll(base, 1, 1) + np.roll(base, -1, 1))
    base = (base - base.mean()) / (base.std() or 1.0)
    return base * (relief_m / 4.0), dx


def test_the_three_declared_axes_are_finite_and_ordered_by_roughness():
    """The axes the demonstration declares must respond monotonically to actual roughness."""
    from terratrace import features

    def axes(z, dx):
        slope = features.slope_deg(z, dx, dx)
        relief = features.relief(z, window=3, alpha=0.0)
        return (float(np.nanmean(slope)), float(np.nanmean(relief)),
                float(np.nanstd(z[np.isfinite(z)])))

    smooth, dx = _synthetic_lunar_surface(relief_m=20.0)
    rough, _ = _synthetic_lunar_surface(relief_m=400.0)
    s, r = axes(smooth, dx), axes(rough, dx)
    assert all(np.isfinite(v) for v in s + r), f"non-finite axis value: {s} {r}"
    for i, name in enumerate(AXES):
        assert r[i] > s[i], f"{name} did not increase with roughness: {s[i]} -> {r[i]}"


def test_aggregation_reaches_the_declared_supports_with_equal_footprints():
    """500-1000 m supports are reachable from 5 m posting, and equal cells mean equal ground."""
    from terratrace import support

    z, dx = _synthetic_lunar_surface(n=96)
    cells = {}
    for target in (500.0, 750.0, 1000.0):
        factor = max(int(round(target / dx)), 1)
        agg, rec = support.block_aggregate(z, factor, dx, aggregation="mean", min_valid=0.5)
        cells[target] = (agg.shape[0], float(rec.target_support_m))
        assert rec.target_support_m >= target, (
            f"support {target} m achieved only {rec.target_support_m} m"
        )
        assert agg.shape[0] < z.shape[0], "aggregation did not reduce the grid"
    assert all(np.isfinite(a[1]) for a in cells.values())


# --------------------------------------------------------------------------- the frozen artifact

def test_artifact_pareto_membership_is_recomputable_from_its_own_numbers():
    """The published layer-1 set must follow from the stored distances — not be asserted beside them."""
    if not ARTIFACT.exists():
        return
    from terratrace import decision

    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    for scale, block in data["scales"].items():
        dist = {k: v for k, v in block["axis_distance_fraction"].items()}
        assert dist, f"{scale}: no distances stored, membership cannot be checked"
        recomputed = sorted(decision.non_dominated(dist))
        assert recomputed == sorted(block["layer1"]), (
            f"{scale}: stored layer1 {sorted(block['layer1'])} != recomputed {recomputed}"
        )


def test_artifact_supports_a_single_non_dominated_candidate_at_every_support():
    """The result reported in the docs: exactly one Earth candidate survives, at every support."""
    if not ARTIFACT.exists():
        return
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert set(data["scales"]) == {"500m", "750m", "1000m"}
    for scale, block in data["scales"].items():
        assert block["layer1"] == ["earth_nevada_basin"], (
            f"{scale}: expected the one reported candidate, got {block['layer1']}"
        )
        assert block["lunar_is_the_reference"] is True
        assert all(np.isfinite(block["axes"]["LUNAR_Site01"][a]) for a in AXES)


def test_artifact_declares_itself_exploratory_and_excludes_mars():
    """The artifact must carry its own scope, so it cannot be cited as a confirmatory panel."""
    if not ARTIFACT.exists():
        return
    prov = json.loads(ARTIFACT.read_text(encoding="utf-8"))["provenance"]
    assert "EXPLORATORY" in prov["status"].upper()
    assert prov["supports_m"] == [500.0, 750.0, 1000.0]
    assert prov["extent_m"] == 16000.0
    assert "MOLA" in prov["mars_excluded_because"]
    assert len(prov["lunar"]["sha256"]) == 64


# --------------------------------------------------------------------------- the prose

def test_the_lunar_documentation_stays_honest():
    """Prose rot is the failure mode here: a page quietly upgrading the result to a finding."""
    demo = (DOCS / "LUNAR-DEMONSTRATION.md").read_text(encoding="utf-8")
    assert "EXPLORATORY" in demo, "the demonstration page must label the result exploratory"
    low = demo.lower()
    for label in ("one lunar site", "uncertainty"):
        assert label in low, f"the demonstration page dropped its {label!r} caveat"
    # it must not claim base suitability anywhere
    for banned in ("suitable for a base", "safe to land", "base suitability is supported"):
        assert banned not in low, f"the page makes a base-suitability claim: {banned!r}"

    status = (DOCS / "LUNAR-STATUS.md").read_text(encoding="utf-8")
    assert "NOT STARTED** — blocked on data" not in status, (
        "the status page still says the lunar comparison is unstarted, which is now false"
    )
    assert "LUNAR-DEMONSTRATION.md" in status, "the status page must point at the exploratory result"


# --------------------------------------------------------------------------- real data (gated)

def test_real_site01_axes_reproduce_the_published_numbers():
    """With the 41 MB product present, re-derive the reference axes and compare to the artifact.

    Skipped (returns) when the product or rasterio is absent, so a NumPy-only clone stays green.
    """
    if not (MOON_TIF.exists() and ARTIFACT.exists()):
        return
    try:
        import rasterio
    except Exception:
        return
    from terratrace import features, support

    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    with rasterio.open(MOON_TIF) as ds:
        z = ds.read(1).astype("float64")
        dx = float(ds.res[0])
    assert dx == 5.0, f"unexpected native posting {dx} m"

    for scale, block in data["scales"].items():
        target = float(block["support_m"])
        factor = max(int(round(target / dx)), 1)
        agg, rec = support.block_aggregate(z, factor, dx, aggregation="mean", min_valid=0.5)
        got_dx = float(rec.target_support_m)
        n = block["cells"][0]
        h, w = agg.shape
        r0, c0 = (h - n) // 2, (w - n) // 2
        agg = agg[r0:r0 + n, c0:c0 + n]
        got = {
            "mean_slope_deg": float(np.nanmean(features.slope_deg(agg, got_dx, got_dx))),
            "mean_relief3_m": float(np.nanmean(features.relief(agg, window=3, alpha=0.0))),
            "elev_std_m": float(np.nanstd(agg[np.isfinite(agg)])),
        }
        for axis in AXES:
            want = block["axes"]["LUNAR_Site01"][axis]
            assert abs(got[axis] - want) <= max(0.01 * abs(want), 0.05), (
                f"{scale}/{axis}: artifact says {want}, raster gives {got[axis]}"
            )
