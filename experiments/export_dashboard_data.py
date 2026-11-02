"""
experiments/export_dashboard_data.py

Collects REAL outputs (experiment_results.json + deterministic re-runs of the
best ORIGEN seeds + a generated candidate population) into
results/dashboard_data.json for the project screen. Nothing is hand-typed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core.targets import get_target, TARGET_REGISTRY
from core.search import run_origen_search
from core.candidate_generator import generate_population
from constraints.engine import ConstraintEngine
from simulation.folding import fold_to_point_cloud, FOLD_AMOUNT_GRID, hub_vertex

R = lambda a, n=3: np.round(np.asarray(a, dtype=float), n).tolist()


def first_failure_text(rep) -> str:
    if rep.passed:
        return "All necessary constraints satisfied."
    s = rep.rejected_at_stage
    if s == "topology":
        return rep.topology.explanation
    if s == "geometry":
        return rep.geometry.explanation
    if s == "maekawa":
        return next(r.explanation for r in rep.maekawa_results if not r.passed)
    return next(r.explanation for r in rep.kawasaki_results if not r.passed)


def pattern_block(pattern, target, fe):
    hub = hub_vertex(pattern)
    rays = pattern.incident_creases(hub)
    frames = []
    for f in FOLD_AMOUNT_GRID:
        cloud = fold_to_point_cloud(pattern, f)
        frames.append([R(cloud[1 + 6 * i: 7 + 6 * i]) for i in range(len(rays))])
    rep = ConstraintEngine().evaluate(pattern, stop_early=False)
    return {
        "pattern": pattern.to_dict(),
        "hub": hub,
        "ray_assignments": [c.assignment for c in rays],
        "hub_xy": list(pattern.position(hub)),
        "fold_amounts": FOLD_AMOUNT_GRID,
        "frames": frames,  # frames[fold_idx][ray_idx] = 6 points (x, y, z)
        "best_fold_amount": fe.best_fold_amount,
        "similarity": fe.similarity_score,
        "chamfer": fe.best_chamfer_distance,
        "constraints": rep.to_dict(),
    }


def main():
    res_path = os.path.join(ROOT, "results", "experiment_results.json")
    exp = json.load(open(res_path))
    P = exp["parameters"]
    out = {"parameters": P, "targets": {}, "experiment": {}, "population_demo": {}}

    for tname in P["targets"]:
        tgt = get_target(tname)
        tr = exp["results"][tname]
        # ---- experiment summary (copied from the recorded run)
        out["experiment"][tname] = {}
        for m, v in tr.items():
            out["experiment"][tname][m] = {
                "aggregate": v["aggregate"],
                "sim_curve": R(v["mean_best_similarity_curve"], 4),
                "evals_curve": R(v["mean_shape_evals_curve"], 2),
            }
        o = [t["best_similarity"] for t in tr["origen"]["trials"]]
        b = [t["best_similarity"] for t in tr["baseline_guided"]["trials"]]
        out["experiment"][tname]["paired_vs_guided"] = {
            "origen_better": int(sum(x > y + 1e-9 for x, y in zip(o, b))),
            "tie": int(sum(abs(x - y) <= 1e-9 for x, y in zip(o, b))),
            "origen_worse": int(sum(x < y - 1e-9 for x, y in zip(o, b))),
        }
        # ---- best ORIGEN design: re-run the best seed (deterministic) and verify
        k = int(np.argmax(o))
        seed = P["seed0"] + k
        rerun = run_origen_search(tgt, P["n_iterations"], seed)
        assert abs(rerun.best_similarity() - o[k]) < 1e-12, "re-run is not deterministic!"
        blk = pattern_block(rerun.best_valid.pattern, tgt, rerun.best_valid.fold_evaluation)
        blk["seed"] = seed
        blk["target_points"] = R(tgt.points, 2)
        blk["description"] = tgt.description
        out["targets"][tname] = blk

    # ---- candidate population demo (engine filtering, independent of the search)
    pop = generate_population(300, seed=7, invalid_fraction=0.5)
    eng = ConstraintEngine()
    counts = {"topology": 0, "geometry": 0, "maekawa": 0, "kawasaki": 0, "passed": 0}
    samples = []
    for i, p in enumerate(pop):
        rep = eng.evaluate(p, stop_early=True)
        counts["passed" if rep.passed else rep.rejected_at_stage] += 1
        if i < 36:
            samples.append({"pattern": p.to_dict(), "passed": rep.passed,
                            "stage": rep.rejected_at_stage, "why": first_failure_text(rep)})
    out["population_demo"] = {"n": len(pop), "seed": 7, "invalid_fraction_requested": 0.5,
                              "counts": counts, "samples": samples}

    # ---- unit test status (really executed now)
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=ROOT, capture_output=True, text=True)
    tail = (r.stderr or r.stdout).strip().splitlines()
    out["tests"] = {"ok": r.returncode == 0, "summary": " | ".join(tail[-3:])}

    path = os.path.join(ROOT, "results", "dashboard_data.json")
    json.dump(out, open(path, "w"))
    print("wrote", path, f"({os.path.getsize(path)/1024:.0f} KB)")
    print("population counts:", counts)
    print("tests:", out["tests"])


if __name__ == "__main__":
    main()
