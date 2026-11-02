"""visualization/crease_plot.py - matplotlib plots of crease patterns and the folded approximation."""
from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from core.crease_pattern import CreasePattern, MOUNTAIN, VALLEY
from core.targets import TargetShape
from simulation.folding import fold_to_point_cloud, normalize

STYLE = {"M": dict(color="#d83a39", ls=(0, (4, 1.3, 1, 1.3))), "V": dict(color="#5b49d0", ls=(0, (3, 2))),
         "B": dict(color="#777777", ls="-")}


def plot_crease_pattern(pattern: CreasePattern, ax=None, title: str = ""):
    """2D crease pattern: mountain = red dash-dot, valley = violet dashed."""
    ax = ax or plt.subplots(figsize=(4, 4))[1]
    s = pattern.paper_size
    ax.plot([0, s, s, 0, 0], [0, 0, s, s, 0], color="#555", lw=1)
    for c in pattern.creases():
        (x1, y1), (x2, y2) = pattern.position(c.u), pattern.position(c.v)
        ax.plot([x1, x2], [y1, y2], lw=1.6, **STYLE[c.assignment])
    for v in pattern.vertices():
        if pattern.degree(v) >= 3:
            ax.plot(*pattern.position(v), "ko", ms=4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=9)
    return ax


def plot_folded(pattern: CreasePattern, target: TargetShape, fold_amount: float, ax=None):
    """3D view of the SIMPLIFIED fold approximation against the (normalised) target cloud."""
    if ax is None:
        ax = plt.figure(figsize=(4.5, 4)).add_subplot(projection="3d")
    cloud = normalize(fold_to_point_cloud(pattern, fold_amount))
    tgt = normalize(target.points)
    ax.scatter(*tgt.T, s=6, c="#999", alpha=.5, label="target")
    ax.scatter(*cloud.T, s=10, c="#2a78d6", label="folded approx.")
    ax.set_title(f"Simplified fold model, amount {fold_amount:.2f}", fontsize=9)
    ax.legend(fontsize=7)
    return ax
