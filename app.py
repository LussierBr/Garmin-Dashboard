"""Brody's Garmin health dashboard.  Run:  streamlit run app.py"""
from __future__ import annotations

import os

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from garmin_dash import analytics, charts
from garmin_dash.ask import answer
from garmin_dash.data import METRICS, available_metrics, fmt, load_daily
from garmin_dash.predict import EXTRA_FEATURES, fit

st.set_page_config(page_title="Garmin Health", page_icon="❤️", layout="wide")


@st.cache_data(ttl=600)
def get_data():
    return load_daily()


df, source = get_data()
metric_keys = available_metrics(df)

st.title("Garmin Health")
st.caption(
    f"{source} · {df['date'].min():%b %d, %Y} to {df['date'].max():%b %d, %Y} · {len(df)} days"
    + (" · run `python fetch_garmin.py` to load your real data" if source == "sample data" else "")
)

tab_dash, tab_ask, tab_predict = st.tabs(["Dashboard", "Ask your data", "Sleep predictor"])

# ---------------------------------------------------------------- Dashboard --
with tab_dash:
    window = st.segmented_control("Period", ["30 days", "90 days", "All"], default="90 days", key="period")
    days = {"30 days": 30, "90 days": 90, "All": None}[window or "90 days"]

    st.subheader("Last 30 days vs the 30 before")
    kpis = [("steps", "Avg steps"), ("sleep_score", "Avg sleep score"), ("resting_hr", "Resting HR"), ("avg_stress", "Avg stress")]
    for col, (key, label) in zip(st.columns(4), kpis):
        cur, prev = analytics.window_compare(df, key)
        m = METRICS[key]
        delta = None if np.isnan(prev) else cur - prev
        col.metric(
            label, f"{fmt(key, cur)} {m.unit if m.unit not in ('steps', '0-100') else ''}".strip(),
            None if delta is None else (f"{delta:+,.0f}" if abs(delta) >= 100 else f"{delta:+.1f}"),
            delta_color="normal" if m.higher_is_better else "inverse",
            border=True,
        )

    st.subheader("What stands out")
    for line in analytics.insights(df):
        st.markdown(f"- {line}")

    st.subheader("Trends")
    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.trend(df, "steps", days), width="stretch")
    c2.plotly_chart(charts.trend(df, "sleep_score", days), width="stretch")
    c3, c4 = st.columns(2)
    c3.plotly_chart(charts.trend(df, "resting_hr", days), width="stretch")
    c4.plotly_chart(charts.trend(df, "avg_stress", days), width="stretch")
    st.caption("Faint bars and dots are daily values; the line is the 7-day average.")

    st.subheader("Sleep")
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(charts.sleep_stages(df, 30), width="stretch")
    with c2:
        last = df.dropna(subset=["sleep_hours"]).tail(30)
        st.metric("Avg sleep (30 nights)", f"{last['sleep_hours'].mean():.1f} h", border=True)
        st.metric("Avg deep sleep", f"{last['deep_hours'].mean():.1f} h ({(last['deep_hours'] / last['sleep_hours']).mean():.0%})", border=True)
        if "bedtime_hour" in last and last["bedtime_hour"].notna().any():
            b = last["bedtime_hour"].mean() % 24
            st.metric("Typical bedtime", f"{int(b) % 12 or 12}:{int((b % 1) * 60):02d} {'pm' if 12 <= b < 24 else 'am'}", border=True)

    st.subheader("Weekly rhythm")
    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.weekday_bars(df, "steps"), width="stretch")
    c2.plotly_chart(charts.weekday_bars(df, "avg_stress"), width="stretch")

    st.subheader("Connections")
    corr_cols = [k for k in ["steps", "active_kcal", "avg_stress", "resting_hr", "body_battery_high",
                             "sleep_score", "tonight_sleep_score", "tonight_sleep_hours"] if k in metric_keys]
    st.plotly_chart(charts.correlation_heatmap(df, corr_cols), width="stretch")
    st.caption("Blue = rise together, red = one rises as the other falls. \"That night\" sleep lines up with the same day's activity.")

    st.subheader("Notable days")
    nd = analytics.notable_days(df)
    for col, (label, day, val) in zip(st.columns(3) * 2, nd):
        with col.container(border=True):
            st.caption(label)
            st.markdown(f"### {val}")
            st.caption(day)

    with st.expander("Data table"):
        st.dataframe(df.sort_values("date", ascending=False), width="stretch", hide_index=True)

