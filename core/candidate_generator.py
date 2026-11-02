"""
core/candidate_generator.py

Single-hub "star" candidates on a square sheet: one interior hub at the
centre, n rays to the boundary. Valid-by-construction candidates use evenly
spaced rays (exactly Kawasaki) and a Maekawa-correct M/V split. Deliberately
corrupted candidates (force_invalid) give the constraint engine real work.
"""
from __future__ import annotations

import math
import random
from typing import List, Optional

from core.crease_pattern import CreasePattern, MOUNTAIN, VALLEY

INVALID_MODES = ["maekawa", "kawasaki", "disconnect", "degenerate", "out_of_bounds"]


def boundary_point(paper_size: float, angle: float) -> tuple:
    """Where a ray from the sheet centre at `angle` meets the square boundary."""
    c, half = paper_size / 2.0, paper_size / 2.0
    dx, dy = math.cos(angle), math.sin(angle)
    t = min(half / abs(dx) if abs(dx) > 1e-12 else float("inf"),
            half / abs(dy) if abs(dy) > 1e-12 else float("inf"))
    x = min(max(c + dx * t, 0.0), paper_size)
    y = min(max(c + dy * t, 0.0), paper_size)
    return (x, y)


def valid_assignments(n_rays: int, rng: random.Random) -> List[str]:
    m = n_rays // 2 + 1 if n_rays % 2 == 0 else (n_rays + 1) // 2
    a = [MOUNTAIN] * m + [VALLEY] * (n_rays - m)
    rng.shuffle(a)
    return a


def generate_single_vertex_candidate(paper_size: float = 100.0, n_rays: Optional[int] = None,
                                     rng: Optional[random.Random] = None,
                                     force_invalid: Optional[str] = None) -> CreasePattern:
    rng = rng or random.Random()
    n_rays = n_rays or rng.choice([4, 4, 6, 6, 8])
    cp = CreasePattern(paper_size=paper_size)
    hub = cp.add_vertex((paper_size / 2, paper_size / 2))

    if force_invalid == "kawasaki":
        angles = sorted(rng.uniform(0, 2 * math.pi) for _ in range(n_rays))
    else:
        phase = rng.uniform(0, 2 * math.pi / n_rays)
        angles = [phase + 2 * math.pi * i / n_rays for i in range(n_rays)]

    tips = [cp.add_vertex(boundary_point(paper_size, a)) for a in angles]

    if force_invalid == "maekawa":
        half = n_rays // 2
        assign = [MOUNTAIN] * half + [VALLEY] * (n_rays - half)
    else:
        assign = valid_assignments(n_rays, rng)
    for t, a in zip(tips, assign):
        cp.add_crease(hub, t, a)

    if force_invalid == "disconnect":
        a = cp.add_vertex((paper_size * 0.05, paper_size * 0.05))
        b = cp.add_vertex((paper_size * 0.10, paper_size * 0.05))
        cp.add_crease(a, b, MOUNTAIN)
    elif force_invalid == "degenerate":
        a = cp.add_vertex((paper_size * 0.5, paper_size * 0.9))
        b = cp.add_vertex((paper_size * 0.5, paper_size * 0.9))
        cp.add_crease(a, b, VALLEY)
    elif force_invalid == "out_of_bounds":
        x, y = cp.position(tips[0])
        cp.set_position(tips[0], (x + paper_size * 0.5, y + paper_size * 0.5))
    return cp


def generate_population(n: int, paper_size: float = 100.0, invalid_fraction: float = 0.5,
                        seed: Optional[int] = None) -> List[CreasePattern]:
    """n candidates, ~invalid_fraction deliberately corrupted (rest valid by construction)."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        mode = rng.choice(INVALID_MODES) if rng.random() < invalid_fraction else None
        out.append(generate_single_vertex_candidate(paper_size, rng.choice([4, 4, 6, 6, 8]), rng, mode))
    return out
