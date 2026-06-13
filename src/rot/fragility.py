"""Fragility index F (0-1): whose money carries the AI build, and how exposed.

Components (weights in assumptions): aggregate external-finance share across
all K-holders, the same ratio for the neocloud tier alone (the fragile edge),
and a circularity penalty from the deal ledger. Mapped to a Minsky stage and
a traffic-light colour for the map dot.
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .config import CURATED
from .seriesio import read_series
from .universe import load_universe

STAGE_COLOR = {"hedge": "#1D9E75", "speculative": "#BA7517", "ponzi": "#E24B4A"}


def _t4(sid: str) -> float | None:
    try:
        df = read_series(sid).sort_values("date").tail(4)
    except FileNotFoundError:
        return None
    return float(df["value"].sum()) if len(df) == 4 else None


def _ext_share(tickers: list[str]) -> float | None:
    """max(0, (sum capex - sum OCF)/sum capex) over a set of firms, trailing 4q."""
    cap = ocf = 0.0
    n = 0
    for t in tickers:
        tl = t.lower()
        c = _t4(f"edgar_{tl}_capex_q") or _t4(f"fmp_{tl}_capex_q")
        o = _t4(f"edgar_{tl}_ocf_q") or _t4(f"fmp_{tl}_ocf_q")
        if c and o:
            cap += c
            ocf += o
            n += 1
    if not cap or n == 0:
        return None
    return max(0.0, (cap - ocf) / cap)


def _open_circularity_flags() -> int:
    p = CURATED / "ledger.csv"
    if not p.exists():
        return 0
    df = pd.read_csv(p)
    if "circularity_flag" not in df.columns:
        return 0
    return int(df["circularity_flag"].astype(str).str.lower().isin(["true", "1"]).sum())


def fragility() -> dict:
    a = load()["fragility"]
    uni = load_universe()
    hyper_neo = uni[uni.bucket.isin(["hyperscaler", "neocloud"])]["ticker"].tolist()
    neo = uni[uni.bucket == "neocloud"]["ticker"].tolist()

    agg = _ext_share(hyper_neo) or 0.0
    neo_int = _ext_share(neo) or 0.0
    flags = _open_circularity_flags()
    circ = min(1.0, flags / a["circularity_full_at"])

    F = (a["weight_aggregate_external"] * agg
         + a["weight_neocloud_intensity"] * neo_int
         + a["weight_circularity"] * circ)
    F = max(0.0, min(1.0, F))

    th = a["stage_thresholds"]
    stage = "hedge" if F < th["hedge"] else "speculative" if F < th["speculative"] else "ponzi"
    return {
        "F": F, "stage": stage, "color": STAGE_COLOR[stage],
        "components": {"aggregate_external_share": agg, "neocloud_intensity": neo_int,
                       "circularity_flags": flags, "circularity_component": circ},
        "note": "F = location-weighted external-finance dependence of the build, plus a "
                "circularity penalty. Hedge (cash-funded) < 0.33 < speculative < 0.66 < Ponzi. "
                "The centre is solid; fragility concentrates at the neocloud edge.",
    }
