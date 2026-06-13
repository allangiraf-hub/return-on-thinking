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

# Cp covers every K-holder whose AI revenue is measurable. META is excluded:
# its AI is monetized through advertising uplift, not a revenue line, so neither
# its revenue nor its capital enters the coverage ratio (population consistency).
CP_FIRMS = ["MSFT", "AMZN", "GOOGL", "ORCL", "NBIS", "CRWV", "IREN", "APLD"]
STATED_FIRMS = ["MSFT", "AMZN", "NBIS"]          # stated AI ARR (T2)
CLOUD_FIRMS = {"GOOGL": "google_cloud_ai_share", "ORCL": "oracle_cloud_ai_share"}  # attributed (T3)
NEOCLOUD_FIRMS = ["CRWV", "IREN", "APLD"]        # total revenue, pure-play (T1)


def _ai_revenue(corner: str) -> tuple[float, list[dict]]:
    """AI-attributed revenue across the measurable firms, at a revenue corner.

    Stated AI ARR (best) + cloud-segment x AI-share (attributed) + neocloud total.
    """
    a = load()
    df = pd.read_csv(CURATED / "ai_revenue.csv")
    df["d"] = pd.to_datetime(df.call_date)
    contributors = []
    total = 0.0

    stated = df[(df.metric == "ai_arr") & (df.basis == "realized") & (df.ticker.isin(STATED_FIRMS))]
    for _, r in stated.sort_values("d").groupby("entity").tail(1).iterrows():
        total += r.value_usd_low
        contributors.append({"entity": r.entity, "value": r.value_usd_low, "basis": "stated AI ARR", "tier": "T2"})

    for tk, share_key in CLOUD_FIRMS.items():
        seg = df[(df.metric == "cloud_segment_revenue") & (df.ticker == tk)]
        if seg.empty:
            continue
        r = seg.sort_values("d").iloc[-1]
        share = a["revenue_attribution"][share_key][corner]
        v = r.value_usd_low * share
        total += v
        contributors.append({"entity": r.entity, "value": v, "basis": f"cloud x {int(share*100)}% AI", "tier": "T3"})

    neo = df[(df.metric == "neocloud_total_revenue") & (df.ticker.isin(NEOCLOUD_FIRMS))]
    for _, r in neo.sort_values("d").groupby("ticker").tail(1).iterrows():
        total += r.value_usd_low
        contributors.append({"entity": r.entity, "value": r.value_usd_low, "basis": "neocloud total", "tier": "T1"})

    return total, contributors


def cp_band() -> dict:
    a = load()
    m = a["quasi_rent_margin"]
    out = {}
    for name, (dc, mc, sc, rc) in {"high": ("low", "high", "low", "high"),
                                    "mid": ("mid", "mid", "mid", "mid"),
                                    "low": ("high", "low", "high", "low")}.items():
        rev, _ = _ai_revenue(rc)
        uc = user_cost(dc, tickers=CP_FIRMS, share_corner=sc)["user_cost"]
        out[name] = (rev * m[mc]) / uc if uc else None
    rev_mid, contributors = _ai_revenue("mid")
    ucm = user_cost("mid", tickers=CP_FIRMS)
    return {
        "cp_low": out["low"], "cp_mid": out["mid"], "cp_high": out["high"],
        "realized_ai_revenue_usd": rev_mid,
        "user_cost_mid_usd": ucm["user_cost"], "K_total_mid_usd": ucm["K_total"],
        "firms": CP_FIRMS, "contributors": contributors,
        "note": "v3: AI-attributed revenue of every measurable K-holder (stated AI ARR + cloud-segment x AI-share "
                "+ neocloud total) over the AI-attributed user cost of the same firms. Meta excluded "
                "(AI monetized via ad uplift, no revenue line). Population-consistent.",
    }


def _pv_flow(flow0: float, growth: float, disc: float, years: int) -> float:
    return sum(flow0 * (1 + growth) ** t / (1 + disc) ** t for t in range(years))


def _exposed_wage_bill() -> float:
    """Usage-weighted AI-exposed wage bill, summed over SOC major groups.
    Replaces the uniform macro W*e with a per-occupation sum (adversarial-review fix)."""
    df = pd.read_csv(CURATED / "occupations.csv")
    return float((df.employment_m * 1e6 * df.mean_wage_usd * df.ai_usage).sum())


def cs_band() -> dict:
    a = load()
    m = a["cs_macro"]
    disc = m["discount_rate"]
    exposed = _exposed_wage_bill()      # per-occupation Sigma(emp x wage x usage)
    out = {}
    for name, c in {"low": "low", "mid": "mid", "high": "high"}.items():
        s_share = m["appropriability_to_society"][c]
        # flow = exposed wage bill x productivity effect x adoption x social share
        flow0 = exposed * m["rct_effect"][c] * m["adoption_rate"][c] * s_share
        g = m["annual_growth"][c]
        uc = user_cost({"low": "high", "mid": "mid", "high": "low"}[name])["user_cost"]
        out[name] = {}
        for h in a["cs"]["horizons_years"]:
            out[name][f"h{h}"] = _pv_flow(flow0, g, disc, h) / _pv_flow(uc, 0.0, disc, h)
        out[name]["annual_flow_usd"] = flow0
    # macro cross-check (uniform exposure) for transparency
    macro_flow = m["us_employee_compensation_usd"] * m["ai_exposed_task_share"]["mid"] * m["rct_effect"]["mid"] * m["adoption_rate"]["mid"] * m["appropriability_to_society"]["mid"]
    return {
        "cs": out,
        "exposed_wage_bill_usd": exposed,
        "macro_crosscheck_flow_usd": macro_flow,
        "note": "v3: economy-wide AI productivity value built as a per-occupation sum over SOC major "
                "groups (usage-weighted wage bill x effect x adoption x social share), over the AI-attributed "
                "user cost of all K-holders. A projection, not realized value. 30y illustrative.",
    }
