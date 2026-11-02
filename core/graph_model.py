"""core/graph_model.py - pure graph-theory helpers over CreasePattern.graph."""
from __future__ import annotations

from typing import List, Tuple
import networkx as nx

from core.crease_pattern import CreasePattern


def is_connected(p: CreasePattern) -> bool:
    return p.graph.number_of_nodes() > 0 and nx.is_connected(p.graph)


def connected_components(p: CreasePattern) -> List[set]:
    return list(nx.connected_components(p.graph))


def find_isolated_vertices(p: CreasePattern) -> List[int]:
    return [n for n, d in p.graph.degree() if d == 0]


def find_duplicate_edges(p: CreasePattern) -> List[Tuple[int, int]]:
    """
    A simple nx.Graph cannot hold parallel edges, so this only reports edges
    appearing twice in the edge iterator (never for nx.Graph). It is a hook
    for MultiGraph-based patterns; the generator also avoids duplicates.
    """
    seen, dupes = set(), []
    for u, v in p.graph.edges():
        key = (min(u, v), max(u, v))
        if key in seen:
            dupes.append(key)
        seen.add(key)
    return dupes


def find_degenerate_edges(p: CreasePattern, min_length: float = 1e-6) -> List[Tuple[int, int]]:
    return [(u, v) for u, v, d in p.graph.edges(data=True) if d.get("length", p.crease_length(u, v)) < min_length]
