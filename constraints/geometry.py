"""
constraints/geometry.py - geometric validity: inside paper, positive length,
no proper crossings between non-adjacent creases. Says nothing about
flat-foldability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import List, Tuple

from core.crease_pattern import CreasePattern

MIN_LENGTH = 1e-6


@dataclass
class GeometryResult:
    passed: bool
    out_of_bounds_vertices: List[int] = field(default_factory=list)
    zero_length_creases: List[Tuple[int, int]] = field(default_factory=list)
    crossing_creases: List[tuple] = field(default_factory=list)
    explanation: str = ""

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict:
        return {"check": "geometry", "status": self.status, "passed": self.passed,
                "out_of_bounds_vertices": self.out_of_bounds_vertices,
                "zero_length_creases": self.zero_length_creases,
                "crossing_creases": self.crossing_creases, "explanation": self.explanation}


def _segments_intersect(p1, p2, p3, p4, eps=1e-9) -> bool:
    def orient(a, b, c):
        val = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(val) < eps else (1 if val > 0 else 2)

    def on_seg(a, b, c):
        return (min(a[0], b[0]) - eps <= c[0] <= max(a[0], b[0]) + eps and
                min(a[1], b[1]) - eps <= c[1] <= max(a[1], b[1]) + eps)

    o1, o2, o3, o4 = orient(p1, p2, p3), orient(p1, p2, p4), orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    return ((o1 == 0 and on_seg(p1, p2, p3)) or (o2 == 0 and on_seg(p1, p2, p4)) or
            (o3 == 0 and on_seg(p3, p4, p1)) or (o4 == 0 and on_seg(p3, p4, p2)))


def check_geometry(pattern: CreasePattern, check_crossings: bool = True) -> GeometryResult:
    issues = []
    eps, s = 1e-6, pattern.paper_size
    oob = [v for v in pattern.vertices()
           if not (-eps <= pattern.position(v)[0] <= s + eps and -eps <= pattern.position(v)[1] <= s + eps)]
    if oob:
        issues.append(f"Vertices outside paper: {oob}.")
    zero = [(u, v) for u, v, d in pattern.graph.edges(data=True)
            if d.get("length", pattern.crease_length(u, v)) < MIN_LENGTH]
    if zero:
        issues.append(f"Zero-length creases: {zero}.")
    crossings = []
    if check_crossings:
        for (u1, v1), (u2, v2) in combinations(list(pattern.graph.edges()), 2):
            if {u1, v1} & {u2, v2}:
                continue
            if _segments_intersect(pattern.position(u1), pattern.position(v1),
                                   pattern.position(u2), pattern.position(v2)):
                crossings.append(((u1, v1), (u2, v2)))
        if crossings:
            issues.append(f"{len(crossings)} crease pair(s) cross away from a vertex.")
    return GeometryResult(not issues, oob, zero, crossings, "Geometry OK." if not issues else " ".join(issues))
