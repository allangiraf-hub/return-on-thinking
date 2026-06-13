"""The coverage dials - v2 (population-consistent, per adversarial review 2026-06-13).

Cp: AI-attributed revenue of the firms that disclose it, over the AI-attributed
user cost of THOSE SAME firms (no 3-vs-9 population mismatch).
Cs: economy-wide social-value flow over the AI-attributed user cost of ALL
K-holders (decoupled from Cp's denominator, so the map axes are not mechanically
linked by a shared UC). Banded appropriability; 30y horizon illustrative only.
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .config import CURATED
from .usercost import user_cost

# firms with a stated, realized AI revenue figure -> the Cp-measurable set
CP_FIRMS = ["MSFT", "AMZN", "NBIS"]


def _realized_ai_revenue(firms: list[str]) -> tuple[float, list[dict]]:
    df = pd.read_csv(CURATED / "ai_revenue.csv")
    df = df[(df.metric == "ai_arr") & (df.basis == "realized") & (df.ticker.isin(firms))]
    if df.empty:
        return 0.0, []
    df["d"] = pd.to_datetime(df.call_date)
    latest = df.sort_values("d").groupby("entity").tail(1)
    return float(latest["value_usd_low"].sum()), latest[["entity", "value_usd_low", "call_date"]].to_dict("records")


def cp_band() -> dict:
    a = load()
    rev, contributors = _realized_ai_revenue(CP_FIRMS)
    m = a["quasi_rent_margin"]
    out = {}
    # favourable corner: high margin x low delta UC x low AI-share (less capital attributed)
    for name, (dc, mc, sc) in {"high": ("low", "high", "low"),
                                "mid": ("mid", "mid", "mid"),
                                "low": ("high", "low", "high")}.items():
        uc = user_cost(dc, tickers=CP_FIRMS, share_corner=sc)["user_cost"]
        out[name] = (rev * m[mc]) / uc if uc else None
    ucm = user_cost("mid", tickers=CP_FIRMS)
    return {
        "cp_low": out["low"], "cp_mid": out["mid"], "cp_high": out["high"],
        "realized_ai_revenue_usd": rev,
        "user_cost_mid_usd": ucm["user_cost"], "K_total_mid_usd": ucm["K_total"],
        "firms": CP_FIRMS, "contributors": contributors,
        "note": "v2: AI-attributed revenue of the firms that disclose it, over the AI-attributed "
                "user cost of the same firms. Population-consistent. Realized only; guidance excluded.",
    }


def _pv_flow(flow0: float, growth: float, disc: float, years: int) -> float:
    return sum(flow0 * (1 + growth) ** t / (1 + disc) ** t for t in range(years))


def cs_band() -> dict:
    a = load()
    m = a["cs_macro"]
    wage, disc = m["us_employee_compensation_usd"], m["discount_rate"]
    out = {}
    for name, c in {"low": "low", "mid": "mid", "high": "high"}.items():
        s = m["appropriability_to_society"][c]
        flow0 = wage * m["ai_exposed_task_share"][c] * m["rct_effect"][c] * m["adoption_rate"][c] * s
        g = m["annual_growth"][c]
        # social value comes from ALL AI capital deployed -> 9-firm AI-attributed UC
        uc = user_cost({"low": "high", "mid": "mid", "high": "low"}[name])["user_cost"]
        out[name] = {}
        for h in a["cs"]["horizons_years"]:
            out[name][f"h{h}"] = _pv_flow(flow0, g, disc, h) / _pv_flow(uc, 0.0, disc, h)
        out[name]["annual_flow_usd"] = flow0
    return {
        "cs": out,
        "note": "v2: economy-wide AI productivity value (banded appropriability) over the AI-attributed "
                "user cost of all K-holders. A projection, not realized value. 30-year horizon illustrative.",
    }
