"""
app.py - Streamlit interface for ORIGEN.

    pip install -r requirements.txt
    streamlit run app.py

STATUS: written but NOT executed in the sandbox it was authored in (Streamlit could
not be installed there). The core modules it calls are tested; the UI layer is not.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from core.targets import get_target, TARGET_REGISTRY
from core.candidate_generator import generate_population
from core.search import run_origen_search
from constraints.engine import ConstraintEngine
from experiments.baseline import run_baseline_search
from visualization.crease_plot import plot_crease_pattern, plot_folded
from visualization.results_plot import load_results, plot_convergence, plot_metric_bars

st.set_page_config(page_title="ORIGEN", layout="wide")
st.title("ORIGEN: topology-constrained inverse origami search")
st.warning("Maekawa and Kawasaki are necessary conditions only. The fold view is a simplified rod model, "
           "not a rigid-origami simulation. Passing the checks does not prove physical foldability.")

target_name = st.sidebar.selectbox("Target shape", list(TARGET_REGISTRY), index=2)
target = get_target(target_name)
tab1, tab2, tab3 = st.tabs(["Generate & filter", "Run search", "Recorded experiment"])

with tab1:
    n = st.slider("Candidates", 20, 400, 120)
    frac = st.slider("Fraction deliberately invalid", 0.0, 1.0, 0.5)
    seed = st.number_input("Seed", 0, 10_000, 7)
    pop = generate_population(n, invalid_fraction=frac, seed=int(seed))
    eng = ConstraintEngine()
    reps = [eng.evaluate(p) for p in pop]
    counts = pd.Series([r.rejected_at_stage or "passed" for r in reps]).value_counts()
    st.bar_chart(counts)
    show = st.radio("Show", ["all", "passed", "rejected"], horizontal=True)
    idx = [i for i, r in enumerate(reps) if show == "all" or (show == "passed") == r.passed][:12]
    cols = st.columns(4)
    for k, i in enumerate(idx):
        fig, ax = plt.subplots(figsize=(2.2, 2.2))
        plot_crease_pattern(pop[i], ax, f"#{i} " + ("PASS" if reps[i].passed else f"FAIL: {reps[i].rejected_at_stage}"))
        cols[k % 4].pyplot(fig)
        plt.close(fig)

with tab2:
    iters = st.slider("Iterations", 50, 500, 200)
    s = st.number_input("Search seed", 0, 10_000, 0)
    if st.button("Run ORIGEN and baseline"):
        o = run_origen_search(target, iters, int(s))
        b = run_baseline_search(target, iters, int(s))
        st.dataframe(pd.DataFrame({"ORIGEN": o.stats.to_dict(), "Baseline": b.stats.to_dict()}).astype(str))
        c1, c2 = st.columns(2)
        if o.best_valid:
            fig, ax = plt.subplots(figsize=(4, 4))
            plot_crease_pattern(o.best_valid.pattern, ax, f"ORIGEN best, similarity {o.best_similarity():.3f}")
            c1.pyplot(fig)
            c2.pyplot(plot_folded(o.best_valid.pattern, target, o.best_valid.fold_evaluation.best_fold_amount).figure)
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(o.stats.best_valid_similarity_history, label="ORIGEN")
        ax.plot(b.stats.best_valid_similarity_history, label="Baseline")
        ax.legend()
        st.pyplot(fig)

with tab3:
    res = load_results()
    if res is None:
        st.info("Experiment results are unavailable: run `python3 -m experiments.origen_experiment` first.")
    else:
        st.json(res["parameters"])
        st.pyplot(plot_convergence(res, target_name))
        st.pyplot(plot_convergence(res, target_name, vs_evals=True))
        st.pyplot(plot_metric_bars(res, target_name, "n_shape_evaluations", "Shape evaluations per run"))
