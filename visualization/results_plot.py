"""visualization/results_plot.py - plots from results/experiment_results.json (real recorded runs only)."""
from __future__ import annotations

import json
import os

import matplotlib.pyplot as plt

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results", "experiment_results.json")
LABELS = {"origen": "ORIGEN", "baseline_guided": "Baseline (shape-guided)", "baseline_eval_then_reject": "Control (evaluate, then reject)"}
COLORS = {"origen": "#2a78d6", "baseline_guided": "#eb6834", "baseline_eval_then_reject": "#1baf7a"}


def load_results(path: str = RESULTS):
    """Returns the recorded experiment dict, or None if the experiment has not been run."""
    return json.load(open(path)) if os.path.exists(path) else None


def plot_convergence(res: dict, target: str, vs_evals: bool = False):
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for m, d in res["results"][target].items():
        y = d["mean_best_similarity_curve"]
        x = d["mean_shape_evals_curve"] if vs_evals else range(len(y))
        ax.plot(x, y, label=LABELS[m], color=COLORS[m], ls="--" if m == "baseline_eval_then_reject" else "-")
    ax.set_xlabel("cumulative shape evaluations" if vs_evals else "iteration")
    ax.set_ylabel("best valid similarity (mean)")
    ax.legend(fontsize=8)
    ax.set_title(f"{target}: {res['parameters']['n_trials']} trials", fontsize=10)
    fig.tight_layout()
    return fig


def plot_metric_bars(res: dict, target: str, metric: str, title: str):
    fig, ax = plt.subplots(figsize=(4.5, 2.8))
    ms = list(res["results"][target])
    vals = [res["results"][target][m]["aggregate"][metric]["mean"] for m in ms]
    errs = [res["results"][target][m]["aggregate"][metric]["std"] for m in ms]
    ax.barh([LABELS[m] for m in ms], vals, xerr=errs, color=[COLORS[m] for m in ms])
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    return fig
