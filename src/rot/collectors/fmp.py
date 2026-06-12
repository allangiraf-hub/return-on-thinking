"""FMP (Ultimate plan): earnings-call transcripts and statements for filers
EDGAR cannot cover (foreign private issuers, e.g. Nebius).

Secret: FMP_API_KEY (env). Full transcripts are licensed content and are
NEVER committed - they are fetched, scanned for revenue statements, and only
short verbatim hit sentences (fair-use quotes with provenance) are stored in
data/raw/transcript_hits.csv for human review into curated/ai_revenue.csv.
"""
from __future__ import annotations

import os
import re

import pandas as pd
import requests

from ..config import RAW
from ..seriesio import write_series
from ..universe import load_universe

BASE = "https://financialmodelingprep.com/stable"
HITS_FILE = RAW / "transcript_hits.csv"
BACKFILL_FROM = 2023

# Sentences worth a human look: money amounts near AI/run-rate language.
PATTERN = re.compile(
    r"(annualized|run[- ]?rate|ARR\b|AI revenue|artificial intelligence revenue|"
    r"AI business|backlog|remaining performance obligation|RPO\b|Azure AI|AI cloud)",
    re.I,
)
MONEY = re.compile(r"\$\s?\d[\d,.]*\s*(billion|million|bn|mn|m\b|b\b)", re.I)

FOREIGN_FILERS = {"NBIS"}  # no us-gaap XBRL; statements come via FMP


def _key() -> str:
    k = os.environ.get("FMP_API_KEY")
    if not k:
        raise RuntimeError("FMP_API_KEY not set")
    return k


def _get(path: str, **params) -> list | dict:
    params["apikey"] = _key()
    r = requests.get(f"{BASE}/{path}", params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def scan_transcript(ticker: str, year: int, quarter: int) -> list[dict]:
    data = _get("earning-call-transcript", symbol=ticker, year=year, quarter=quarter)
    if not data:
        return []
    content = data[0].get("content", "")
    date = data[0].get("date", f"{year}-Q{quarter}")
    hits = []
    for sent in re.split(r"(?<=[.!?])\s+", content):
        if PATTERN.search(sent) and MONEY.search(sent) and len(sent) < 600:
            hits.append(
                {
                    "ticker": ticker, "year": year, "quarter": quarter,
                    "call_date": str(date)[:10], "sentence": sent.strip(),
                    "status": "candidate",
                }
            )
    return hits


def transcript_dates(ticker: str) -> list[tuple[int, int]]:
    data = _get("earning-call-transcript-dates", symbol=ticker)
    return [(d["fiscalYear"], d["quarter"]) for d in data if int(d["fiscalYear"]) >= BACKFILL_FROM]


def append_hits(rows: list[dict]) -> int:
    if not rows:
        return 0
    new = pd.DataFrame(rows)
    HITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if HITS_FILE.exists():
        hist = pd.read_csv(HITS_FILE)
        new = pd.concat([hist, new], ignore_index=True)
        new = new.drop_duplicates(["ticker", "year", "quarter", "sentence"])
    new.to_csv(HITS_FILE, index=False)
    return len(new)


def run() -> list[str]:
    """Weekly mode: scan only the latest transcript per ticker; pull NBIS statements."""
    written = []
    for _, firm in load_universe().iterrows():
        try:
            dates = transcript_dates(firm.ticker)
        except requests.HTTPError:
            continue
        if dates:
            y, q = sorted(dates)[-1]
            append_hits(scan_transcript(firm.ticker, y, q))
    for ticker in FOREIGN_FILERS:
        try:
            rows = _get("cash-flow-statement", symbol=ticker, period="quarter", limit=40)
        except requests.HTTPError:
            # some symbols only resolve on the v3 path
            r = requests.get(
                f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}",
                params={"period": "quarter", "limit": 40, "apikey": _key()}, timeout=120)
            r.raise_for_status()
            rows = r.json()
        for concept, field in [("capex", "capitalExpenditure"), ("ocf", "operatingCashFlow"),
                               ("debt_issued", "netDebtIssuance")]:
            df = pd.DataFrame(
                {
                    "date": [r["date"] for r in rows],
                    "value": [abs(r.get(field) or 0) for r in rows],
                    "unit": "USD",
                    "source_url": f"{BASE}/cash-flow-statement?symbol={ticker}",
                    "tier": "T2",
                }
            )
            df = df[df["value"] > 0]
            if not df.empty:
                sid = f"fmp_{ticker.lower()}_{concept}_q"
                write_series(sid, df)
                written.append(sid)
    return written