# --------------------------------------------------------------------- Ask --
with tab_ask:
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    st.markdown("Ask to compare two things and get a chart plus a short explanation.")
    if not has_key:
        st.info("Running in offline mode with keyword matching. Set `ANTHROPIC_API_KEY` to let Claude interpret questions and write the explanations.")

    examples = [
        "Do more steps help me sleep better that night?",
        "How does stress relate to my resting heart rate?",
        "Show steps and sleep score over time",
        "Compare my stress and steps by day of the week",
    ]
    ex_cols = st.columns(len(examples))
    clicked = None
    for c, ex in zip(ex_cols, examples):
        if c.button(ex, width="stretch"):
            clicked = ex

    if "history" not in st.session_state:
        st.session_state.history = []

    for i, item in enumerate(st.session_state.history):
        with st.chat_message("user"):
            st.markdown(item["q"])
        with st.chat_message("assistant"):
            if "error" in item:
                st.error(item["error"])
            else:
                st.plotly_chart(item["a"].figure, width="stretch", key=f"ask_{i}")
                st.markdown(item["a"].explanation)

    q = st.chat_input("e.g. Does stress affect how long I sleep?") or clicked
    if q:
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    a = answer(q, df, metric_keys)
                    st.session_state.history.append({"q": q, "a": a})
                except Exception as e:  # show API/network errors in the chat rather than crashing
                    st.session_state.history.append({"q": q, "error": f"Couldn't answer that: {type(e).__name__}: {e}"})
        st.rerun()

    if st.session_state.history and st.button("Clear conversation"):
        st.session_state.history = []
        st.rerun()

# ----------------------------------------------------------------- Predict --
with tab_predict:
    st.markdown("Enter a step count to predict your sleep score that night, based on your own history.")
    extras = st.multiselect("Also account for", list(EXTRA_FEATURES), format_func=EXTRA_FEATURES.get,
                            help="Optional. When left at their defaults these use your typical values.")
    model = fit(df, extras)
    if model is None:
        st.warning("Not enough nights with both steps and a sleep score yet (need at least 30).")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            steps = st.number_input("Steps today", 0, 60000, int(round(model.medians["steps"], -2)), step=500)
            extra_vals = {}
            if "avg_stress" in extras:
                extra_vals["avg_stress"] = st.slider("Average stress today", 0, 100, int(model.medians["avg_stress"]))
            if "sleep_score" in extras:
                extra_vals["sleep_score"] = st.slider("Last night's sleep score", 0, 100, int(model.medians["sleep_score"]))
            p = model.predict(steps, **extra_vals)
            st.metric("Predicted sleep score", f"{p['mean']:.0f}", border=True)
            st.markdown(f"80% of nights like this land between **{p['low']:.0f}** and **{p['high']:.0f}**.")
            if p["extrapolating"]:
                st.warning(f"{steps:,} steps is outside the range you usually walk "
                           f"({model.step_range[0]:,.0f}–{model.step_range[1]:,.0f}), so treat this as a rough guess.")

        with c2:
            cur = model.curve()
            obs = df[["steps", "tonight_sleep_score"]].dropna()
            fig = go.Figure()
            fig.add_scatter(x=cur["steps"], y=cur["high"], mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
            fig.add_scatter(x=cur["steps"], y=cur["low"], mode="lines", line=dict(width=0), fill="tonexty",
                            fillcolor="rgba(74,58,167,0.15)", name="80% range", hoverinfo="skip")
            fig.add_scatter(x=obs["steps"], y=obs["tonight_sleep_score"], mode="markers", name="Your nights",
                            marker=dict(size=7, color=charts.GRAY, opacity=0.45),
                            hovertemplate="%{x:,.0f} steps → %{y:.0f}<extra></extra>")
            fig.add_scatter(x=cur["steps"], y=cur["mean"], mode="lines", name="Prediction",
                            line=dict(color=charts.VIOLET, width=2.5), hovertemplate="%{x:,.0f} steps → %{y:.0f}<extra></extra>")
            fig.add_scatter(x=[steps], y=[p["mean"]], mode="markers", name="Your input",
                            marker=dict(size=14, color=charts.ORANGE, line=dict(width=2, color="white")),
                            hovertemplate="%{x:,.0f} steps → %{y:.0f}<extra></extra>")
            if extras:
                fig.add_annotation(text="curve holds other inputs at your typical values", x=1, y=0, xref="paper",
                                   yref="paper", showarrow=False, font=dict(size=11), xanchor="right", yanchor="bottom")
            fig.update_layout(height=420, margin=dict(l=8, r=8, t=10, b=8), hovermode="closest",
                              legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
            fig.update_xaxes(title="Steps that day")
            fig.update_yaxes(title="Sleep score that night", gridcolor="rgba(128,128,128,0.18)")
            st.plotly_chart(fig, width="stretch")

        st.subheader("How much to trust this")
        m1, m2, m3 = st.columns(3)
        m1.metric("Nights used", f"{model.n}", border=True)
        m2.metric("Variation explained (R²)", f"{model.r2:.0%}", border=True)
        better = model.baseline_mae - model.holdout_mae
        m3.metric("Typical error on recent nights", f"±{model.holdout_mae:.1f} pts",
                  f"{abs(better):.1f} pts {'better' if better >= 0 else 'worse'} than guessing your average",
                  delta_color="normal" if better >= 0 else "inverse", border=True)
        st.caption(
            "Linear regression with a curved step term (more steps can help up to a point). "
            "The error check trains on your earlier 80% of nights and tests on the most recent 20%. "
            "Lots of things affect sleep that steps don't capture, so expect individual nights to vary."
        )
