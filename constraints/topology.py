"""
constraints/topology.py - graph-level structural checks (cheap, run first):
connectivity, isolated vertices, duplicate edges, interior vertices of degree < 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.crease_pattern import CreasePattern
from core import graph_model


@dataclass
class TopologyResult:
    passed: bool
    checks: dict = field(default_factory=dict)
    explanation: str = ""

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict:
        return {"check": "topology", "status": self.status, "passed": self.passed,
                "checks": self.checks, "explanation": self.explanation}


def check_topology(pattern: CreasePattern) -> TopologyResult:
    issues, checks = [], {}
    connected = graph_model.is_connected(pattern)
    checks["connected"] = connected
    if not connected:
        n = len(graph_model.connected_components(pattern))
        issues.append(f"Graph is disconnected ({n} components).")
    iso = graph_model.find_isolated_vertices(pattern)
    checks["isolated_vertices"] = iso
    if iso:
        issues.append(f"Isolated vertices: {iso}.")
    dup = graph_model.find_duplicate_edges(pattern)
    checks["duplicate_edges"] = dup
    if dup:
        issues.append(f"Duplicate edges: {dup}.")
    low = [v for v in pattern.interior_vertices() if pattern.degree(v) < 3]
    checks["low_degree_interior_vertices"] = low
    if low:
        issues.append(f"Interior vertices with degree < 3 cannot satisfy Maekawa: {low}.")
    return TopologyResult(not issues, checks, "Topology OK." if not issues else " ".join(issues))
