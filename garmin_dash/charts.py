"""Plotly figure builders. One fixed colour per metric family, single y-axis always."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .analytics import WEEKDAYS
from .data import METRICS

BLUE, ORANGE, AQUA, VIOLET, RED, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#e34948", "#8a8984"
COLOR = {
    "steps": BLUE, "distance_km": BLUE, "active_kcal": BLUE,
    "sleep_score": VIOLET, "sleep_hours": VIOLET, "deep_hours": VIOLET, "rem_hours": VIOLET, "bedtime_hour": VIOLET,
    "tonight_sleep_score": VIOLET, "tonight_sleep_hours": VIOLET,
    "resting_hr": RED, "max_hr": RED,
    "avg_stress": ORANGE, "max_stress": ORANGE, "high_stress_min": ORANGE,
    "body_battery_high": AQUA,
}


BAR_TRENDS = {"steps", "distance_km", "active_kcal", "high_stress_min"}


def _label(key: str) -> str:
    m = METRICS[key]
    return m.label if m.unit.lower() in m.label.lower() else f"{m.label} ({m.unit})"


def _layout(fig: go.Figure, title: str | None = None, height: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15)) if title else None,
        height=height, margin=dict(l=8, r=8, t=40 if title else 10, b=8),
        hovermode="x unified", showlegend=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


def trend(df: pd.DataFrame, col: str, days: int | None = None, height: int = 260) -> go.Figure:
    d = df if days is None else df[df["date"] > df["date"].max() - pd.Timedelta(days=days)]
    c = COLOR.get(col, BLUE)
    fig = go.Figure()
    if col in BAR_TRENDS:  # counts read well as bars from zero
        fig.add_bar(x=d["date"], y=d[col], marker_color=c, opacity=0.35, name="Daily",
                    hovertemplate="%{y:,.1f}<extra>Daily</extra>")
    else:  # levels like heart rate: dots, so the axis can zoom to the real range
        fig.add_scatter(x=d["date"], y=d[col], mode="markers", marker=dict(color=c, size=6, opacity=0.35),
                        name="Daily", hovertemplate="%{y:,.1f}<extra>Daily</extra>")
    roll = d[col].rolling(7, min_periods=4).mean()
    fig.add_scatter(x=d["date"], y=roll, mode="lines", line=dict(color=c, width=2.5), name="7-day avg",
                    hovertemplate="%{y:,.1f}<extra>7-day avg</extra>")
    fig.update_layout(bargap=0.15)
    return _layout(fig, METRICS[col].label, height)


def weekday_bars(df: pd.DataFrame, col: str, height: int = 260) -> go.Figure:
    wk = df.groupby("weekday")[col].mean().reindex(WEEKDAYS)
    fig = go.Figure(go.Bar(
        x=[w[:3] for w in WEEKDAYS], y=wk.values, marker_color=COLOR.get(col, BLUE),
        marker_cornerradius=4, text=[f"{v:,.0f}" if pd.notna(v) else "" for v in wk.values],
        textposition="outside", hovertemplate="%{x}: %{y:,.1f}<extra></extra>",
    ))
    fig = _layout(fig, f"{METRICS[col].label} by weekday", height)
    fig.update_layout(hovermode="closest")
    lo, hi = np.nanmin(wk.values), np.nanmax(wk.values)
    fig.update_yaxes(range=[max(0, lo - (hi - lo) * 1.5), hi + (hi - lo) * 0.6])
    return fig


def sleep_stages(df: pd.DataFrame, nights: int = 30, height: int = 300) -> go.Figure:
    d = df.dropna(subset=["sleep_hours"]).tail(nights)
    fig = go.Figure()
    # Sequential violet ramp: deep (darkest) -> awake (lightest).
    for col, name, color in [("deep_hours", "Deep", "#2d2380"), ("rem_hours", "REM", "#6a5bd1"),
                             ("light_hours", "Light", "#a79ff0"), ("awake_hours", "Awake", "#d9d5fa")]:
        if col in d:
            fig.add_bar(x=d["date"], y=d[col], name=name, marker_color=color,
                        marker_line=dict(width=0), hovertemplate=f"{name}: %{{y:.1f}} h<extra></extra>")
    fig = _layout(fig, f"Sleep stages, last {nights} nights (hours)", height)
    fig.update_layout(barmode="stack", bargap=0.2, showlegend=True,
                      legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    return fig


def correlation_heatmap(df: pd.DataFrame, cols: list[str], height: int = 420) -> go.Figure:
    c = df[cols].corr().round(2)
    labels = [METRICS[k].label for k in cols]
    fig = go.Figure(go.Heatmap(
        z=c.values, x=labels, y=labels, zmin=-1, zmax=1,
        # Diverging: red (negative) - neutral gray - blue (positive).
        colorscale=[[0, "#c0392b"], [0.5, "#e8e8e6"], [1, "#1f5fae"]],
        text=c.values, texttemplate="%{text:.2f}", textfont=dict(size=11),
        hovertemplate="%{y} vs %{x}: r = %{z:.2f}<extra></extra>", xgap=2, ygap=2,
        colorbar=dict(title="r", thickness=10),
    ))
    fig = _layout(fig, "How your metrics move together (correlation)", height)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(tickangle=-35)
    fig.update_yaxes(autorange="reversed", gridcolor=None)
    return fig


def scatter(df: pd.DataFrame, x: str, y: str, title: str | None = None, height: int = 380) -> go.Figure:
    d = df[["date", x, y]].dropna()
    fig = go.Figure(go.Scatter(
        x=d[x], y=d[y], mode="markers",
        marker=dict(size=9, color=COLOR.get(y, BLUE), opacity=0.7, line=dict(width=1, color="white")),
        customdata=d["date"].dt.strftime("%b %d, %Y"),
        hovertemplate="%{customdata}<br>" + METRICS[x].label + ": %{x:,.1f}<br>" + METRICS[y].label + ": %{y:,.1f}<extra></extra>",
    ))
    if len(d) >= 5:
        slope, icpt = np.polyfit(d[x], d[y], 1)
        xs = np.linspace(d[x].min(), d[x].max(), 50)
        fig.add_scatter(x=xs, y=slope * xs + icpt, mode="lines", line=dict(color=GRAY, width=2, dash="dash"),
                        hoverinfo="skip", name="Trend")
    fig = _layout(fig, title, height)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title=_label(x), showgrid=True, gridcolor="rgba(128,128,128,0.18)")
    fig.update_yaxes(title=_label(y))
    return fig


def over_time_indexed(df: pd.DataFrame, x: str, y: str, title: str | None = None, height: int = 380) -> go.Figure:
    """Two metrics over time on ONE axis: each as a 7-day average indexed to its own mean (100 = typical)."""
    fig = go.Figure()
    for col, color in ((x, BLUE), (y, ORANGE if COLOR.get(y) != ORANGE else VIOLET)):
        roll = df[col].rolling(7, min_periods=4).mean()
        idx = roll / df[col].mean() * 100
        fig.add_scatter(x=df["date"], y=idx, mode="lines", line=dict(color=color, width=2.5), name=METRICS[col].label,
                        customdata=roll, hovertemplate=METRICS[col].label + ": %{customdata:,.1f} (index %{y:.0f})<extra></extra>")
    fig.add_hline(y=100, line=dict(color=GRAY, width=1, dash="dot"))
    fig = _layout(fig, title, height)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    fig.update_yaxes(title="7-day avg, % of your typical")
    return fig


def bucket_bars(df: pd.DataFrame, x: str, y: str, title: str | None = None, height: int = 380) -> go.Figure:
    """Average y within quartile buckets of x."""
    d = df[[x, y]].dropna()
    q = pd.qcut(d[x], 4, duplicates="drop")
    g = d.groupby(q, observed=True)[y].agg(["mean", "size"])
    xf = METRICS[x].fmt
    labels = [f"{xf.format(iv.left)}–{xf.format(iv.right)}" for iv in g.index]
    fig = go.Figure(go.Bar(
        x=labels, y=g["mean"], marker_color=COLOR.get(y, BLUE), marker_cornerradius=4,
        text=[f"{v:,.1f}" for v in g["mean"]], textposition="outside",
        customdata=g["size"], hovertemplate="%{x}<br>avg %{y:,.1f} over %{customdata} days<extra></extra>",
    ))
    fig = _layout(fig, title, height)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title=_label(x) + ", grouped into quarters")
    fig.update_yaxes(title="Average " + _label(y))
    return fig


def weekday_pair(df: pd.DataFrame, x: str, y: str, title: str | None = None, height: int = 380) -> go.Figure:
    """Weekday profile of both metrics, each indexed to its own mean so they share one axis."""
    fig = go.Figure()
    for col, color in ((x, BLUE), (y, ORANGE if COLOR.get(y) != ORANGE else VIOLET)):
        wk = df.groupby("weekday")[col].mean().reindex(WEEKDAYS)
        fig.add_bar(x=[w[:3] for w in WEEKDAYS], y=wk / df[col].mean() * 100, name=METRICS[col].label,
                    marker_color=color, marker_cornerradius=4, customdata=wk,
                    hovertemplate=METRICS[col].label + ": %{customdata:,.1f}<extra></extra>")
    fig.add_hline(y=100, line=dict(color=GRAY, width=1, dash="dot"))
    fig = _layout(fig, title, height)
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08, showlegend=True,
                      legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    fig.update_yaxes(title="% of your typical")
    return fig
