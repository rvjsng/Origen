"""
core/targets.py - simple parametric target shapes as 3D point clouds.
  flat_sheet   : z = 0 square
  cylinder     : half-cylinder (a rolled sheet)
  curved_dome  : shallow paraboloid cap (simple curved/deployable shape)
Shape matching normalises clouds (centroid + RMS radius) so scale/offset are
ignored; only shape remains.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class TargetShape:
    name: str
    description: str
    points: np.ndarray  # (N, 3)


def flat_sheet(size: float = 100.0, resolution: int = 10) -> TargetShape:
    xs = np.linspace(0, size, resolution)
    X, Y = np.meshgrid(xs, xs)
    pts = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], axis=1)
    return TargetShape("flat_sheet", "Flat sheet, z = 0 everywhere (trivial target).", pts)


def cylinder(radius: float = 30.0, height: float = 100.0, resolution: int = 12) -> TargetShape:
    T, H = np.meshgrid(np.linspace(0, math.pi, resolution), np.linspace(0, height, resolution))
    pts = np.stack([(radius * np.cos(T)).ravel(), (radius * np.sin(T)).ravel(), H.ravel()], axis=1)
    return TargetShape("cylinder", f"Half-cylinder, radius {radius}, height {height} (rolled panel).", pts)


def curved_dome(width: float = 100.0, max_height: float = 25.0, resolution: int = 12) -> TargetShape:
    xs = np.linspace(-width / 2, width / 2, resolution)
    X, Y = np.meshgrid(xs, xs)
    r2_max = (width / 2) ** 2 * 2
    Z = np.clip(max_height * (1 - (X ** 2 + Y ** 2) / r2_max), 0, None)
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    return TargetShape("curved_dome", f"Shallow paraboloid dome, height {max_height} (simple curved deployable).", pts)


TARGET_REGISTRY = {"flat_sheet": flat_sheet, "cylinder": cylinder, "curved_dome": curved_dome}


def get_target(name: str, **kw) -> TargetShape:
    if name not in TARGET_REGISTRY:
        raise ValueError(f"Unknown target {name!r}; options: {list(TARGET_REGISTRY)}")
    return TARGET_REGISTRY[name](**kw)
