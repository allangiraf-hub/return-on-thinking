"""FMP revenue collector (v5) - self-refresh the Cp numerator.

Replaces hand-pinned ai_revenue.csv rows for the two mechanical revenue inputs:
  * neocloud total revenue  -> quarterly income-statement revenue per pure-play
    (CRWV, IREN, APLD), written as fmp_<t>_revenue_q; dials takes the trailing 4q.
  * cloud-segment revenue    -> annual revenue-product-segmentation, the cloud line
    per hyperscaler (GOOGL "Google Cloud", ORCL "Cloud And License Business"),
    written as fmp_<t>_cloud_segment_rev_a; dials applies the AI-share band.

Stated AI ARR (Microsoft/Amazon/Nebius) stays in the curated CSV - those are
verbatim earnings-call quotes that need human review, not a mechanical series.

Secret: FMP_API_KEY (env). Validated 2026-06-13: the trailing-4q sums reproduce
the pinned figures exactly (CRWV $6.23bn, IREN $0.76bn, APLD $0.36bn) and the
segment lines match the 10-Ks (Google Cloud $58.7bn, Oracle $49.2bn).
"""
from __future__ import annotations

import os

import pandas as pd
import requests

from ..seriesio import write_series

BASE = "https://financialmodelingprep.com/stable"
NEOCLOUDS = ["CRWV", "IREN", "APLD"]
# (ticker -> the segment label FMP reports for the cloud line)
CLOUD_SEGMENT = {"GOOGL": "Google Cloud", "ORCL": "Cloud And License Business"}


def _key() -> str:
    k = os.environ.get("FMP_API_KEY")
    if not k:
        raise RuntimeError("FMP_API_KEY not set")
    return k


def _get(path: str, **params) -> list:
    params["apikey"] = _key()
    r = requests.get(f"{BASE}/{path}", params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def _neocloud_revenue(ticker: str) -> str | None:
    rows = _get("income-statement", symbol=ticker, period="quarter", limit=8)
    recs = [{"date": r["date"], "value": abs(r.get("revenue") or 0)} for r in rows if r.get("revenue")]
    if not recs:
        return None
    df = pd.DataFrame(recs)
    df["unit"] = "USD"
    df["source_url"] = f"{BASE}/income-statement?symbol={ticker}&period=quarter"
    df["tier"] = "T1"
    sid = f"fmp_{ticker.lower()}_revenue_q"
    write_series(sid, df[df["value"] > 0])
    return sid


def _cloud_segment(ticker: str, label: str) -> str | None:
    rows = _get("revenue-product-segmentation", symbol=ticker, period="annual", limit=6)
    recs = []
    for r in rows:
        data = r.get("data") or {}
        if label in data and data[label]:
            recs.append({"date": r["date"], "value": abs(data[label])})
    if not recs:
        return None
    df = pd.DataFrame(recs)
    df["unit"] = "USD"
    df["source_url"] = f"{BASE}/revenue-product-segmentation?symbol={ticker}"
    df["tier"] = "T1"
    sid = f"fmp_{ticker.lower()}_cloud_segment_rev_a"
    write_series(sid, df[df["value"] > 0])
    return sid


def run() -> list[str]:
    written = []
    for tk in NEOCLOUDS:
        try:
            sid = _neocloud_revenue(tk)
            if sid:
                written.append(sid)
        except requests.HTTPError:
            continue
    for tk, label in CLOUD_SEGMENT.items():
        try:
            sid = _cloud_segment(tk, label)
            if sid:
                written.append(sid)
        except requests.HTTPError:
            continue
    return written
