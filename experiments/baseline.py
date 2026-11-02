"""
experiments/baseline.py - UNCONSTRAINED baselines (kept separate from ORIGEN).

Both baselines use the same mutation operators, annealing rule, start
candidate generator and scoring terms as ORIGEN, and run the (expensive)
fold/shape evaluation on EVERY proposal BEFORE any validity information is used.

mode="guided_unfiltered" (default; "generate -> evaluate -> reject bad ones afterwards"):
    The search objective is shape quality only (raw_quality, no validity term).
    Invalid candidates can be accepted into the chain. Validity is checked
    afterwards, purely to decide which designs may be REPORTED as valid.

mode="evaluate_then_reject":
    Shape evaluation is run first, then invalid candidates are rejected with
    the same stage-credit score ORIGEN uses. The search trajectory is therefore
    the same as ORIGEN's for a given seed; only the evaluation cost differs.
    Included as a control / implementation sanity check.
"""
from __future__ import annotations

import random
import time
from typing import Optional

from core.candidate_generator import generate_single_vertex_candidate
from core.scoring import ScoredCandidate, raw_quality, valid_score, rejected_score
from core.search import SearchResult, SearchStats, anneal_accept, propose_mutation
from core.targets import TargetShape
from constraints.engine import ConstraintEngine
from simulation.folding import evaluate_shape_match

MODES = ("guided_unfiltered", "evaluate_then_reject")


def run_baseline_search(target: TargetShape, n_iterations: int = 200, seed: int = 0,
                        mode: str = "guided_unfiltered", paper_size: float = 100.0,
                        kawasaki_tolerance: float = 1e-6, temperature: float = 0.05) -> SearchResult:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    t0 = time.perf_counter()
    rng, engine, st = random.Random(seed), ConstraintEngine(kawasaki_tolerance), SearchStats()
    best_valid: Optional[ScoredCandidate] = None

    def evaluate(pattern, it) -> ScoredCandidate:
        nonlocal best_valid
        st.n_generated += 1
        st.n_shape_evaluations += 1                       # ALWAYS pay for shape evaluation first
        try:
            fe = evaluate_shape_match(pattern, target)
        except ValueError:
            fe = None
        rep = engine.evaluate(pattern, stop_early=False)  # bookkeeping: classify validity after the fact
        if rep.passed:
            st.n_passed_constraints += 1
            if st.first_valid_iteration is None:
                st.first_valid_iteration = it
        else:
            st.rejected_by_stage[rep.rejected_at_stage] += 1
        sim = fe.similarity_score if fe else 0.0
        raw = raw_quality(sim, pattern)
        if mode == "guided_unfiltered":
            score = raw                                    # validity NOT part of the objective
        else:
            score = valid_score(raw) if rep.passed else rejected_score(rep.rejected_at_stage)
        sc = ScoredCandidate(pattern, rep, fe, score, raw)
        if rep.passed and fe is not None:
            key = valid_score(raw)
            if best_valid is None or key > valid_score(best_valid.raw_quality):
                best_valid = sc
        return sc

    def log():
        st.best_score_history.append(valid_score(best_valid.raw_quality) if best_valid else 0.0)
        st.best_valid_similarity_history.append(best_valid.fold_evaluation.similarity_score if best_valid else 0.0)
        st.shape_evals_history.append(st.n_shape_evaluations)

    current = evaluate(generate_single_vertex_candidate(paper_size, rng=rng), 0)
    log()
    for it in range(1, n_iterations + 1):
        prop = evaluate(propose_mutation(current.pattern, rng), it)
        if anneal_accept(prop.score - current.score, temperature, rng):
            current = prop
        log()
    st.runtime_s = time.perf_counter() - t0
    params = dict(method=f"baseline:{mode}", target=target.name, n_iterations=n_iterations, seed=seed,
                  kawasaki_tolerance=kawasaki_tolerance, temperature=temperature, paper_size=paper_size)
    return SearchResult(best_valid, st, params)
