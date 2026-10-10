"""Pareto frontier ranking for multi-candidate (batch) studies.

With many Earth candidates, the non-dominated set alone is not a ranking. This
module peels successive Pareto layers (layer 1 = non-dominated, layer 2 =
non-dominated once layer 1 is removed, ...) and exposes a dominance matrix, so a
batch run yields a defensible shortlist. Within a layer the order is a *transparent
sum tie-break only* — it is NOT a composite "Mars-likeness" score and carries no
decision weight.
"""
from __future__ import annotations

import math
from itertools import combinations

from .decision import dominates


def _finite(v):
    return all(math.isfinite(x) for x in v)


def pareto_layers(vectors):
    """Return ordered layers (best first). NaN vectors are excluded."""
    rem = {u: tuple(float(x) for x in v) for u, v in vectors.items() if _finite(v)}
    layers = []
    while rem:
        front = [u for u in rem if not any(dominates(rem[o], rem[u]) for o in rem if o != u)]
        if not front:                      # safety; strict dominance can't cycle
            front = list(rem)
        front.sort()                        # id order only — list position implies NO score
        layers.append(front)
        for u in front:
            del rem[u]
    return layers


def dominance_matrix(vectors):
    """Pairwise dominance: value is the dominating unit id, or '~' for neither."""
    fin = {u: tuple(float(x) for x in v) for u, v in vectors.items() if _finite(v)}
    out = {}
    for i, j in combinations(sorted(fin), 2):
        if dominates(fin[i], fin[j]):
            out[f"{i}|{j}"] = i
        elif dominates(fin[j], fin[i]):
            out[f"{i}|{j}"] = j
        else:
            out[f"{i}|{j}"] = "~"
    return out


def summarize(vectors):
    layers = pareto_layers(vectors)
    rank = {}
    for li, layer in enumerate(layers, 1):
        for u in layer:
            rank[u] = li
    ineligible = sorted(u for u, v in vectors.items() if not _finite(v))
    return {
        "pareto_layers": layers,
        "rank": rank,
        "dominance_matrix": dominance_matrix(vectors),
        "ineligible": ineligible,
        "note": ("rank = Pareto layer (1 = non-dominated / best). Layer membership is "
                 "the ranking; within-layer order is by id and carries NO score. Reflects "
                 "the baseline scenario; the stable recommendation may be a subset of layer 1."),
    }
