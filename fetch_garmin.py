"""Download daily Garmin Connect data and cache it locally.

Credentials come ONLY from environment variables, never from this file:
    GARMIN_EMAIL, GARMIN_PASSWORD

After the first login, session tokens are saved to ~/.garminconnect (or
$GARMINTOKENS), so later runs don't need the password or an MFA code.

Raw API responses are cached one file per day in data/raw/, so re-running only
downloads days that are new (plus the last two days, which may have changed).
The flattened table is written to data/garmin_daily.csv, which the app uses
automatically in place of the sample data.

Usage:
    python fetch_garmin.py            # last 180 days
    python fetch_garmin.py --days 365
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
OUT_CSV = ROOT / "data" / "garmin_daily.csv"
TOKENSTORE = os.getenv("GARMINTOKENS", "~/.garminconnect")


def connect():
    from garminconnect import Garmin

    email, password = os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD")
    client = Garmin(email, password, prompt_mfa=lambda: input("Garmin MFA code: ").strip())
    try:
        # Uses saved tokens if present, otherwise logs in with the env-var credentials.
        client.login(TOKENSTORE)
    except Exception as e:  # library raises several auth/connection types
        if not (email and password):
            sys.exit("No saved Garmin session. Set GARMIN_EMAIL and GARMIN_PASSWORD and try again.")
        sys.exit(f"Garmin login failed: {type(e).__name__}: {e}")
    return client


def fetch_day(client, day: str) -> dict:
    out = {}
    for key, call in (("summary", client.get_user_summary), ("sleep", client.get_sleep_data)):
        try:
            out[key] = call(day)
        except Exception as e:
            out[key] = None
            print(f"  {day}: could not fetch {key} ({type(e).__name__})")
    return out


def _hours(seconds):
    return round(seconds / 3600, 2) if seconds else None


def flatten(day: str, raw: dict) -> dict:
    s = raw.get("summary") or {}
    sleep = (raw.get("sleep") or {}).get("dailySleepDTO") or {}
    score = (((sleep.get("sleepScores") or {}).get("overall")) or {}).get("value")

    bedtime = None
    if sleep.get("sleepStartTimestampLocal"):
        start = datetime.fromtimestamp(sleep["sleepStartTimestampLocal"] / 1000, tz=timezone.utc)
        bedtime = start.hour + start.minute / 60
        if bedtime < 12:  # after midnight -> 24+ so bedtimes sort sensibly
            bedtime += 24

    dist = s.get("totalDistanceMeters")
    high_stress = s.get("highStressDuration")
    return {
        "date": day,
        "steps": s.get("totalSteps"),
        "distance_km": round(dist / 1000, 2) if dist else None,
        "active_kcal": s.get("activeKilocalories"),
        "resting_hr": s.get("restingHeartRate"),
        "min_hr": s.get("minHeartRate"),
        "max_hr": s.get("maxHeartRate"),
        # Garmin uses -1/-2 for "not enough data".
        "avg_stress": s.get("averageStressLevel") if (s.get("averageStressLevel") or -1) >= 0 else None,
        "max_stress": s.get("maxStressLevel") if (s.get("maxStressLevel") or -1) >= 0 else None,
        "high_stress_min": round(high_stress / 60) if high_stress else None,
        "body_battery_high": s.get("bodyBatteryHighestValue"),
        "body_battery_low": s.get("bodyBatteryLowestValue"),
        "sleep_score": score,
        "sleep_hours": _hours(sleep.get("sleepTimeSeconds")),
        "deep_hours": _hours(sleep.get("deepSleepSeconds")),
        "light_hours": _hours(sleep.get("lightSleepSeconds")),
        "rem_hours": _hours(sleep.get("remSleepSeconds")),
        "awake_hours": _hours(sleep.get("awakeSleepSeconds")),
        "bedtime_hour": round(bedtime, 2) if bedtime is not None else None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=180, help="how many days back to fetch (default 180)")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and re-download every day")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(args.days, -1, -1)]
    recent = set(days[-2:])
    todo = [d for d in days if args.refresh or d in recent or not (RAW_DIR / f"{d}.json").exists()]

    if todo:
        client = connect()
        print(f"Fetching {len(todo)} day(s) from Garmin Connect...")
        for i, d in enumerate(todo, 1):
            (RAW_DIR / f"{d}.json").write_text(json.dumps(fetch_day(client, d)))
            if i % 20 == 0:
                print(f"  {i}/{len(todo)}")
            time.sleep(0.3)  # be gentle with Garmin's API
    else:
        print("Cache is up to date.")

    rows = [flatten(d, json.loads((RAW_DIR / f"{d}.json").read_text())) for d in days if (RAW_DIR / f"{d}.json").exists()]
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(rows)} days to {OUT_CSV}")


if __name__ == "__main__":
    main()
