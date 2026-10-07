"""Generate a synthetic daily table so the dashboard runs without a Garmin login.

The numbers are made up but have realistic structure: weekday/weekend rhythms,
a slow fitness trend, missing days, and sleep that responds to the previous
day's steps and stress. Run directly to (re)write data/sample_daily.csv.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "data" / "sample_daily.csv"


def build(days: int = 240, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = date.today() - timedelta(days=1)
    dates = pd.date_range(end - timedelta(days=days - 1), end, freq="D")
    n = len(dates)
    t = np.arange(n) / n
    weekend = dates.dayofweek >= 5
    friday = dates.dayofweek == 4

    steps = rng.lognormal(np.log(8200), 0.38, n) * np.where(weekend, 1.15, 1.0) * (0.92 + 0.15 * t)
    steps[rng.random(n) < 0.08] *= 1.8  # occasional long hike/run day
    steps = np.clip(steps, 900, 32000).round()

    stress = np.clip(rng.normal(34, 7, n) + np.where(weekend, -7, 3) - 4 * t, 12, 75).round()
    resting_hr = np.clip(rng.normal(58, 1.6, n) - 3.0 * t + 0.08 * (stress - 30), 47, 72).round()

    # Sleep for the night AFTER each day, driven by that day's steps & stress.
    k_steps = steps / 1000
    tonight_score = (
        52 + 3.1 * k_steps - 0.11 * k_steps**2 - 0.42 * (stress - 30)
        + np.where(friday, -6, 0) + rng.normal(0, 7.5, n)
    )
    tonight_score = np.clip(tonight_score, 25, 98).round()
    tonight_hours = np.clip(5.4 + 0.032 * tonight_score + rng.normal(0, 0.45, n), 3.8, 9.8)
    bedtime = np.clip(22.8 + np.where(friday | (dates.dayofweek == 5), 1.1, 0) + rng.normal(0, 0.5, n), 21, 26.5)

    # Garmin dates sleep by wake-up day, so shift forward one day.
    sleep_score = np.roll(tonight_score, 1).astype(float)
    sleep_hours = np.roll(tonight_hours, 1)
    bedtime_hour = np.roll(bedtime, 1)
    sleep_score[0] = sleep_hours[0] = bedtime_hour[0] = np.nan

    deep = sleep_hours * np.clip(rng.normal(0.17, 0.03, n) + 0.0008 * (sleep_score - 70), 0.08, 0.3)
    rem = sleep_hours * np.clip(rng.normal(0.22, 0.03, n), 0.1, 0.32)
    awake = np.clip(rng.normal(0.35, 0.15, n), 0.05, 1.2)
    light = sleep_hours - deep - rem

    df = pd.DataFrame({
        "date": dates.date,
        "steps": steps,
        "distance_km": (steps * 0.00076).round(2),
        "active_kcal": (steps * 0.042 + rng.normal(0, 60, n)).clip(50).round(),
        "resting_hr": resting_hr,
        "min_hr": resting_hr - rng.integers(2, 6, n),
        "max_hr": np.clip(105 + steps / 400 + rng.normal(0, 10, n), 95, 188).round(),
        "avg_stress": stress,
        "max_stress": np.clip(stress + rng.normal(52, 8, n), 60, 99).round(),
        "high_stress_min": np.clip((stress - 22) * 4 + rng.normal(0, 15, n), 0, None).round(),
        "body_battery_high": np.clip(35 + 0.6 * sleep_score + rng.normal(0, 6, n), 20, 100).round(),
        "body_battery_low": np.clip(rng.normal(18, 6, n), 5, 40).round(),
        "sleep_score": sleep_score,
        "sleep_hours": sleep_hours.round(2),
        "deep_hours": deep.round(2),
        "light_hours": light.round(2),
        "rem_hours": rem.round(2),
        "awake_hours": awake.round(2),
        "bedtime_hour": bedtime_hour.round(2),
    })
    # A few nights the watch was off, a few days it wasn't worn.
    df.loc[rng.random(n) < 0.04, ["sleep_score", "sleep_hours", "deep_hours", "light_hours", "rem_hours", "awake_hours", "bedtime_hour"]] = np.nan
    df.loc[rng.random(n) < 0.02, ["steps", "distance_km", "active_kcal"]] = np.nan
    return df


def write_sample(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build().to_csv(path, index=False)
    return path


if __name__ == "__main__":
    print(f"Wrote {write_sample()}")
