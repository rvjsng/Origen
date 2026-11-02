"""
simulation/folding.py

SIMPLIFIED fold / shape-evaluation layer. THIS IS NOT A RIGID-ORIGAMI SIMULATOR.

For single-hub star patterns, each ray is a rigid rod rotated out of the paper
plane by an elevation whose sign follows its mountain/valley assignment and
whose magnitude is fold_amount * 90 deg. Gives an umbrella-like 3D point cloud
(flat at 0, cone/dome-like as fold_amount grows). It does NOT check that a
collision-free rigid folding motion exists. Replace `fold_to_point_cloud` with
a real simulator later without touching the constraint engine or search loop.

Separation of concerns:
  1. mathematical constraints -> constraints/engine.py
  2. geometric validation     -> constraints/geometry.py
  3. fold/shape evaluation    -> this file (approximate)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from core.crease_pattern import CreasePattern, MOUNTAIN, VALLEY
from core.targets import TargetShape

N_SAMPLES_PER_RAY = 6
FOLD_AMOUNT_GRID = [0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0]


def hub_vertex(pattern: CreasePattern) -> int:
    interior = pattern.interior_vertices()
    if not interior:
        raise ValueError("No interior vertex; cannot fold.")
    return max(interior, key=pattern.degree)


def fold_to_point_cloud(pattern: CreasePattern, fold_amount: float) -> np.ndarray:
    hub = hub_vertex(pattern)
    hx, hy = pattern.position(hub)
    pts = [(hx, hy, 0.0)]
    for c in pattern.incident_creases(hub):
        tip = c.other(hub)
        tx, ty = pattern.position(tip)
        radius = pattern.crease_length(hub, tip)
        norm = max(((tx - hx) ** 2 + (ty - hy) ** 2) ** 0.5, 1e-9)
        ux, uy = (tx - hx) / norm, (ty - hy) / norm
        sign = 1.0 if c.assignment == MOUNTAIN else (-1.0 if c.assignment == VALLEY else 0.0)
        elev = sign * fold_amount * (np.pi / 2)
        for frac in np.linspace(1.0 / N_SAMPLES_PER_RAY, 1.0, N_SAMPLES_PER_RAY):
            r = radius * frac
            pts.append((hx + ux * r * np.cos(elev), hy + uy * r * np.cos(elev), r * np.sin(elev)))
    return np.array(pts, dtype=float)


def normalize(points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return points
    c = points - points.mean(axis=0)
    rms = np.sqrt((c ** 2).sum(axis=1).mean())
    return c if rms < 1e-9 else c / rms


def chamfer_distance(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0 or len(b) == 0:
        return float("inf")
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return float(d.min(axis=1).mean() + d.min(axis=0).mean())


@dataclass
class FoldEvaluation:
    best_fold_amount: float
    best_chamfer_distance: float
    similarity_score: float  # 1/(1+chamfer), in (0,1]
    chamfer_by_fold_amount: List[float]

    def to_dict(self) -> dict:
        return {"best_fold_amount": self.best_fold_amount, "best_chamfer_distance": self.best_chamfer_distance,
                "similarity_score": self.similarity_score,
                "tried_fold_amounts": FOLD_AMOUNT_GRID, "chamfer_by_fold_amount": self.chamfer_by_fold_amount}


def evaluate_shape_match(pattern: CreasePattern, target: TargetShape) -> FoldEvaluation:
    t = normalize(target.points)
    dists = [chamfer_distance(normalize(fold_to_point_cloud(pattern, f)), t) for f in FOLD_AMOUNT_GRID]
    i = int(np.argmin(dists))
    sim = 1.0 / (1.0 + dists[i]) if np.isfinite(dists[i]) else 0.0
    return FoldEvaluation(FOLD_AMOUNT_GRID[i], dists[i], sim, dists)
