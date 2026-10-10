"""Frontier-ranking fixtures."""
from terratrace import frontier


def test_pareto_layers_peel_in_order():
    vecs = {"a": (0.1, 0.1), "b": (0.2, 0.5), "c": (0.5, 0.2), "d": (0.9, 0.9)}
    layers = frontier.pareto_layers(vecs)
    assert layers[0] == ["a"]
    assert set(layers[1]) == {"b", "c"}
    assert layers[2] == ["d"]


def test_rank_and_dominance_matrix():
    vecs = {"a": (0.1, 0.1), "b": (0.2, 0.5), "c": (0.5, 0.2), "d": (0.9, 0.9)}
    s = frontier.summarize(vecs)
    assert s["rank"] == {"a": 1, "b": 2, "c": 2, "d": 3}
    dm = s["dominance_matrix"]
    assert dm["a|b"] == "a" and dm["a|d"] == "a"
    assert dm["b|c"] == "~"
    assert dm["b|d"] == "b" and dm["c|d"] == "c"


def test_nan_vectors_are_ineligible_not_ranked():
    vecs = {"a": (0.1, 0.1), "bad": (float("nan"), 0.2)}
    s = frontier.summarize(vecs)
    assert s["ineligible"] == ["bad"]
    assert "bad" not in s["rank"]
    assert s["rank"]["a"] == 1


def test_within_layer_order_is_id_sorted_not_score():
    # Same Pareto layer (mutually non-dominated): order must be by id, so a vector
    # that is numerically "worse" on the first axis must NOT be pushed later.
    vecs = {"z_small": (0.1, 0.9), "a_big": (0.9, 0.1)}
    layers = frontier.pareto_layers(vecs)
    assert len(layers) == 1                      # neither dominates the other
    assert layers[0] == ["a_big", "z_small"]     # pure id sort, not value-ordered


def test_identical_vectors_share_one_layer():
    # Ties on every axis -> no strict dominance -> same (first) layer, id-sorted.
    vecs = {"c": (0.3, 0.3), "a": (0.3, 0.3), "b": (0.3, 0.3)}
    layers = frontier.pareto_layers(vecs)
    assert layers == [["a", "b", "c"]]
    s = frontier.summarize(vecs)
    assert s["rank"] == {"a": 1, "b": 1, "c": 1}


def test_dominance_matrix_is_order_independent():
    # Building from different dict insertion orders must give the same verdicts,
    # and keys are always "lo|hi" in id order.
    base = {"a": (0.1, 0.1), "b": (0.2, 0.5), "c": (0.5, 0.2)}
    shuffled = {"c": (0.5, 0.2), "a": (0.1, 0.1), "b": (0.2, 0.5)}
    assert frontier.dominance_matrix(base) == frontier.dominance_matrix(shuffled)
    dm = frontier.dominance_matrix(shuffled)
    assert set(dm) == {"a|b", "a|c", "b|c"}      # combinations(sorted(...), 2)
    assert dm["a|b"] == "a" and dm["a|c"] == "a" and dm["b|c"] == "~"


def test_summarize_is_deterministic_across_insertion_order():
    base = {"a": (0.1, 0.1), "b": (0.2, 0.5), "c": (0.5, 0.2), "d": (0.9, 0.9)}
    shuffled = {k: base[k] for k in ("d", "b", "a", "c")}
    assert frontier.summarize(base) == frontier.summarize(shuffled)
