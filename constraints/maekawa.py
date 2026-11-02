"""
constraints/maekawa.py

Maekawa's theorem: at a flat-foldable interior vertex |M - V| = 2.
NECESSARY for local flat-foldability; NOT sufficient, and says nothing about
angles (Kawasaki) or global self-intersection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MaekawaResult:
    passed: bool
    mountain_count: int
    valley_count: int
    difference: int
    explanation: str
    vertex_id: Optional[int] = None

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict:
        return {"check": "maekawa", "status": self.status, "vertex_id": self.vertex_id,
                "passed": self.passed, "mountain_count": self.mountain_count,
                "valley_count": self.valley_count, "difference": self.difference,
                "explanation": self.explanation}


def check_maekawa(mountain_count: int, valley_count: int, vertex_id: Optional[int] = None) -> MaekawaResult:
    total = mountain_count + valley_count
    diff = abs(mountain_count - valley_count)
    passed = total > 0 and diff == 2
    if total == 0:
        why = "Vertex has no mountain/valley creases; Maekawa's theorem does not apply."
    elif passed:
        why = (f"|M-V| = |{mountain_count}-{valley_count}| = 2. Satisfies Maekawa "
               f"(necessary condition only; does not prove foldability).")
    else:
        why = f"|M-V| = |{mountain_count}-{valley_count}| = {diff} != 2. Violates Maekawa."
    return MaekawaResult(passed, mountain_count, valley_count, diff, why, vertex_id)
