"""US Census C30: monthly data-centre construction put in place (private, SA).

Source: the published C30 time-series workbook (no API key needed):
https://www.census.gov/construction/c30/xlsx/privsatime.xlsx
'Data center' column, $mn at seasonally adjusted annual rate.
Date cells carry p/r suffixes (preliminary/revised); both are accepted and
later runs overwrite with revised values.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from ..seriesio import write_series

XLSX_URL = "https://www.census.gov/construction/c30/xlsx/privsatime.xlsx"
PAGE_URL = "https://www.census.gov/construction/c30/c30index.html"


def run() -> list[str]:
    r = requests.get(XLSX_URL, timeout=120, headers={"User-Agent": "return-on-thinking (allan@aroscapital.com)"})
    r.raise_for_status()
    raw = pd.ExcelFile(io.BytesIO(r.content)).parse(0, header=None)
    hdr_rows = raw.index[raw[0].astype(str).str.strip().eq("Date")]
    if len(hdr_rows) == 0:
        raise RuntimeError("Census C30: no 'Date' header row - workbook layout drift?")
    hdr = hdr_rows[0]
    header = raw.iloc[hdr].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    dc_cols = [i for i, h in enumerate(header) if h.lower() == "data center"]
    if not dc_cols:
        raise RuntimeError("Census C30: no 'Data center' column - category drift?")
    body = raw.iloc[hdr + 1 :, [0, dc_cols[0]]].copy()
    body.columns = ["raw_date", "value"]
    body["raw_date"] = body["raw_date"].astype(str).str.strip().str.rstrip("pr")
    body["date"] = pd.to_datetime(body["raw_date"], format="%b-%y", errors="coerce")
    body["value"] = pd.to_numeric(body["value"], errors="coerce")
    body = body.dropna(subset=["date", "value"])
    if len(body) < 24:
        raise RuntimeError(f"Census C30: only {len(body)} usable rows - parse drift?")
    out = pd.DataFrame(
        {
            "date": body["date"].dt.date.astype(str),
            "value": body["value"],
            "unit": "USD mn, SAAR (private, seasonally adjusted)",
            "source_url": XLSX_URL,
            "tier": "T1",
        }
    )
    write_series("census_datacenter_construction", out)
    return ["census_datacenter_construction"]
