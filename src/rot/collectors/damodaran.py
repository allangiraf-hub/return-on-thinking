"""Implied equity risk premium from Damodaran's public dataset (annual history).

Calibration input for r in the user cost. The histimpl.xls sheet carries
one row per year; we take 'Implied ERP (FCFE)' or the closest match.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

from ..config import DAMODARAN_HISTIMPL
from ..seriesio import write_series


def run() -> list[str]:
    r = requests.get(DAMODARAN_HISTIMPL, timeout=120, headers={"User-Agent": "return-on-thinking"})
    r.raise_for_status()
    raw = pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)
    # locate header row: first row containing 'Year'
    hdr_idx = raw.index[raw.apply(lambda row: row.astype(str).str.fullmatch("Year").any(), axis=1)][0]
    df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=hdr_idx)
    df.columns = [str(c).strip() for c in df.columns]
    erp_col = next(c for c in df.columns if "Implied ERP" in c and "FCFE" in c) if any(
        "Implied ERP" in c and "FCFE" in c for c in df.columns
    ) else next(c for c in df.columns if "Implied" in c and "Premium" in c or "Implied ERP" in c)
    df = df[["Year", erp_col]].dropna()
    df = df[pd.to_numeric(df["Year"], errors="coerce").notna()]
    out = pd.DataFrame(
        {
            "date": df["Year"].astype(int).astype(str) + "-12-31",
            "value": pd.to_numeric(df[erp_col], errors="coerce") * 100.0,
            "unit": "percent",
            "source_url": DAMODARAN_HISTIMPL,
            "tier": "T2",
        }
    ).dropna()
    if len(out) < 30:
        raise RuntimeError(f"Damodaran sheet parsed only {len(out)} rows - layout drift?")
    write_series("damodaran_implied_erp", out)
    return ["damodaran_implied_erp"]
