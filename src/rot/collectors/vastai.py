"""GPU rental spot prices - the market price of the user cost.

Ported from potindicators.gpu but writes through the append-only contract:
this archive cannot be backfilled, so history is never deleted.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
from potindicators.gpu import fetch_offers

from ..config import GPU_MODELS
from ..seriesio import append_snapshot


def run() -> list[str]:
    offers = fetch_offers()
    today = dt.date.today().isoformat()
    rows = []
    for model in GPU_MODELS:
        sel = offers[offers["gpu_name"].str.contains(model, case=False, na=False)]
        if len(sel) >= 3:
            rows.append(
                {
                    "date": today,
                    "gpu_model": model,
                    "value": round(float(sel["usd_per_gpu_hr"].median()), 4),
                    "n_offers": len(sel),
                }
            )
    if not rows:
        raise RuntimeError("vast.ai returned no offers for any tracked GPU - source drift?")
    df = pd.DataFrame(rows)
    df["unit"] = "USD/GPU-hr"
    df["source_url"] = "https://console.vast.ai/api/v0/bundles/"
    df["tier"] = "T1"
    append_snapshot("vastai_gpu_rental", df)
    return ["vastai_gpu_rental"]
