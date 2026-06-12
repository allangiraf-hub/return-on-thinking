"""Capex, operating cash flow and debt issuance for the K-holder universe.

Reuses potindicators' EDGAR functions (tag fallback, YTD differencing).
Writes per-firm quarterly series with the filing as evidence.
"""
from __future__ import annotations

import pandas as pd
from potindicators import edgar as pe


def _quarters(raw: pd.DataFrame) -> pd.DataFrame:
    """Defensive wrapper: quarterly_values raises on frames that yield no
    quarters (young filers, sparse tags); treat that as 'no data'."""
    try:
        q = pe.quarterly_values(raw)
    except KeyError:
        return pd.DataFrame()
    return q if not q.empty else pd.DataFrame()

from ..config import TAG_CAPEX, TAG_DEBT_ISSUED, TAG_OCF
from ..seriesio import write_series
from ..universe import load_universe

CONCEPTS = {"capex": TAG_CAPEX, "ocf": TAG_OCF, "debt_issued": TAG_DEBT_ISSUED}


def run() -> list[str]:
    written = []
    for _, firm in load_universe().iterrows():
        for concept, tags in CONCEPTS.items():
            raw = pe.concept_with_fallback(int(firm.cik), tags)
            if raw.empty:
                continue
            q = _quarters(raw)
            if q.empty:
                continue
            df = pd.DataFrame(
                {
                    "date": q["period_end"].dt.date.astype(str),
                    "value": q["usd"],
                    "unit": "USD",
                    "source_url": f"https://data.sec.gov/api/xbrl/companyconcept/CIK{int(firm.cik):010d}/us-gaap/{tags[0]}.json",
                    "tier": "T1",
                }
            )
            sid = f"edgar_{firm.ticker.lower()}_{concept}_q"
            write_series(sid, df)
            written.append(sid)
    return written
