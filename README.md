# ORIGEN: topology-constrained search for inverse origami design

A research prototype. Given a simple target shape, ORIGEN searches over crease patterns and uses
cheap mathematical and graph checks to discard invalid candidates before the expensive fold evaluation.

> **Necessary conditions are not physical foldability.** Maekawa and Kawasaki are necessary local conditions
> at a vertex. A pattern that passes them has **not** been proven to fold flat, to fold without
> self-intersection, or to be physically realisable. The fold evaluation in this repo is a simplified
> approximation, not a rigid-origami simulator.

## Live project screen

`docs/index.html` is a single self-contained page (crease plots, 3D fold view, experiment charts) built from
the recorded results. After pushing to GitHub it is served by GitHub Pages at
`https://<your-username>.github.io/<repo-name>/` (see "Publish on GitHub" below). Open it locally by
double-clicking the file; it only needs internet for the Google Fonts stylesheet and falls back to system fonts without it.

## The inverse origami problem

Forward: crease pattern → fold → 3D shape. Inverse: target shape → find a crease pattern that folds
towards it. The search space is huge and almost all of it is unfoldable, so a naive search spends most of
its evaluations on patterns that could never fold.

## Why a graph

A crease pattern is a planar graph: vertices are crease intersections, edges are creases carrying a
mountain/valley label. That makes connectivity, vertex degree, sector angles and per-vertex M/V counts
direct to compute, which is what the constraint engine needs. Backed by NetworkX (`core/crease_pattern.py`).

## The constraints (`constraints/`)

| Stage | Check | Status |
|---|---|---|
| topology | connected, no isolated vertices, no duplicate edges, interior degree ≥ 3 | exact graph checks |
| geometry | inside the sheet, positive length, no proper crossings | exact geometric checks |
| Maekawa | `|M − V| = 2` at each interior vertex | necessary, not sufficient |
| Kawasaki | alternating sector-angle sums equal (A + C = B + D for 4 creases; any even degree), tolerance 1e-6 rad | necessary, not sufficient |

`ConstraintEngine.evaluate` runs them cheapest-first and stops at the first failure
(`stop_early=True`). With `stop_early=False` it reports every failing stage.

## Search (`core/search.py`)

Simulated-annealing style Monte Carlo over single-hub star patterns. Moves: move a crease, flip M/V,
swap an M and a V, rotate an adjacent pair (keeps Kawasaki exactly), add or remove an M+V pair, re-space.
Some moves keep a pattern valid, some deliberately break it. Fitness (`core/scoring.py`) combines
constraint stage reached, shape similarity `1/(1+Chamfer)` and a placeholder structural term.

## Baselines and the experiment (`experiments/`)

Both baselines use the **same** operators, start generator and scoring terms. They run the fold evaluation on
every proposal first.

* `guided_unfiltered` (the main baseline): shape quality is the only objective. Invalid designs can enter the
  chain. Validity is checked afterwards and only valid designs count as results.
* `evaluate_then_reject` (control): evaluate first, then reject with ORIGEN's score. Its trajectory is
  identical to ORIGEN's by construction, so it isolates cost. Matching ORIGEN exactly is a wiring check.

Metrics (`experiments/metrics.py`): candidates generated, rejections per stage, shape evaluations,
runtime, valid-candidate rate, invalid candidates avoided, best valid similarity, iterations to best.
Run `python3 -m experiments.origen_experiment --trials 20 --iterations 200`; parameters and per-trial
raw metrics are written to `results/experiment_results.json`. Seeds are fixed and re-runs are deterministic.

### What the recorded run showed

20 seeds × 200 iterations × 3 targets, one machine, temperature 0.05. Means over targets, ORIGEN vs the
shape-guided baseline:

* shape evaluations: **28% fewer** (about 144 vs 201 per run); invalid candidates sent to evaluation: 0 vs about 140
* runtime: **27% lower** (the fold evaluator is cheap here; a heavy simulator would widen this)
* candidates passing every check: **72% vs 31%**
* best valid similarity: **0.674 vs 0.674**, no meaningful difference. Paired by seed ORIGEN scored
  higher in 32, tied in 2 and lower in 26 of 60 runs. No significance test was run.

So the hypothesis is supported for **less wasted exploration** and **not shown** for **better convergence
of final quality** in this setup. Regenerate the numbers yourself; do not treat these as general results.

## Run

```bash
pip install -r requirements.txt
python3 -m unittest discover -s tests          # 25 tests
python3 -m experiments.origen_experiment       # writes results/experiment_results.json
python3 experiments/export_dashboard_data.py   # re-runs best seeds, builds dashboard data
python3 visualization/build_project_screen.py  # writes results/origen_project_screen.html
streamlit run app.py                           # Streamlit UI (see status below)
```

## Publish on GitHub

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

Then in the repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**. The
`deploy project screen` workflow publishes `docs/` on every push to `main`, and the `tests` workflow runs the
unit tests. After changing code or re-running experiments, rebuild the page with
`python3 visualization/build_project_screen.py` and commit `docs/index.html`.
No license file is included; add one (for example MIT) before inviting reuse.

## Layout

`core/` graph model, targets, generator, scoring, search · `constraints/` the engine and its four checks ·
`simulation/folding.py` simplified fold model · `experiments/` baseline, ORIGEN runner, metrics, export ·
`visualization/` matplotlib plots and the project screen · `tests/` unit tests for the mathematical core.

## Limitations

* Single-hub star patterns only; no multi-vertex patterns yet.
* Fold model: rigid rods tilted by M/V sign with one global fold amount. No panels, no collisions, no layer ordering.
* Targets are small point clouds compared after centring and RMS scaling.
* One annealing temperature, no parameter sweep, no significance testing.
* `app.py` (Streamlit) was written but not executed where this was built.
* The generator's invalid modes are all caught by the topology stage before geometry, so the geometry stage is
  only exercised by its unit tests.

## Future work

Multi-vertex generation with local-to-global flat-foldability checks, a real rigid-origami or bar-and-hinge
simulator behind `simulation/folding.py`, richer targets, a learned (GNN) scorer as an optional component,
parameter sweeps and proper statistical tests.
