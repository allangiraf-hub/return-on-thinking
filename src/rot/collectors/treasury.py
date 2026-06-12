"""10-year Treasury yield direct from the US Treasury's daily yield-curve CSV.

Primary-source backstop for FRED's DGS10 (FRED's keyless endpoint proved
unreliable, 2026-06-12). Fetches the current year plus the previous one.
"""
from __future__ import annotations

import datetime as dt

import io

import pandas as pd
import requests

from ..seriesio import write_series

URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
    "&field_tdr_date_value={year}&_format=csv"
)


def run() -> list[str]:
    year = dt.date.today().year
    frames = []
    for y in (year - 1, year):
        r = requests.get(URL.format(year=y), timeout=60, headers={"User-Agent": "return-on-thinking (allan@aroscapital.com)"})
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    if "10 Yr" not in df.columns:
        raise RuntimeError("Treasury CSV: '10 Yr' column missing - layout drift?")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["Date"], format="%m/%d/%Y").dt.date.astype(str),
            "value": pd.to_numeric(df["10 Yr"], errors="coerce"),
            "unit": "percent",
            "source_url": URL.format(year=year),
            "tier": "T1",
        }
    ).dropna()
    write_series("treasury_10y", out)
    return ["treasury_10y"]
