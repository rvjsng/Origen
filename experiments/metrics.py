"""
experiments/metrics.py - per-trial metrics and cross-trial aggregation.

Definitions (all computed from the recorded SearchStats; nothing is estimated):
  valid_discovery_rate   = candidates passing all constraints / candidates generated
  invalid_total          = generated - passed
  invalid_sent_to_sim    = shape evaluations - passed      (ORIGEN: 0 by construction)
  invalid_avoided_pct    = 100 * (1 - invalid_sent_to_sim / invalid_total)
  iterations_to_best     = first iteration at which best-valid-similarity reaches its final value
  best_similarity        = shape similarity 1/(1+Chamfer) of the best VALID candidate (0 if none found)
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from core.search import SearchResult


def trial_metrics(res: SearchResult) -> Dict:
    st = res.stats
    invalid_total = st.n_generated - st.n_passed_constraints
    sent = max(st.n_shape_evaluations - st.n_passed_constraints, 0)
    avoided = 100.0 * (1.0 - sent / invalid_total) if invalid_total > 0 else float("nan")
    hist = st.best_valid_similarity_history
    final = hist[-1] if hist else 0.0
    iters_to_best = next((i for i, v in enumerate(hist) if v >= final - 1e-12), len(hist))
    return {
        "n_generated": st.n_generated,
        "n_rejected_total": st.total_rejected(),
        **{f"rejected_{k}": v for k, v in st.rejected_by_stage.items()},
        "n_passed_constraints": st.n_passed_constraints,
        "n_shape_evaluations": st.n_shape_evaluations,
        "runtime_s": st.runtime_s,
        "valid_discovery_rate": st.n_passed_constraints / st.n_generated if st.n_generated else 0.0,
        "invalid_total": invalid_total,
        "invalid_sent_to_simulation": sent,
        "invalid_avoided_pct": avoided,
        "best_similarity": res.best_similarity(),
        "iterations_to_best": iters_to_best,
        "first_valid_iteration": st.first_valid_iteration,
    }


def aggregate(trials: List[Dict]) -> Dict:
    keys = [k for k, v in trials[0].items() if isinstance(v, (int, float))]
    out = {}
    for k in keys:
        vals = np.array([t[k] if t[k] is not None else np.nan for t in trials], dtype=float)
        out[k] = {"mean": float(np.nanmean(vals)), "std": float(np.nanstd(vals)),
                  "min": float(np.nanmin(vals)), "max": float(np.nanmax(vals))}
    out["n_trials"] = len(trials)
    return out


def mean_curve(histories: List[List[float]]) -> List[float]:
    return np.mean(np.array(histories, dtype=float), axis=0).tolist()
