"""Company universe with runtime CIK resolution via SEC's ticker map."""
from __future__ import annotations

import json

import pandas as pd
import requests

from .config import CURATED, EDGAR_USER_AGENT, UNIVERSE_FILE

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_CACHE = CURATED / "cik_cache.json"


def load_universe() -> pd.DataFrame:
    """ticker,bucket from curated file + cik column (cached lookup)."""
    uni = pd.read_csv(UNIVERSE_FILE, comment="#")
    cache = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}
    unknown = [t for t in uni["ticker"] if t not in cache]
    if unknown:
        r = requests.get(
            TICKER_MAP_URL,
            headers={"User-Agent": EDGAR_USER_AGENT},
            timeout=60,
        )
        r.raise_for_status()
        sec = {v["ticker"].upper(): v["cik_str"] for v in r.json().values()}
        for t in unknown:
            if t.upper() in sec:
                cache[t] = int(sec[t.upper()])
        _CACHE.write_text(json.dumps(cache, indent=0))
    uni["cik"] = uni["ticker"].map(cache)
    missing = uni[uni["cik"].isna()]["ticker"].tolist()
    if missing:
        raise LookupError(f"no CIK found for {missing}; foreign filers may need manual entry in cik_cache.json")
    uni["cik"] = uni["cik"].astype(int)
    return uni
