"""MongoDB storage for the daily table and the Garmin session tokens.

Layout (database names can be overridden with env vars):
  garmin.daily          one document per day, _id = "YYYY-MM-DD", fields = data.RAW_COLUMNS
  garmin_auth.tokens    one document, _id = "garmin", the Garmin session token JSON

Tokens live in a separate database so the web app can use a MongoDB user that
can only READ the `garmin` database and never sees the Garmin session.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timezone

import pandas as pd

DB_NAME = os.getenv("MONGODB_DB", "garmin")
AUTH_DB_NAME = os.getenv("MONGODB_AUTH_DB", "garmin_auth")


def mongo_uri() -> str | None:
    return os.getenv("MONGODB_URI") or None


def _client():
    from pymongo import MongoClient

    uri = mongo_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI is not set")
    return MongoClient(uri, serverSelectionTimeoutMS=15000, appname="garmin-dashboard")


def _clean(value):
    """NaN/NA -> None and numpy scalars -> Python, so documents stay plain JSON-ish."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def upsert_daily(rows: list[dict]) -> int:
    """Insert or replace one document per day. Returns the number of days written."""
    from pymongo import ReplaceOne

    if not rows:
        return 0
    now = datetime.now(timezone.utc)
    ops = []
    for row in rows:
        doc = {k: _clean(v) for k, v in row.items()}
        doc["_id"] = str(doc["date"])[:10]
        doc["date"] = doc["_id"]
        doc["updated_at"] = now
        ops.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
    with _client() as client:
        client[DB_NAME].daily.bulk_write(ops, ordered=False)
    return len(ops)


def read_daily() -> pd.DataFrame:
    with _client() as client:
        docs = list(client[DB_NAME].daily.find({}, {"_id": 0, "updated_at": 0}))
    return pd.DataFrame(docs)


def load_tokens() -> str | None:
    with _client() as client:
        doc = client[AUTH_DB_NAME].tokens.find_one({"_id": "garmin"})
    return doc["tokens"] if doc else None


def save_tokens(tokens_json: str) -> None:
    with _client() as client:
        client[AUTH_DB_NAME].tokens.replace_one(
            {"_id": "garmin"},
            {"_id": "garmin", "tokens": tokens_json, "updated_at": datetime.now(timezone.utc)},
            upsert=True,
        )
