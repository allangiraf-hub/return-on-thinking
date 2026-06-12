"""The collector contract: every series row carries its evidence.

Columns: series_id, date, value, unit, source_url, retrieved_at, tier.
tier: T1 = filed/official, T2 = company-stated, T3 = press-reported.
Collectors raise on schema drift rather than silently adapting.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from .config import SERIES

REQUIRED = ["series_id", "date", "value", "unit", "source_url", "retrieved_at", "tier"]
TIERS = {"T1", "T2", "T3"}


def validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"series frame missing columns: {missing}")
    if df["value"].isna().any():
        raise ValueError("series frame contains NaN values")
    bad = set(df["tier"].unique()) - TIERS
    if bad:
        raise ValueError(f"unknown tiers: {bad}")
    return df


def write_series(series_id: str, df: pd.DataFrame) -> pd.DataFrame:
    """Validate and write one series to data/series/<series_id>.csv (full replace)."""
    df = df.copy()
    df["series_id"] = series_id
    df["retrieved_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    df = validate(df[REQUIRED + [c for c in df.columns if c not in REQUIRED]])
    df = df.sort_values("date")
    SERIES.mkdir(parents=True, exist_ok=True)
    df.to_csv(SERIES / f"{series_id}.csv", index=False)
    return df


def append_snapshot(series_id: str, df: pd.DataFrame) -> pd.DataFrame:
    """Append-only writer for irreplaceable snapshot series (GPU prices).
    Idempotent within a day; never deletes history."""
    df = df.copy()
    df["series_id"] = series_id
    df["retrieved_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    df = validate(df[REQUIRED + [c for c in df.columns if c not in REQUIRED]])
    path = SERIES / f"{series_id}.csv"
    SERIES.mkdir(parents=True, exist_ok=True)
    if path.exists():
        hist = pd.read_csv(path)
        today_dates = set(df["date"].astype(str))
        hist = hist[~hist["date"].astype(str).isin(today_dates)]
        df = pd.concat([hist, df], ignore_index=True)
    df = df.sort_values("date")
    df.to_csv(path, index=False)
    return df


def read_series(series_id: str) -> pd.DataFrame:
    path = SERIES / f"{series_id}.csv"
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df
