"""
core/scoring.py - modular fitness.

  raw_quality = 0.85 * shape_similarity + 0.15 * structural_quality
  valid candidate   : score = 0.4 + 0.6 * raw_quality          (in [0.4, 1.0])
  rejected candidate: score = stage partial credit (<= 0.3), never shape-evaluated

Stage credit gives the annealer a gradient toward validity. Structural quality
is a placeholder parsimony heuristic (crease count near IDEAL_CREASE_COUNT).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.crease_pattern import CreasePattern
from core.targets import TargetShape
from constraints.engine import ConstraintEngine, ConstraintReport
from simulation.folding import evaluate_shape_match, FoldEvaluation

SHAPE_WEIGHT, STRUCTURE_WEIGHT = 0.85, 0.15
IDEAL_CREASE_COUNT = 6
STAGE_CREDIT = {"topology": 0.0, "geometry": 0.1, "maekawa": 0.2, "kawasaki": 0.3}


@dataclass
class ScoredCandidate:
    pattern: CreasePattern
    constraint_report: ConstraintReport
    fold_evaluation: Optional[FoldEvaluation]
    score: float
    raw_quality: Optional[float] = None

    def to_dict(self) -> dict:
        return {"score": self.score, "constraints_passed": self.constraint_report.passed,
                "rejected_at_stage": self.constraint_report.rejected_at_stage,
                "fold_evaluation": self.fold_evaluation.to_dict() if self.fold_evaluation else None,
                "pattern_summary": self.pattern.summary()}


def structural_quality(pattern: CreasePattern) -> float:
    n = pattern.graph.number_of_edges()
    return max(0.0, 1.0 - abs(n - IDEAL_CREASE_COUNT) / (IDEAL_CREASE_COUNT * 2))


def raw_quality(similarity: float, pattern: CreasePattern) -> float:
    return SHAPE_WEIGHT * similarity + STRUCTURE_WEIGHT * structural_quality(pattern)


def valid_score(raw: float) -> float:
    return 0.4 + 0.6 * raw


def rejected_score(stage: Optional[str]) -> float:
    return STAGE_CREDIT.get(stage, 0.0)


def score_candidate(pattern: CreasePattern, target: TargetShape, engine: ConstraintEngine) -> ScoredCandidate:
    """Stand-alone scoring (constraints first, shape evaluation only if they pass)."""
    rep = engine.evaluate(pattern, stop_early=True)
    if not rep.passed:
        return ScoredCandidate(pattern, rep, None, rejected_score(rep.rejected_at_stage))
    fe = evaluate_shape_match(pattern, target)
    raw = raw_quality(fe.similarity_score, pattern)
    return ScoredCandidate(pattern, rep, fe, valid_score(raw), raw)
