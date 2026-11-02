"""
core/crease_pattern.py

Graph representation of an origami crease pattern (NetworkX backed).
Vertices = crease intersection points; edges = creases with assignment
'M' (mountain), 'V' (valley) or 'B' (border, not a fold).
No validation happens here; that is the job of constraints/engine.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import networkx as nx

Point = Tuple[float, float]
MOUNTAIN, VALLEY, BORDER = "M", "V", "B"
VALID_ASSIGNMENTS = {MOUNTAIN, VALLEY, BORDER}


@dataclass
class Crease:
    u: int
    v: int
    assignment: str = VALLEY

    def other(self, node: int) -> int:
        if node == self.u:
            return self.v
        if node == self.v:
            return self.u
        raise ValueError(f"Node {node} is not an endpoint of this crease")


@dataclass
class CreasePattern:
    paper_size: float = 100.0
    graph: nx.Graph = field(default_factory=nx.Graph)
    _next_id: int = 0

    def add_vertex(self, position: Point) -> int:
        vid = self._next_id
        self._next_id += 1
        self.graph.add_node(vid, position=tuple(position))
        return vid

    def add_crease(self, u: int, v: int, assignment: str = VALLEY) -> None:
        if assignment not in VALID_ASSIGNMENTS:
            raise ValueError(f"Invalid assignment {assignment!r}")
        if u == v:
            raise ValueError("Cannot add a crease from a vertex to itself")
        self.graph.add_edge(u, v, assignment=assignment, length=self.crease_length(u, v))

    def position(self, vid: int) -> Point:
        return self.graph.nodes[vid]["position"]

    def set_position(self, vid: int, position: Point) -> None:
        self.graph.nodes[vid]["position"] = tuple(position)
        for nbr in self.graph.neighbors(vid):
            self.graph[vid][nbr]["length"] = self.crease_length(vid, nbr)

    def crease_length(self, u: int, v: int) -> float:
        (x1, y1), (x2, y2) = self.position(u), self.position(v)
        return math.hypot(x2 - x1, y2 - y1)

    def crease_angle(self, u: int, v: int) -> float:
        (x1, y1), (x2, y2) = self.position(u), self.position(v)
        return math.atan2(y2 - y1, x2 - x1) % (2 * math.pi)

    def vertices(self) -> List[int]:
        return list(self.graph.nodes)

    def creases(self) -> List[Crease]:
        return [Crease(u, v, d.get("assignment", VALLEY)) for u, v, d in self.graph.edges(data=True)]

    def degree(self, vid: int) -> int:
        return self.graph.degree[vid]

    def incident_creases(self, vid: int) -> List[Crease]:
        return [Crease(vid, n, self.graph[vid][n].get("assignment", VALLEY)) for n in self.graph.neighbors(vid)]

    def sector_angles(self, vid: int) -> List[float]:
        """Angular gaps (rad) between consecutive creases around vid, CCW."""
        nbrs = list(self.graph.neighbors(vid))
        if len(nbrs) < 2:
            return []
        angles = sorted(self.crease_angle(vid, n) for n in nbrs)
        return [(angles[(i + 1) % len(angles)] - angles[i]) % (2 * math.pi) for i in range(len(angles))]

    def mountain_valley_counts(self, vid: int) -> Tuple[int, int]:
        m = v = 0
        for c in self.incident_creases(vid):
            if c.assignment == MOUNTAIN:
                m += 1
            elif c.assignment == VALLEY:
                v += 1
        return m, v

    def is_boundary_vertex(self, vid: int) -> bool:
        x, y = self.position(vid)
        e, s = 1e-9, self.paper_size
        return abs(x) < e or abs(y) < e or abs(x - s) < e or abs(y - s) < e

    def interior_vertices(self) -> List[int]:
        return [v for v in self.vertices() if not self.is_boundary_vertex(v)]

    def copy(self) -> "CreasePattern":
        cp = CreasePattern(paper_size=self.paper_size)
        cp.graph = self.graph.copy()
        cp._next_id = self._next_id
        return cp

    def summary(self) -> Dict:
        return {
            "n_vertices": self.graph.number_of_nodes(),
            "n_creases": self.graph.number_of_edges(),
            "n_interior_vertices": len(self.interior_vertices()),
            "paper_size": self.paper_size,
        }

    def to_dict(self) -> Dict:
        """JSON-friendly export (used by the dashboard)."""
        return {
            "paper_size": self.paper_size,
            "vertices": {str(v): list(self.position(v)) for v in self.vertices()},
            "creases": [[c.u, c.v, c.assignment] for c in self.creases()],
        }
