"""Loading the daily table and describing its metrics.

The daily table has one row per calendar day. Sleep columns describe the night
that ENDED on that morning (this is how Garmin dates sleep). Derived
``tonight_*`` columns shift sleep back one day, so a row's steps and stress
line up with the sleep that followed them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REAL_CSV = DATA_DIR / "garmin_daily.csv"
SAMPLE_CSV = DATA_DIR / "sample_daily.csv"


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    unit: str
    description: str
    fmt: str = "{:,.0f}"
    higher_is_better: bool | None = True


METRICS: dict[str, Metric] = {m.key: m for m in [
    Metric("steps", "Steps", "steps", "Total steps walked that day"),
    Metric("distance_km", "Distance", "km", "Distance covered that day", "{:,.1f}"),
    Metric("active_kcal", "Active calories", "kcal", "Calories burned through activity that day"),
    Metric("resting_hr", "Resting heart rate", "bpm", "Resting heart rate for the day", higher_is_better=False),
    Metric("max_hr", "Max heart rate", "bpm", "Highest heart rate recorded that day", higher_is_better=None),
    Metric("avg_stress", "Average stress", "0-100", "Garmin all-day average stress level", "{:,.1f}", higher_is_better=False),
    Metric("max_stress", "Peak stress", "0-100", "Highest stress level that day", higher_is_better=False),
    Metric("high_stress_min", "High-stress minutes", "min", "Minutes spent in high stress that day", higher_is_better=False),
    Metric("body_battery_high", "Body Battery peak", "0-100", "Highest Body Battery that day"),
    Metric("sleep_score", "Sleep score (last night)", "0-100", "Garmin sleep score for the night before this day"),
    Metric("sleep_hours", "Sleep duration (last night)", "h", "Hours slept the night before this day", "{:,.1f}"),
    Metric("deep_hours", "Deep sleep (last night)", "h", "Hours of deep sleep the night before", "{:,.1f}"),
    Metric("rem_hours", "REM sleep (last night)", "h", "Hours of REM sleep the night before", "{:,.1f}"),
    Metric("bedtime_hour", "Bedtime (last night)", "hour", "Clock hour sleep started, 22 = 10pm, 25 = 1am", "{:,.1f}", None),
    Metric("tonight_sleep_score", "Sleep score (that night)", "0-100", "Sleep score for the night AFTER this day; pair with same-day steps or stress"),
    Metric("tonight_sleep_hours", "Sleep duration (that night)", "h", "Hours slept the night AFTER this day", "{:,.1f}"),
]}

# Columns written by fetch_garmin.py / make_sample_data.py, in order.
RAW_COLUMNS = [
    "date", "steps", "distance_km", "active_kcal", "resting_hr", "min_hr", "max_hr",
    "avg_stress", "max_stress", "high_stress_min", "body_battery_high", "body_battery_low",
    "sleep_score", "sleep_hours", "deep_hours", "light_hours", "rem_hours", "awake_hours",
    "bedtime_hour",
]


def load_daily() -> tuple[pd.DataFrame, str]:
    """Return (daily table, source label). Prefers real cached Garmin data."""
    if REAL_CSV.exists():
        path, source = REAL_CSV, "Garmin Connect"
    elif SAMPLE_CSV.exists():
        path, source = SAMPLE_CSV, "sample data"
    else:
        from make_sample_data import write_sample  # lazy: only when nothing exists
        write_sample(SAMPLE_CSV)
        path, source = SAMPLE_CSV, "sample data"

    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    # Reindex to a continuous calendar so shifting by one row means one day.
    full = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    df = df.set_index("date").reindex(full).rename_axis("date").reset_index()
    df["tonight_sleep_score"] = df["sleep_score"].shift(-1)
    df["tonight_sleep_hours"] = df["sleep_hours"].shift(-1)
    df["weekday"] = df["date"].dt.day_name()
    # Garmin reports 0 steps for days the watch wasn't worn; treat as missing.
    df.loc[df["steps"] <= 0, "steps"] = pd.NA
    return df, source


def available_metrics(df: pd.DataFrame, min_points: int = 10) -> list[str]:
    return [k for k in METRICS if k in df and df[k].notna().sum() >= min_points]


def with_unit(metric_key: str, value) -> str:
    """Formatted value plus unit, skipping units that read badly inline (e.g. 0-100)."""
    unit = METRICS[metric_key].unit
    return fmt(metric_key, value) + ("" if unit in ("0-100", "hour") else f" {unit}")


def fmt(metric_key: str, value) -> str:
    if value is None or pd.isna(value):
        return "–"
    return METRICS[metric_key].fmt.format(value)
