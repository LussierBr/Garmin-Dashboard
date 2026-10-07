"""Download daily Garmin Connect data and cache it locally.

Credentials come ONLY from environment variables, never from this file:
    GARMIN_EMAIL, GARMIN_PASSWORD

After the first login, session tokens are saved to ~/.garminconnect (or
$GARMINTOKENS), so later runs don't need the password or an MFA code.

Raw API responses are cached one file per day in data/raw/, so re-running only
downloads days that are new (plus the last two days, which may have changed).
The flattened table is written to data/garmin_daily.csv, which the app uses
automatically in place of the sample data.

With --mongo (and MONGODB_URI set), the days are also upserted into MongoDB and
the Garmin session is saved there too, so the scheduled GitHub Action can log
in without a password or MFA code. See README "Deploy".

Usage:
    python fetch_garmin.py                    # last 180 days, local CSV only
    python fetch_garmin.py --days 365 --mongo # also upload to MongoDB
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


def connect(use_mongo: bool = False):
    from garminconnect import Garmin

    email, password = os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD")
    interactive = sys.stdin.isatty()
    prompt = (lambda: input("Garmin MFA code: ").strip()) if interactive else None

    # Prefer the session saved in MongoDB (kept fresh by every run), then the local token file.
    stores = [TOKENSTORE]
    if use_mongo:
        from garmin_dash import store
        saved = store.load_tokens()
        if saved:
            stores.insert(0, saved)

    error = None
    for tokenstore in stores:
        client = Garmin(email, password, prompt_mfa=prompt)
        try:
            # Uses saved tokens if valid, otherwise logs in with the env-var credentials.
            client.login(tokenstore)
            return client
        except Exception as e:  # library raises several auth/connection types
            error = e

    if not interactive:
        sys.exit(
            f"Garmin login failed ({type(error).__name__}). The saved session has probably expired: "
            "run `python fetch_garmin.py --mongo` once on your own computer to refresh it."
        )
    if not (email and password):
        sys.exit("No saved Garmin session. Set GARMIN_EMAIL and GARMIN_PASSWORD and try again.")
    sys.exit(f"Garmin login failed: {type(error).__name__}: {error}")


def save_session(client, use_mongo: bool) -> None:
    """Persist the (possibly refreshed) session so the next run can reuse it."""
    tokens = client.client.dumps()
    if use_mongo:
        from garmin_dash import store
        store.save_tokens(tokens)
    if sys.stdin.isatty():  # keep the local token file current too, on your own machine
        try:
            client.client.dump(str(Path(TOKENSTORE).expanduser()))
        except Exception:
            pass


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
        # Today's steps/stress are still accumulating; the app hides them until a later run completes the day.
        "partial_day": day >= date.today().isoformat(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=180, help="how many days back to fetch (default 180)")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and re-download every day")
    ap.add_argument("--mongo", action="store_true", help="also upload to MongoDB (needs MONGODB_URI)")
    args = ap.parse_args()
    if args.mongo and not os.getenv("MONGODB_URI"):
        sys.exit("--mongo needs the MONGODB_URI environment variable.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(args.days, -1, -1)]
    recent = set(days[-2:])
    todo = [d for d in days if args.refresh or d in recent or not (RAW_DIR / f"{d}.json").exists()]

    if todo:
        client = connect(args.mongo)
        print(f"Fetching {len(todo)} day(s) from Garmin Connect...")
        for i, d in enumerate(todo, 1):
            (RAW_DIR / f"{d}.json").write_text(json.dumps(fetch_day(client, d)))
            if i % 20 == 0:
                print(f"  {i}/{len(todo)}")
            time.sleep(0.3)  # be gentle with Garmin's API
        save_session(client, args.mongo)
    else:
        print("Cache is up to date.")

    rows = [flatten(d, json.loads((RAW_DIR / f"{d}.json").read_text())) for d in days if (RAW_DIR / f"{d}.json").exists()]
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(rows)} days to {OUT_CSV}")

    if args.mongo:
        from garmin_dash import store
        print(f"Upserted {store.upsert_daily(rows)} days into MongoDB.")


if __name__ == "__main__":
    main()
