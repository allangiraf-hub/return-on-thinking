"""The three dials, assembled at the assumption corners.

Cp (earnings) = quasi-rents / user cost. Quasi-rents = realized AI-attributable
revenue x margin band. Only REALIZED revenue feeds Cp; guidance/contracted are
carried as forward markers, never in the level. Foreign-filer and chipmaker
context rows are excluded from the K-holder numerator per the consolidation rule.
"""
from __future__ import annotations

import pandas as pd

from .assumptions import load
from .config import CURATED
from .usercost import user_cost

# metrics that count as K-holder AI revenue (not chipmaker, not cloud-total context)
CP_METRICS = {"ai_arr"}
KHOLDER_TICKERS = {"MSFT", "GOOGL", "AMZN", "META", "ORCL", "CRWV", "NBIS", "APLD", "IREN"}


def _latest_realized_ai_revenue() -> tuple[float, list[dict]]:
    """Most recent REALIZED ai_arr per K-holder entity, summed."""
    df = pd.read_csv(CURATED / "ai_revenue.csv")
    df = df[(df.metric.isin(CP_METRICS)) & (df.basis == "realized") & (df.ticker.isin(KHOLDER_TICKERS))]
    if df.empty:
        return 0.0, []
    df["d"] = pd.to_datetime(df.call_date)
    latest = df.sort_values("d").groupby("entity").tail(1)
    rows = latest[["entity", "value_usd_low", "call_date"]].to_dict("records")
    return float(latest["value_usd_low"].sum()), rows


def cp_band() -> dict:
    """Cp at low/mid/high corners (delta x margin), plus the inputs."""
    a = load()
    rev, contributors = _latest_realized_ai_revenue()
    m = a["quasi_rent_margin"]
    out = {}
    # earnings-friendly corner = low delta (small UC) x high margin (big QR); and vice-versa
    for name, (dc, mc) in {"high": ("low", "high"), "mid": ("mid", "mid"), "low": ("high", "low")}.items():
        uc = user_cost(dc)["user_cost"]
        qr = rev * m[mc]
        out[name] = qr / uc if uc else None
    return {
        "cp_low": out["low"], "cp_mid": out["mid"], "cp_high": out["high"],
        "realized_ai_revenue_usd": rev,
        "user_cost_mid_usd": user_cost("mid")["user_cost"],
        "K_total_mid_usd": user_cost("mid")["K_total"],
        "contributors": contributors,
        "note": "Cp = realized AI quasi-rents / user cost of installed stock. "
                "Realized K-holder AI revenue only; guidance excluded. Corners span "
                "delta x margin. Levels uncertain to a factor of several - watch the trajectory.",
    }


def _pv_flow(flow0: float, growth: float, disc: float, years: int) -> float:
    """Present value of a growing annual value flow over a horizon."""
    return sum(flow0 * (1 + growth) ** t / (1 + disc) ** t for t in range(years))


def cs_band() -> dict:
    """Social-return coverage Cs at 10- and 30-year horizons, low/mid/high corners.

    Annual social value flow = wage bill x AI-exposed task share x productivity
    effect x adoption x social-appropriability share. Compared to the present
    value of the user cost over the horizon. A BOUNDED ESTIMATE, gross of harms.
    """
    a = load()
    m = a["cs_macro"]
    wage = m["us_employee_compensation_usd"]
    disc = m["discount_rate"]
    soc = m["appropriability_to_society"]
    out = {}
    for name, c in {"low": "low", "mid": "mid", "high": "high"}.items():
        flow0 = wage * m["ai_exposed_task_share"][c] * m["rct_effect"][c] * m["adoption_rate"][c] * soc
        g = m["annual_growth"][c]
        uc = user_cost({"low": "high", "mid": "mid", "high": "low"}[name])["user_cost"]
        out[name] = {}
        for h in a["cs"]["horizons_years"]:
            pv_value = _pv_flow(flow0, g, disc, h)
            pv_uc = _pv_flow(uc, 0.0, disc, h)
            out[name][f"h{h}"] = pv_value / pv_uc if pv_uc else None
        out[name]["annual_flow_usd"] = flow0
    return {
        "cs": out,
        "note": "Social return: time saved/work improved valued against user cost, "
                "at 10y and 30y horizons. Bounded estimate with biases in both directions; "
                "gross of harms (see electricity-price and layoff indicators). NOT a floor.",
    }
