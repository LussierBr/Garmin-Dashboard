"""Plain-pandas analytics used by the dashboard and the Ask tab."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import with_unit

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def window_compare(df: pd.DataFrame, col: str, days: int = 30) -> tuple[float, float]:
    """Mean over the last `days` vs the `days` before that."""
    end = df["date"].max()
    cur = df.loc[df["date"] > end - pd.Timedelta(days=days), col].mean()
    prev = df.loc[(df["date"] <= end - pd.Timedelta(days=days)) & (df["date"] > end - pd.Timedelta(days=2 * days)), col].mean()
    return cur, prev


def pair_stats(df: pd.DataFrame, x: str, y: str) -> dict:
    """Correlation, slope and tercile means for y against x."""
    d = df[[x, y]].dropna()
    n = len(d)
    if n < 5:
        return {"n": n}
    r = d[x].corr(d[y])
    rho = d[x].corr(d[y], method="spearman")
    slope, intercept = np.polyfit(d[x], d[y], 1)
    terciles = pd.qcut(d[x], 3, labels=["low", "mid", "high"], duplicates="drop")
    groups = d.groupby(terciles, observed=True).agg(x_min=(x, "min"), x_max=(x, "max"), y_mean=(y, "mean"), n=(y, "size"))
    return {
        "n": n,
        "pearson_r": round(float(r), 3),
        "spearman_rho": round(float(rho), 3),
        "r_squared": round(float(r**2), 3),
        "slope_per_unit_x": float(slope),
        "x_mean": float(d[x].mean()),
        "y_mean": float(d[y].mean()),
        "tercile_means": {
            str(k): {"x_range": [round(float(v.x_min), 2), round(float(v.x_max), 2)], "y_mean": round(float(v.y_mean), 2), "days": int(v.n)}
            for k, v in groups.iterrows()
        },
    }


def strength_word(r: float) -> str:
    a = abs(r)
    return "very weak" if a < 0.1 else "weak" if a < 0.3 else "moderate" if a < 0.5 else "strong"


def streaks(series: pd.Series) -> tuple[int, int]:
    """(current streak, longest streak) of consecutive True values."""
    longest = cur = 0
    for v in series.fillna(False):
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    return cur, longest


def notable_days(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """(label, date, value text) for standout days."""
    out = []
    picks = [
        ("Most steps", "steps", "max"),
        ("Best sleep score", "sleep_score", "max"),
        ("Worst sleep score", "sleep_score", "min"),
        ("Most stressful day", "avg_stress", "max"),
        ("Calmest day", "avg_stress", "min"),
        ("Lowest resting HR", "resting_hr", "min"),
    ]
    for label, col, how in picks:
        s = df[col].dropna()
        if s.empty:
            continue
        idx = s.idxmax() if how == "max" else s.idxmin()
        out.append((label, df.loc[idx, "date"].strftime("%a %b %d, %Y"), with_unit(col, s[idx])))
    return out


def insights(df: pd.DataFrame) -> list[str]:
    """Short, data-backed sentences for the dashboard."""
    out: list[str] = []

    d = df[["steps", "tonight_sleep_score"]].dropna()
    if len(d) >= 20:
        hi = d.loc[d["steps"] >= 10000, "tonight_sleep_score"]
        lo = d.loc[d["steps"] < 10000, "tonight_sleep_score"]
        if len(hi) >= 5 and len(lo) >= 5:
            diff = hi.mean() - lo.mean()
            out.append(
                f"On days you walk 10,000+ steps, your sleep score that night averages **{hi.mean():.0f}** "
                f"vs **{lo.mean():.0f}** on other days ({diff:+.0f} points, {len(hi)} vs {len(lo)} days)."
            )

    d = df[["avg_stress", "tonight_sleep_score"]].dropna()
    if len(d) >= 20:
        r = d["avg_stress"].corr(d["tonight_sleep_score"])
        q = d["avg_stress"].quantile([0.25, 0.75])
        calm = d.loc[d["avg_stress"] <= q.iloc[0], "tonight_sleep_score"].mean()
        tense = d.loc[d["avg_stress"] >= q.iloc[1], "tonight_sleep_score"].mean()
        out.append(
            f"Stress and that night's sleep have a {strength_word(r)} {'negative' if r < 0 else 'positive'} link (r = {r:.2f}): "
            f"your calmest quarter of days are followed by sleep scores around **{calm:.0f}**, your most stressed quarter by **{tense:.0f}**."
        )

    wk = df.dropna(subset=["steps"]).groupby("weekday")["steps"].mean().reindex(WEEKDAYS)
    if wk.notna().sum() >= 5:
        out.append(f"You're most active on **{wk.idxmax()}s** ({wk.max():,.0f} steps on average) and least on **{wk.idxmin()}s** ({wk.min():,.0f}).")

    ws = df.dropna(subset=["sleep_score"]).groupby(df["date"].dt.dayofweek)["sleep_score"].mean()
    if len(ws) == 7:
        # sleep_score on day D is the night before D, so name the night.
        night = {i: WEEKDAYS[(i - 1) % 7] for i in range(7)}
        out.append(f"Your best nights are usually **{night[ws.idxmax()]} nights** (avg score {ws.max():.0f}); the worst are **{night[ws.idxmin()]} nights** ({ws.min():.0f}).")

    if df["resting_hr"].notna().sum() >= 60:
        first = df["resting_hr"].dropna().head(30).mean()
        last = df["resting_hr"].dropna().tail(30).mean()
        if abs(last - first) >= 1:
            direction = "down" if last < first else "up"
            out.append(f"Resting heart rate is **{direction} {abs(last - first):.1f} bpm** comparing your first and latest 30 days ({first:.1f} → {last:.1f}).")

    cur, longest = streaks(df["steps"] >= 10000)
    out.append(f"10k-step streak: **{cur} day{'s' if cur != 1 else ''}** right now, longest **{longest}**.")
    return out
