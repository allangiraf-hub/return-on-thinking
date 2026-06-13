"""Fragility index F - v2: weakest-link, not a weighted average.

The v1 weighted average put 50% of the weight on an aggregate term that nets the
cash-rich centre against the leveraged edge - hiding exactly the edge risk the
framework says matters most (adversarial review 2026-06-13). v2 uses
F = max(centre external share, edge external share), with circular deals shown as
a separate flag rather than averaged into invisibility.
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .config import CURATED
from .seriesio import read_series
from .universe import load_universe

STAGE_COLOR = {"hedge": "#1D9E75", "speculative": "#BA7517", "ponzi": "#E24B4A"}


def _t4(sid: str, asof=None) -> float | None:
    try:
        df = read_series(sid).sort_values("date")
    except FileNotFoundError:
        return None
    if asof is not None:
        df = df[df["date"] <= pd.Timestamp(asof)]
    df = df.tail(4)
    return float(df["value"].sum()) if len(df) == 4 else None


def _ext_share(tickers: list[str], asof=None) -> float | None:
    cap = ocf = 0.0
    n = 0
    for t in tickers:
        tl = t.lower()
        c = _t4(f"edgar_{tl}_capex_q", asof) or _t4(f"fmp_{tl}_capex_q", asof)
        o = _t4(f"edgar_{tl}_ocf_q", asof) or _t4(f"fmp_{tl}_ocf_q", asof)
        if c and o:
            cap += c
            ocf += o
            n += 1
    return max(0.0, (cap - ocf) / cap) if cap and n else None


def _open_circularity_flags() -> int:
    p = CURATED / "ledger.csv"
    if not p.exists():
        return 0
    df = pd.read_csv(p)
    if "circularity_flag" not in df.columns:
        return 0
    return int(df["circularity_flag"].astype(str).str.lower().isin(["true", "1"]).sum())


def fragility(asof=None) -> dict:
    a = load()["fragility"]
    uni = load_universe()
    centre = _ext_share(uni[uni.bucket == "hyperscaler"]["ticker"].tolist(), asof=asof) or 0.0
    edge = _ext_share(uni[uni.bucket == "neocloud"]["ticker"].tolist(), asof=asof) or 0.0
    flags = _open_circularity_flags()

    # F is pure located-leverage; circular deals are a SEPARATE warning flag, not
    # averaged or added into the number (the v1 mistake was burying signals in a blend).
    F = max(0.0, min(1.0, max(centre, edge)))
    th = a["stage_thresholds"]
    stage = "hedge" if F < th["hedge"] else "speculative" if F < th["speculative"] else "ponzi"
    return {
        "F": F, "stage": stage, "color": STAGE_COLOR[stage],
        "components": {"centre_external_share": centre, "edge_external_share": edge,
                       "circularity_flags": flags},
        "note": "v2: F = max(centre, edge) external-finance share + circularity bonus. "
                "The headline tracks wherever the leverage actually sits - the centre self-funds, "
                "the neocloud edge does not. A weighted average hid the edge.",
    }
