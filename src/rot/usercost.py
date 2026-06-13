"""User cost of the AI capital stock: UC = Sum_i (r_i + delta_i) K_i.

v2: K is AI-ATTRIBUTED. Each firm's quarterly capex is multiplied by an
ai_capex_share (banded, per bucket) before accumulation, so the stock reflects
AI/data-centre capital rather than all corporate capex. The denominator can be
restricted to a firm subset so a coverage ratio always compares the same
population in numerator and denominator (the adversarial-review fix).
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .seriesio import read_series
from .universe import load_universe


def _firm_capex_q(ticker: str) -> pd.Series | None:
    t = ticker.lower()
    for sid in (f"edgar_{t}_capex_q", f"fmp_{t}_capex_q"):
        try:
            return read_series(sid).sort_values("date").set_index("date")["value"]
        except FileNotFoundError:
            continue
    return None


def _perpetual_inventory(capex_q: pd.Series, delta_annual: float) -> float:
    dq = 1 - (1 - delta_annual) ** 0.25
    k = 0.0
    for cx in capex_q:
        k = k * (1 - dq) + cx
    return k


def user_cost(corner: str = "mid", tickers: list[str] | None = None,
              share_corner: str | None = None) -> dict:
    """AI-attributed user cost ($/yr) at a delta corner, over a firm subset.

    tickers: restrict to these firms (default: all hyperscalers + neoclouds).
    share_corner: which ai_capex_share band to use (defaults to `corner`).
    """
    a = load()
    uni = load_universe().set_index("ticker")
    if tickers is None:
        tickers = uni[uni.bucket.isin(["hyperscaler", "neocloud"])].index.tolist()
    sc = share_corner or corner

    try:
        rf = read_series("treasury_10y")["value"].iloc[-1] / 100
    except FileNotFoundError:
        rf = a["r"].get("risk_free_fallback", 0.045)
    r = rf + a["r"].get("erp_fallback", 0.043)

    uc = kt = 0.0
    detail = {}
    for tk in tickers:
        if tk not in uni.index:
            continue
        bucket = uni.loc[tk, "bucket"]
        if bucket not in ("hyperscaler", "neocloud"):
            continue
        cx = _firm_capex_q(tk)
        if cx is None or cx.empty:
            continue
        ai_share = a["ai_capex_share"][bucket][sc]
        alloc = a["k_allocation"]["neocloud" if bucket == "neocloud" else "hyperscaler"]
        for cls, ashare in alloc.items():
            delta = a["delta"][cls][corner]
            k_cls = _perpetual_inventory(cx * ai_share * ashare, delta)
            uc += (r + delta) * k_cls
            kt += k_cls
            detail.setdefault(cls, 0.0)
            detail[cls] += k_cls
    return {"user_cost": uc, "K_total": kt, "r": r, "corner": corner,
            "ai_share_corner": sc, "tickers": tickers, "detail": detail}
