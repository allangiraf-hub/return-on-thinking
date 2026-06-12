"""Rates for the user-cost r, via FRED's keyless fredgraph.csv.

Implemented directly (not via potindicators) to send an explicit User-Agent
and retry: FRED's CDN intermittently rejects default library agents from
datacenter IPs (observed on GitHub Actions, 2026-06-12).
"""
from __future__ import annotations

import io
import time

import pandas as pd
import requests

from ..config import FRED_SERIES
from ..seriesio import write_series

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; return-on-thinking/0.1; +https://returns.priceofthinking.com)",
    "Accept": "text/csv,*/*",
}


def fred_series(series_id: str, attempts: int = 3) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    last: Exception | None = None
    for i in range(attempts):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            df.columns = ["date", "value"]
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            return df.dropna()
        except Exception as e:  # noqa: BLE001 - retried, then re-raised
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"FRED fetch failed for {series_id} after {attempts} attempts") from last


def run() -> list[str]:
    written = []
    for sid, _desc in FRED_SERIES.items():
        df = fred_series(sid)
        df["date"] = df["date"].dt.date.astype(str)
        df["unit"] = "percent"
        df["source_url"] = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        df["tier"] = "T1"
        out = f"fred_{sid.lower()}"
        write_series(out, df)
        written.append(out)
    return written
