"""
core/search.py

Shared mutation operators + the ORIGEN topology-constrained stochastic search
(simulated-annealing-style Monte Carlo).

ORIGEN loop per proposal:
    mutate -> ConstraintEngine (early reject) -> shape evaluation ONLY if it passes.

The unconstrained baselines live in experiments/baseline.py and import the SAME
mutation operators and scoring terms, so differences between them and ORIGEN
come only from whether/when the constraint engine is used.

Operators (some deliberately validity-breaking, some validity-preserving):
  move_crease        - perturb one ray's angle         (usually breaks Kawasaki)
  flip_assignment    - flip M<->V on one crease        (breaks Maekawa)
  swap_assignments   - swap an M and a V crease        (keeps Maekawa)
  rotate_pair        - rotate two adjacent rays by the same delta (keeps Kawasaki exactly)
  add_pair           - add one M + one V ray, re-space (keeps Maekawa, repairs Kawasaki)
  remove_pair        - remove one M + one V ray if degree stays >= 4, re-space
  resymmetrize       - even ray spacing                (repairs Kawasaki)
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from core.crease_pattern import CreasePattern, MOUNTAIN, VALLEY
from core.candidate_generator import boundary_point, generate_single_vertex_candidate
from core.scoring import ScoredCandidate, raw_quality, valid_score, rejected_score
from core.targets import TargetShape
from constraints.engine import ConstraintEngine
from simulation.folding import evaluate_shape_match


# ---------------------------------------------------------------- operators
def _hub(cp: CreasePattern) -> Optional[int]:
    interior = cp.interior_vertices()
    return max(interior, key=cp.degree) if interior else None


def _sorted_tips(cp: CreasePattern, hub: int) -> List[int]:
    return sorted(cp.graph.neighbors(hub), key=lambda t: cp.crease_angle(hub, t))


def move_crease(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp, hub = p.copy(), _hub(p)
    if hub is None:
        return cp
    tip = rng.choice(list(cp.graph.neighbors(hub)))
    cp.set_position(tip, boundary_point(cp.paper_size, cp.crease_angle(hub, tip) + rng.uniform(-0.35, 0.35)))
    return cp


def flip_assignment(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp = p.copy()
    edges = list(cp.graph.edges())
    if edges:
        u, v = rng.choice(edges)
        a = cp.graph[u][v]["assignment"]
        cp.graph[u][v]["assignment"] = VALLEY if a == MOUNTAIN else MOUNTAIN
    return cp


def swap_assignments(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp = p.copy()
    ms = [(u, v) for u, v, d in cp.graph.edges(data=True) if d["assignment"] == MOUNTAIN]
    vs = [(u, v) for u, v, d in cp.graph.edges(data=True) if d["assignment"] == VALLEY]
    if ms and vs:
        (a, b), (c, d) = rng.choice(ms), rng.choice(vs)
        cp.graph[a][b]["assignment"], cp.graph[c][d]["assignment"] = VALLEY, MOUNTAIN
    return cp


def rotate_pair(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp, hub = p.copy(), _hub(p)
    if hub is None:
        return cp
    tips = _sorted_tips(cp, hub)
    if len(tips) < 4:
        return cp
    i, delta = rng.randrange(len(tips)), rng.uniform(-0.3, 0.3)
    for t in (tips[i], tips[(i + 1) % len(tips)]):
        cp.set_position(t, boundary_point(cp.paper_size, cp.crease_angle(hub, t) + delta))
    return cp


def resymmetrize(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp, hub = p.copy(), _hub(p)
    if hub is None:
        return cp
    tips = _sorted_tips(cp, hub)
    n = len(tips)
    if n < 2:
        return cp
    phase = cp.crease_angle(hub, tips[0])
    for i, t in enumerate(tips):
        cp.set_position(t, boundary_point(cp.paper_size, phase + 2 * math.pi * i / n))
    return cp


def add_pair(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp, hub = p.copy(), _hub(p)
    if hub is None or cp.degree(hub) >= 10:
        return cp
    for a in (MOUNTAIN, VALLEY):
        cp.add_crease(hub, cp.add_vertex(boundary_point(cp.paper_size, rng.uniform(0, 2 * math.pi))), a)
    return resymmetrize(cp, rng)


def remove_pair(p: CreasePattern, rng: random.Random) -> CreasePattern:
    cp, hub = p.copy(), _hub(p)
    if hub is None or cp.degree(hub) <= 4:
        return cp
    ms = [t for t in cp.graph.neighbors(hub) if cp.graph[hub][t]["assignment"] == MOUNTAIN]
    vs = [t for t in cp.graph.neighbors(hub) if cp.graph[hub][t]["assignment"] == VALLEY]
    if not ms or not vs:
        return cp
    for t in (rng.choice(ms), rng.choice(vs)):
        cp.graph.remove_node(t)
    return resymmetrize(cp, rng)


OPERATORS: Dict[str, Callable[[CreasePattern, random.Random], CreasePattern]] = {
    "move_crease": move_crease, "flip_assignment": flip_assignment, "swap_assignments": swap_assignments,
    "rotate_pair": rotate_pair, "add_pair": add_pair, "remove_pair": remove_pair, "resymmetrize": resymmetrize,
}
_OP_LIST = list(OPERATORS.values())


def propose_mutation(p: CreasePattern, rng: random.Random) -> CreasePattern:
    return rng.choice(_OP_LIST)(p, rng)


# ---------------------------------------------------------------- bookkeeping
@dataclass
class SearchStats:
    n_generated: int = 0
    rejected_by_stage: Dict[str, int] = field(default_factory=lambda: {"topology": 0, "geometry": 0, "maekawa": 0, "kawasaki": 0})
    n_passed_constraints: int = 0
    n_shape_evaluations: int = 0
    runtime_s: float = 0.0
    first_valid_iteration: Optional[int] = None
    best_score_history: List[float] = field(default_factory=list)       # best overall score so far
    best_valid_similarity_history: List[float] = field(default_factory=list)  # best VALID shape similarity (0 until found)
    shape_evals_history: List[int] = field(default_factory=list)  # cumulative shape evaluations after each iteration

    def total_rejected(self) -> int:
        return sum(self.rejected_by_stage.values())

    def to_dict(self) -> dict:
        return {"n_generated": self.n_generated, "rejected_by_stage": dict(self.rejected_by_stage),
                "total_rejected": self.total_rejected(), "n_passed_constraints": self.n_passed_constraints,
                "n_shape_evaluations": self.n_shape_evaluations, "runtime_s": self.runtime_s,
                "first_valid_iteration": self.first_valid_iteration}


@dataclass
class SearchResult:
    best_valid: Optional[ScoredCandidate]
    stats: SearchStats
    params: dict = field(default_factory=dict)

    def best_similarity(self) -> float:
        fe = self.best_valid.fold_evaluation if self.best_valid else None
        return fe.similarity_score if fe else 0.0


def anneal_accept(delta: float, temperature: float, rng: random.Random) -> bool:
    return delta >= 0 or rng.random() < math.exp(delta / max(temperature, 1e-6))


# ---------------------------------------------------------------- ORIGEN search
def run_origen_search(target: TargetShape, n_iterations: int = 200, seed: int = 0,
                      paper_size: float = 100.0, kawasaki_tolerance: float = 1e-6,
                      temperature: float = 0.05) -> SearchResult:
    """Topology-constrained search: constraint engine first, shape evaluation only for survivors."""
    t0 = time.perf_counter()
    rng, engine, st = random.Random(seed), ConstraintEngine(kawasaki_tolerance), SearchStats()
    best_valid: Optional[ScoredCandidate] = None

    def evaluate(pattern: CreasePattern, it: int) -> ScoredCandidate:
        nonlocal best_valid
        st.n_generated += 1
        rep = engine.evaluate(pattern, stop_early=True)
        if not rep.passed:
            st.rejected_by_stage[rep.rejected_at_stage] += 1
            return ScoredCandidate(pattern, rep, None, rejected_score(rep.rejected_at_stage))
        st.n_passed_constraints += 1
        st.n_shape_evaluations += 1
        if st.first_valid_iteration is None:
            st.first_valid_iteration = it
        fe = evaluate_shape_match(pattern, target)
        raw = raw_quality(fe.similarity_score, pattern)
        sc = ScoredCandidate(pattern, rep, fe, valid_score(raw), raw)
        if best_valid is None or sc.score > best_valid.score:
            best_valid = sc
        return sc

    def log(cur: ScoredCandidate):
        st.best_score_history.append(best_valid.score if best_valid else 0.0)
        st.best_valid_similarity_history.append(best_valid.fold_evaluation.similarity_score if best_valid else 0.0)
        st.shape_evals_history.append(st.n_shape_evaluations)

    current = evaluate(generate_single_vertex_candidate(paper_size, rng=rng), 0)
    log(current)
    for it in range(1, n_iterations + 1):
        prop = evaluate(propose_mutation(current.pattern, rng), it)
        if anneal_accept(prop.score - current.score, temperature, rng):
            current = prop
        log(current)
    st.runtime_s = time.perf_counter() - t0
    params = dict(method="origen", target=target.name, n_iterations=n_iterations, seed=seed,
                  kawasaki_tolerance=kawasaki_tolerance, temperature=temperature, paper_size=paper_size)
    return SearchResult(best_valid, st, params)
