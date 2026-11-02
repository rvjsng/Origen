"""
constraints/kawasaki.py

Kawasaki's theorem: at a flat-foldable interior vertex with 2n creases, the
alternating sums of consecutive sector angles are equal (each = pi). For four
sectors this is A + C = B + D. NECESSARY for local flat-foldability only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

DEFAULT_TOLERANCE = 1e-6  # radians


@dataclass
class KawasakiResult:
    passed: bool
    sector_angles: List[float]
    odd_sum: float
    even_sum: float
    error: float
    tolerance: float
    explanation: str
    vertex_id: Optional[int] = None
    applicable: bool = True

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict:
        d = math.degrees
        return {"check": "kawasaki", "status": self.status, "vertex_id": self.vertex_id,
                "passed": self.passed, "applicable": self.applicable,
                "sector_angles_deg": [d(a) for a in self.sector_angles],
                "odd_sum_deg": d(self.odd_sum), "even_sum_deg": d(self.even_sum),
                "error_deg": d(self.error) if not math.isnan(self.error) else None,
                "tolerance_deg": d(self.tolerance), "explanation": self.explanation}


def check_kawasaki(sector_angles: List[float], vertex_id: Optional[int] = None,
                   tolerance: float = DEFAULT_TOLERANCE) -> KawasakiResult:
    n = len(sector_angles)
    if n == 0:
        return KawasakiResult(False, [], 0.0, 0.0, float("nan"), tolerance,
                              "No incident creases; Kawasaki does not apply.", vertex_id, False)
    if n % 2:
        return KawasakiResult(False, list(sector_angles), 0.0, 0.0, float("nan"), tolerance,
                              f"{n} creases (odd): a flat-foldable vertex needs an even number.",
                              vertex_id, False)
    odd = sum(sector_angles[0::2])
    even = sum(sector_angles[1::2])
    err = abs(odd - even)
    ok = err <= tolerance
    note = ""
    if abs(sum(sector_angles) - 2 * math.pi) > 1e-3:
        note = f" WARNING: sectors sum to {math.degrees(sum(sector_angles)):.3f} deg, not 360."
    verdict = "Satisfies" if ok else "Violates"
    cmp_ = "<=" if ok else ">"
    why = (f"Alternating sums {math.degrees(odd):.4f} vs {math.degrees(even):.4f} deg, "
           f"error {math.degrees(err):.6f} {cmp_} tol {math.degrees(tolerance):.6f} deg. "
           f"{verdict} Kawasaki (necessary condition only).{note}")
    return KawasakiResult(ok, list(sector_angles), odd, even, err, tolerance, why, vertex_id, True)
