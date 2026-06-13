"""Retail electricity prices in data-centre-heavy states - a harm indicator
shown beside the social-return dial (the Cs axis is published gross of harms).

EIA API v2; key in env EIA_API_KEY (CI secret). States chosen for data-centre
concentration: Virginia, Texas, Ohio, Iowa, Oregon, Arizona.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

from ..seriesio import write_series

STATES = ["VA", "TX", "OH", "IA", "OR", "AZ"]
URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"


def run() -> list[str]:
    key = os.environ.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY not set")
    written = []
    for st in STATES:
        r = requests.get(URL, params={
            "api_key": key, "frequency": "monthly", "data[0]": "price",
            "facets[sectorid][]": "ALL", "facets[stateid][]": st,
            "start": "2018-01", "sort[0][column]": "period", "sort[0][direction]": "asc",
            "length": 5000}, timeout=120)
        r.raise_for_status()
        data = r.json()["response"]["data"]
        if not data:
            continue
        df = pd.DataFrame({
            "date": [d["period"] + "-01" for d in data],
            "value": [float(d["price"]) for d in data if d.get("price") is not None],
            "unit": "cents/kWh (all sectors)",
            "source_url": "https://www.eia.gov/electricity/data.php",
            "tier": "T1"})
        sid = f"eia_elec_price_{st.lower()}"
        write_series(sid, df)
        written.append(sid)
    return written
