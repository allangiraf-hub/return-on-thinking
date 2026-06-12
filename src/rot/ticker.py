"""Assemble docs/data/ticker.json - the weekly fragility ticker payload.

v0 content: F1 financing headroom per hyperscaler (trailing-4q capex vs OCF),
data-centre construction, GPU rental medians, rates. Every block carries
its source URL; the page renders nothing it cannot cite.
"""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from .config import SITE_DATA
from .seriesio import read_series
from .universe import load_universe


def _trailing4(sid: str) -> float | None:
    try:
        df = read_series(sid)
    except FileNotFoundError:
        return None
    df = df.sort_values("date").tail(4)
    return float(df["value"].sum()) if len(df) == 4 else None


def build() -> dict:
    uni = load_universe()
    financing = []
    for _, firm in uni[uni.bucket == "hyperscaler"].iterrows():
        t = firm.ticker.lower()
        capex, ocf = _trailing4(f"edgar_{t}_capex_q"), _trailing4(f"edgar_{t}_ocf_q")
        if capex and ocf:
            financing.append(
                {
                    "ticker": firm.ticker,
                    "capex_t4q_usd": capex,
                    "ocf_t4q_usd": ocf,
                    "capex_share_of_ocf": round(capex / ocf, 3),
                    "source_url": "https://data.sec.gov/",
                }
            )

    def series_block(sid: str, keep: int = 60, extra_cols: list[str] | None = None) -> dict | None:
        try:
            df = read_series(sid).sort_values("date").tail(keep)
        except FileNotFoundError:
            return None
        cols = ["date", "value"] + (extra_cols or [])
        return {
            "unit": str(df["unit"].iloc[-1]),
            "source_url": str(df["source_url"].iloc[-1]),
            "points": json.loads(
                df[cols].assign(date=df["date"].dt.date.astype(str)).to_json(orient="records")
            ),
        }

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "financing_f1": financing,
        "datacenter_construction": series_block("census_datacenter_construction"),
        "gpu_rental": series_block("vastai_gpu_rental", keep=2000, extra_cols=["gpu_model"]),
        "rates": {
            "treasury_10y": series_block("treasury_10y", keep=250),
            "dgs10": series_block("fred_dgs10", keep=120),
            "baa10y": series_block("fred_baa10y", keep=120),
        },
        "methodology_version": "pre-v1 (P0 ticker; assumptions file lands in P1)",
    }
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "ticker.json").write_text(json.dumps(payload, indent=1))
    return payload
