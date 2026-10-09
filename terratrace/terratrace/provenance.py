"""Provenance records and content hashing.

Every displayed value must resolve to a source, a transformation, and a
limitation. This module builds typed evidence edges and hashes artifacts
so a reviewer can reproduce and audit any claim.
"""
from __future__ import annotations

import hashlib
import json


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def source_node(source_id, provider, product_id, version, terms, status="S1"):
    return {
        "id": source_id,
        "type": "SourceProduct",
        "provider": provider,
        "product_id": product_id,
        "version": version,
        "terms": terms,
        "claim_status": status,
    }


def transform_node(transform_id, method, params, inputs):
    return {
        "id": transform_id,
        "type": "Transformation",
        "method": method,
        "params": params,
        "inputs": list(inputs),
    }


def measurement_node(measure_id, feature, value, unit, window_m, uncertainty, transform_id):
    return {
        "id": measure_id,
        "type": "FeatureMeasurement",
        "feature": feature,
        "value": value,
        "unit": unit,
        "window_m": window_m,
        "uncertainty": uncertainty,
        "generated_by": transform_id,
    }


def claim_node(claim_id, text, status, supports):
    return {
        "id": claim_id,
        "type": "Claim",
        "text": text,
        "claim_status": status,
        "supported_by": list(supports),
    }


class EvidenceGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add(self, node):
        self.nodes[node["id"]] = node
        return node["id"]

    def link(self, src, rel, dst):
        self.edges.append({"from": src, "rel": rel, "to": dst})

    def resolve(self, claim_id):
        """Return every node reachable from a claim (its evidence chain)."""
        seen, stack, chain = set(), [claim_id], []
        adjacency = {}
        for e in self.edges:
            adjacency.setdefault(e["from"], []).append(e["to"])
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            if nid in self.nodes:
                chain.append(self.nodes[nid])
            node = self.nodes.get(nid, {})
            for key in ("supported_by", "generated_by", "inputs"):
                val = node.get(key)
                if isinstance(val, list):
                    stack.extend(val)
                elif isinstance(val, str):
                    stack.append(val)
            stack.extend(adjacency.get(nid, []))
        return chain

    def to_dict(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}
