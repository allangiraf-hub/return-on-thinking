"""Fragility index F - v3 (S9.3): located leverage now folds in the deal ledger.

v2 was F = max(centre, edge) from filed capex/OCF only, with the ledger's circular deals
merely COUNTED. v3 folds the ledger in, per working-paper S9.3:
  * the SPV/ABS finance engineered to stay OUT of the filed capex/OCF ratio (abs + spv
    instruments) enters the weakest-link max as an off-balance-sheet leverage intensity;
  * the reciprocal-capital (circularity) bonus already specified in the assumptions file
    is now actually applied (it was defined but unused in v2).
Both ledger terms are as-of aware (filtered by announced_date), so the historical
trajectory shows leverage ACCUMULATING rather than today's ledger stamped on 2023.
Equity finance is excluded from the leverage term (it absorbs losses); its circular
share is captured by the circularity bonus. The ledger intensity is coarse (commitments
not draws; discovery/survivorship bias) and is reported so the reader can see it; it
binds the headline only when it exceeds the filed edge.
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .config import CURATED
from .seriesio import read_series
from .universe import load_universe

STAGE_COLOR = {"hedge": "#1D9E75", "speculative": "#BA7517", "ponzi": "#E24B4A"}

_OFF_BALANCE = ("abs", "spv")                                   # engineered to stay out of the ratio
_DEBT_LIKE = ("private_credit", "convertible_notes", "abs", "spv")


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


def _ai_capex_ttm(asof=None) -> float:
    """Trailing-4q AI-attributed capex of all K-holders (mid ai_share) - the coarse
    denominator that turns ledger dollars into an intensity comparable to the ext-share."""
    a = load()
    uni = load_universe().set_index("ticker")
    tot = 0.0
    for tk in uni.index:
        bucket = uni.loc[tk, "bucket"]
        if bucket not in ("hyperscaler", "neocloud"):
            continue
        c = _t4(f"edgar_{tk.lower()}_capex_q", asof) or _t4(f"fmp_{tk.lower()}_capex_q", asof)
        if c:
            tot += c * a["ai_capex_share"][bucket]["mid"]
    return tot


def _ledger(asof=None) -> pd.DataFrame:
    p = CURATED / "ledger.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["amt"] = pd.to_numeric(df["amount_usd"], errors="coerce").fillna(0.0)
    df["d"] = pd.to_datetime(df["announced_date"], errors="coerce")
    if asof is not None:
        df = df[df["d"] <= pd.Timestamp(asof)]
    return df


def _circularity_flags(df: pd.DataFrame) -> int:
    if df.empty or "circularity_flag" not in df.columns:
        return 0
    return int(df["circularity_flag"].astype(str).str.lower().isin(["true", "1"]).sum())


def fragility(asof=None) -> dict:
    a = load()["fragility"]
    uni = load_universe()
    centre = _ext_share(uni[uni.bucket == "hyperscaler"]["ticker"].tolist(), asof=asof) or 0.0
    edge = _ext_share(uni[uni.bucket == "neocloud"]["ticker"].tolist(), asof=asof) or 0.0

    led = _ledger(asof=asof)
    inst = led["instrument"].astype(str) if not led.empty else pd.Series(dtype=str)
    off_bs = float(led.loc[inst.isin(_OFF_BALANCE), "amt"].sum()) if not led.empty else 0.0
    debt_like = float(led.loc[inst.isin(_DEBT_LIKE), "amt"].sum()) if not led.empty else 0.0
    equity = float(led.loc[inst.eq("equity"), "amt"].sum()) if not led.empty else 0.0
    flags = _circularity_flags(led)
    capex_ttm = _ai_capex_ttm(asof=asof)

    # off-balance-sheet leverage intensity: SPV/ABS finance kept out of the filed ratio,
    # scaled by AI capex; coarse (commitments, discovery bias) - see module docstring.
    off_bs_intensity = min(1.0, off_bs / capex_ttm) if capex_ttm else 0.0

    # weakest link now includes the off-balance-sheet ledger leverage.
    base = max(0.0, min(1.0, max(centre, edge, off_bs_intensity)))
    # reciprocal-capital bonus (previously specified but unused): flags/full_at, capped.
    full_at = max(1, int(a.get("circularity_full_at", 6)))
    circ = float(a.get("circularity_bonus", 0.0)) * min(1.0, flags / full_at)
    F = max(0.0, min(1.0, base + circ))

    th = a["stage_thresholds"]
    stage = "hedge" if F < th["hedge"] else "speculative" if F < th["speculative"] else "ponzi"
    return {
        "F": F, "stage": stage, "color": STAGE_COLOR[stage],
        "components": {
            "centre_external_share": centre,
            "edge_external_share": edge,
            "off_balance_ledger_intensity": off_bs_intensity,
            "circularity_flags": flags,
            "circularity_bonus_applied": circ,
            "ledger_debt_like_usd": debt_like,
            "ledger_off_balance_debt_usd": off_bs,
            "ledger_equity_usd": equity,
            "ai_capex_ttm_usd": capex_ttm,
            "edge_plus_offbalance_variant": min(1.0, edge + off_bs_intensity),
        },
        "note": "v3 (S9.3): F = max(centre, edge, off-balance ledger leverage) + circularity bonus. "
                "The weakest-link located leverage now includes SPV/ABS finance engineered to stay out "
                "of the filed capex/OCF ratio, plus a reciprocal-capital bonus. Ledger intensity is "
                "coarse (commitments not draws; discovery bias), reported, and binds only if it exceeds "
                "the filed edge; equity finance is excluded from leverage.",
    }
