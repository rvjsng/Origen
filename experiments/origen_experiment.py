"""
experiments/origen_experiment.py - runs ORIGEN and the baselines over multiple
seeded trials on each target and records parameters + raw per-trial metrics.

    python -m experiments.origen_experiment --trials 20 --iterations 200

Writes results/experiment_results.json. Values exist ONLY if this was run.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.targets import get_target, TARGET_REGISTRY
from core.search import run_origen_search
from experiments.baseline import run_baseline_search
from experiments.metrics import trial_metrics, aggregate, mean_curve

METHODS = ["origen", "baseline_guided", "baseline_eval_then_reject"]


def run_method(method: str, target, n_iter: int, seed: int):
    if method == "origen":
        return run_origen_search(target, n_iter, seed)
    mode = "guided_unfiltered" if method == "baseline_guided" else "evaluate_then_reject"
    return run_baseline_search(target, n_iter, seed, mode=mode)


def run_experiment(n_trials: int = 20, n_iterations: int = 200, seed0: int = 0, targets=None) -> dict:
    targets = targets or list(TARGET_REGISTRY)
    out = {"parameters": {"n_trials": n_trials, "n_iterations": n_iterations, "seed0": seed0,
                          "targets": targets, "methods": METHODS, "temperature": 0.05,
                          "kawasaki_tolerance": 1e-6, "python": platform.python_version(),
                          "numpy": np.__version__},
           "results": {}}
    for tname in targets:
        target = get_target(tname)
        out["results"][tname] = {}
        for method in METHODS:
            trials, hist_sim, hist_evals = [], [], []
            for k in range(n_trials):
                res = run_method(method, target, n_iterations, seed0 + k)
                trials.append(trial_metrics(res))
                hist_sim.append(res.stats.best_valid_similarity_history)
                hist_evals.append(res.stats.shape_evals_history)
            out["results"][tname][method] = {
                "aggregate": aggregate(trials), "trials": trials,
                "mean_best_similarity_curve": mean_curve(hist_sim),
                "mean_shape_evals_curve": mean_curve(hist_evals),
            }
            print(f"  {tname:12s} {method:26s} done", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--iterations", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "results", "experiment_results.json"))
    a = ap.parse_args()
    t0 = time.perf_counter()
    data = run_experiment(a.trials, a.iterations, a.seed0)
    data["parameters"]["total_wall_time_s"] = time.perf_counter() - t0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(data, f)
    print("wrote", os.path.abspath(a.out))
