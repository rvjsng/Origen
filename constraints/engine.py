"""
constraints/engine.py - the topology-constrained Constraint Engine.

Cheapest checks first, early rejection on first failing stage:
    topology -> geometry -> maekawa -> kawasaki

HONESTY NOTE: passing every stage means the pattern satisfies NECESSARY
mathematical conditions (Maekawa, Kawasaki at each interior vertex) plus
basic structural/geometric sanity. It does NOT prove global flat-foldability
(layer ordering, self-intersection during folding, thickness, material).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.crease_pattern import CreasePattern
from constraints.topology import check_topology, TopologyResult
from constraints.geometry import check_geometry, GeometryResult
from constraints.maekawa import check_maekawa, MaekawaResult
from constraints.kawasaki import check_kawasaki, KawasakiResult

STAGES = ["topology", "geometry", "maekawa", "kawasaki"]


@dataclass
class ConstraintReport:
    passed: bool
    rejected_at_stage: Optional[str]  # first failing stage; None if passed
    topology: Optional[TopologyResult] = None
    geometry: Optional[GeometryResult] = None
    maekawa_results: List[MaekawaResult] = field(default_factory=list)
    kawasaki_results: List[KawasakiResult] = field(default_factory=list)
    failed_stages: List[str] = field(default_factory=list)  # all failing stages (full mode)

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed, "rejected_at_stage": self.rejected_at_stage,
            "failed_stages": self.failed_stages,
            "topology": self.topology.to_dict() if self.topology else None,
            "geometry": self.geometry.to_dict() if self.geometry else None,
            "maekawa_results": [m.to_dict() for m in self.maekawa_results],
            "kawasaki_results": [k.to_dict() for k in self.kawasaki_results],
        }


class ConstraintEngine:
    def __init__(self, kawasaki_tolerance: float = 1e-6, check_crossings: bool = True):
        self.kawasaki_tolerance = kawasaki_tolerance
        self.check_crossings = check_crossings

    def evaluate(self, pattern: CreasePattern, stop_early: bool = True) -> ConstraintReport:
        failed: List[str] = []

        def finish(topo, geo, mk, kw) -> ConstraintReport:
            return ConstraintReport(passed=not failed, rejected_at_stage=failed[0] if failed else None,
                                    topology=topo, geometry=geo, maekawa_results=mk,
                                    kawasaki_results=kw, failed_stages=list(failed))

        topo = check_topology(pattern)
        if not topo.passed:
            failed.append("topology")
            if stop_early:
                return finish(topo, None, [], [])

        geo = check_geometry(pattern, self.check_crossings)
        if not geo.passed:
            failed.append("geometry")
            if stop_early:
                return finish(topo, geo, [], [])

        interior = pattern.interior_vertices()
        mk: List[MaekawaResult] = []
        for vid in interior:
            m, v = pattern.mountain_valley_counts(vid)
            mk.append(check_maekawa(m, v, vid))
            if not mk[-1].passed and stop_early:
                failed.append("maekawa")
                return finish(topo, geo, mk, [])
        if any(not r.passed for r in mk):
            failed.append("maekawa")

        kw: List[KawasakiResult] = []
        for vid in interior:
            kw.append(check_kawasaki(pattern.sector_angles(vid), vid, self.kawasaki_tolerance))
            if not kw[-1].passed and stop_early:
                failed.append("kawasaki")
                return finish(topo, geo, mk, kw)
        if any(not r.passed for r in kw):
            failed.append("kawasaki")
        return finish(topo, geo, mk, kw)
