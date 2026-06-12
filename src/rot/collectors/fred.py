"""Rates for the user-cost r, via FRED's keyless fredgraph.csv."""
from __future__ import annotations

from potindicators.fred import fred_series

from ..config import FRED_SERIES
from ..seriesio import write_series


def run() -> list[str]:
    written = []
    for sid, _desc in FRED_SERIES.items():
        df = fred_series(sid)
        df = df.rename(columns={"value": "value"})
        df["date"] = df["date"].dt.date.astype(str)
        df["unit"] = "percent"
        df["source_url"] = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        df["tier"] = "T1"
        out = f"fred_{sid.lower()}"
        write_series(out, df)
        written.append(out)
    return written
