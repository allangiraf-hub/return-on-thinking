"""User cost of the AI capital stock: UC = Sum_i (r_i + delta_i) K_i.

K is built by perpetual inventory from filed quarterly capex of the K-holder
universe (hyperscalers + neoclouds), split across asset classes by the
allocation shares in the assumptions file. This treats recent capex of these
firms as AI-attributable - an acknowledged upper bound on AI capital, stated
on the methodology page. r combines the Treasury 10y and the equity premium;
delta is taken at low/mid/high corners. Returns the user cost at each corner.
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .seriesio import read_series
from .universe import load_universe

CLASS_KEYS = {"chips_servers": "chips_servers", "buildings": "buildings", "power_cooling_other": "power_cooling_other"}


def _kholder_capex_quarterly() -> pd.DataFrame:
    """Summed quarterly capex across hyperscalers + neoclouds (USD)."""
    uni = load_universe()
    frames = []
    for _, firm in uni[uni.bucket.isin(["hyperscaler", "neocloud"])].iterrows():
        t = firm.ticker.lower()
        for sid in (f"edgar_{t}_capex_q", f"fmp_{t}_capex_q"):
            try:
                df = read_series(sid)[["date", "value"]].copy()
                frames.append(df)
                break
            except FileNotFoundError:
                continue
    allcx = pd.concat(frames)
    allcx["q"] = allcx["date"].dt.to_period("Q")
    return allcx.groupby("q")["value"].sum().reset_index().sort_values("q")


def _perpetual_inventory(capex_q: pd.Series, delta_annual: float) -> float:
    """Installed stock after running quarterly capex through PIM at given delta."""
    dq = 1 - (1 - delta_annual) ** 0.25  # quarterly depreciation
    k = 0.0
    for cx in capex_q:
        k = k * (1 - dq) + cx
    return k


def user_cost(corner: str = "mid") -> dict:
    """User cost ($/yr) and the K it rests on, at a delta corner (low/mid/high)."""
    a = load()
    cx = _kholder_capex_quarterly()
    # required return (decimal): risk-free + equity premium, from the rate series.
    try:
        rf = read_series("treasury_10y")["value"].iloc[-1] / 100
    except FileNotFoundError:
        rf = a["r"].get("risk_free_fallback", 0.045)
    erp = a["r"].get("erp_fallback", 0.043)
    r = rf + erp
    alloc = a["k_allocation"]["hyperscaler"]
    uc, kt = 0.0, 0.0
    detail = {}
    for cls, share in alloc.items():
        band = a["delta"][cls]
        delta = band[{"low": "low", "mid": "mid", "high": "high"}[corner]]
        k_cls = _perpetual_inventory(cx["value"] * share, delta)
        uc += (r + delta) * k_cls
        kt += k_cls
        detail[cls] = {"K": k_cls, "delta": delta}
    return {"user_cost": uc, "K_total": kt, "r": r, "corner": corner, "detail": detail}
