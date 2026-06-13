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


def _firm_capex_q(ticker: str, asof: pd.Timestamp | None = None) -> pd.Series | None:
    t = ticker.lower()
    for sid in (f"edgar_{t}_capex_q", f"fmp_{t}_capex_q"):
        try:
            s = read_series(sid).sort_values("date").set_index("date")["value"]
            if asof is not None:
                s = s[s.index <= asof]
            return s
        except FileNotFoundError:
            continue
    return None


def _perpetual_inventory(capex_q: pd.Series, delta_annual: float) -> float:
    dq = 1 - (1 - delta_annual) ** 0.25
    k = 0.0
    for cx in capex_q:
        k = k * (1 - dq) + cx
    return k


def _trailing4_sum(sid: str, asof: pd.Timestamp | None) -> float | None:
    try:
        df = read_series(sid).sort_values("date")
    except FileNotFoundError:
        return None
    if asof is not None:
        df = df[df["date"] <= asof]
    df = df.tail(4)
    return float(df["value"].sum()) if len(df) else None


def _debt_weight(ticker: str, asof: pd.Timestamp | None) -> float:
    """Debt-funded share of the build = trailing-4q debt issued / trailing-4q capex,
    clipped to [0,1]. The remainder (internal funds + new equity) carries the equity
    required return. Sourced from filed cash-flow (ProceedsFromIssuanceOfLongTermDebt)."""
    t = ticker.lower()
    debt = _trailing4_sum(f"edgar_{t}_debt_issued_q", asof)
    if debt is None:
        debt = _trailing4_sum(f"fmp_{t}_debt_issued_q", asof)
    cap = _trailing4_sum(f"edgar_{t}_capex_q", asof) or _trailing4_sum(f"fmp_{t}_capex_q", asof)
    if not cap or debt is None:
        return 0.0
    return max(0.0, min(1.0, debt / cap))


def user_cost(corner: str = "mid", tickers: list[str] | None = None,
              share_corner: str | None = None, asof=None) -> dict:
    """AI-attributed user cost ($/yr) at a delta corner, over a firm subset.

    tickers: restrict to these firms (default: all hyperscalers + neoclouds).
    share_corner: which ai_capex_share band to use (defaults to `corner`).
    asof: if given (a date/Timestamp), truncate the capex history and the
        risk-free rate at that quarter-end, so the stock and required return
        reflect what was known then (used by the historical backfill).
    """
    a = load()
    uni = load_universe().set_index("ticker")
    if tickers is None:
        tickers = uni[uni.bucket.isin(["hyperscaler", "neocloud"])].index.tolist()
    sc = share_corner or corner
    asof_ts = pd.Timestamp(asof) if asof is not None else None

    try:
        rf_s = read_series("treasury_10y").sort_values("date")
        if asof_ts is not None:
            rf_s = rf_s[rf_s["date"] <= asof_ts]
        rf = rf_s["value"].iloc[-1] / 100
    except (FileNotFoundError, IndexError):
        rf = a["r"].get("risk_free_fallback", 0.045)
    # v5 debt/equity split: equity-funded capital demands rf+ERP, debt-funded rf+Baa
    # spread; each firm's blended required return weights them by its financing mix.
    try:
        baa_s = read_series(a["r"].get("debt_spread_series", "fred_baa10y")).sort_values("date")
        if asof_ts is not None:
            baa_s = baa_s[baa_s["date"] <= asof_ts]
        baa = baa_s["value"].iloc[-1] / 100
    except (FileNotFoundError, IndexError):
        baa = a["r"].get("baa_spread_fallback", 0.017)
    r_equity = rf + a["r"].get("erp_fallback", 0.043)
    r_debt = rf + baa

    uc = kt = 0.0
    detail = {}
    wsum = wk = 0.0  # K-weighted mean debt share, for reporting
    for tk in tickers:
        if tk not in uni.index:
            continue
        bucket = uni.loc[tk, "bucket"]
        if bucket not in ("hyperscaler", "neocloud"):
            continue
        cx = _firm_capex_q(tk, asof=asof_ts)
        if cx is None or cx.empty:
            continue
        w_debt = _debt_weight(tk, asof_ts)
        r_firm = w_debt * r_debt + (1 - w_debt) * r_equity
        ai_share = a["ai_capex_share"][bucket][sc]
        alloc = a["k_allocation"]["neocloud" if bucket == "neocloud" else "hyperscaler"]
        for cls, ashare in alloc.items():
            delta = a["delta"][cls][corner]
            k_cls = _perpetual_inventory(cx * ai_share * ashare, delta)
            uc += (r_firm + delta) * k_cls
            kt += k_cls
            detail.setdefault(cls, 0.0)
            detail[cls] += k_cls
            wsum += w_debt * k_cls
            wk += k_cls
    r = r_equity  # nominal all-equity reference (back-compat field)
    return {"user_cost": uc, "K_total": kt, "r": r,
            "r_equity": r_equity, "r_debt": r_debt,
            "debt_weight_mean": (wsum / wk) if wk else 0.0, "corner": corner,
            "ai_share_corner": sc, "tickers": tickers, "detail": detail}
