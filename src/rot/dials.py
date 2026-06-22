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
from .seriesio import read_series
from .usercost import user_cost

# Cp covers every K-holder whose AI revenue is measurable. META is excluded:
# its AI is monetized through advertising uplift, not a revenue line, so neither
# its revenue nor its capital enters the coverage ratio (population consistency).
CP_FIRMS = ["MSFT", "AMZN", "GOOGL", "ORCL", "NBIS", "CRWV", "IREN", "APLD"]
STATED_FIRMS = ["MSFT", "AMZN", "NBIS"]          # stated AI ARR (T2)
CLOUD_FIRMS = {"GOOGL": "google_cloud_ai_share", "ORCL": "oracle_cloud_ai_share"}  # attributed (T3)
NEOCLOUD_FIRMS = ["CRWV", "IREN", "APLD"]        # total revenue, pure-play (T1)
_NEO_NAME = {"CRWV": "CoreWeave", "IREN": "IREN", "APLD": "Applied Digital"}
_CLOUD_NAME = {"GOOGL": "Google Cloud", "ORCL": "Oracle"}


def _neocloud_trailing4(tk: str, asof=None):
    """Self-refreshing neocloud revenue: trailing-4q from the auto-collected
    fmp_<t>_revenue_q series (v5). Returns None if the series is absent so the
    caller can fall back to the pinned ai_revenue.csv value."""
    try:
        s = read_series(f"fmp_{tk.lower()}_revenue_q").sort_values("date")
    except FileNotFoundError:
        return None
    if asof is not None:
        s = s[s["date"] <= pd.Timestamp(asof)]
    s = s.tail(4)
    return float(s["value"].sum()) if len(s) == 4 else None


def _cloud_segment(tk: str, asof=None):
    """Self-refreshing cloud-segment revenue: latest annual fmp_<t>_cloud_segment_rev_a
    as of `asof` (v5). None if absent -> caller falls back to pinned CSV."""
    try:
        s = read_series(f"fmp_{tk.lower()}_cloud_segment_rev_a").sort_values("date")
    except FileNotFoundError:
        return None
    if asof is not None:
        s = s[s["date"] <= pd.Timestamp(asof)]
    return float(s["value"].iloc[-1]) if len(s) else None


def _ai_revenue(corner: str, asof=None) -> tuple[float, list[dict]]:
    """AI-attributed revenue across the measurable firms, at a revenue corner.

    Stated AI ARR (best) + cloud-segment x AI-share (attributed) + neocloud total.
    asof: if given, only count figures stated on an earnings call ON OR BEFORE
        that date - so the historical backfill uses what was known then, and the
        numerator switches on as firms first disclosed AI revenue.
    """
    a = load()
    df = pd.read_csv(CURATED / "ai_revenue.csv")
    df["d"] = pd.to_datetime(df.call_date)
    if asof is not None:
        df = df[df["d"] <= pd.Timestamp(asof)]
    contributors = []
    total = 0.0

    stated = df[(df.metric == "ai_arr") & (df.basis == "realized") & (df.ticker.isin(STATED_FIRMS))]
    for _, r in stated.sort_values("d").groupby("entity").tail(1).iterrows():
        total += r.value_usd_low
        contributors.append({"entity": r.entity, "value": r.value_usd_low, "basis": "stated AI ARR", "tier": "T2"})

    for tk, share_key in CLOUD_FIRMS.items():
        # Switch-on discipline (v5.1 fix): recognise AI-attributed cloud revenue
        # only once the firm has DISCLOSED a cloud-segment figure on an earnings
        # call as of `asof` (a row in ai_revenue.csv; df is already asof-filtered).
        # The self-refreshing fmp annual series reaches back into the pre-AI era
        # (GOOGL to 2018, ORCL to 2013), so using it unconditionally back-projects
        # AI revenue into years before any disclosure - violating the backfill
        # "switch-on" doctrine and overstating the historical numerator.
        seg = df[(df.metric == "cloud_segment_revenue") & (df.ticker == tk)]
        if seg.empty:
            continue  # not yet disclosed as of `asof` -> contributes zero
        # disclosed: prefer the self-refreshing fmp segment value; else the pinned figure.
        seg_rev = _cloud_segment(tk, asof)
        src = "auto"
        if seg_rev is None:
            seg_rev = float(seg.sort_values("d").iloc[-1].value_usd_low)
            src = "pinned"
        share = a["revenue_attribution"][share_key][corner]
        v = seg_rev * share
        total += v
        contributors.append({"entity": _CLOUD_NAME.get(tk, tk), "value": v,
                             "basis": f"cloud x {int(share*100)}% AI ({src})", "tier": "T3"})

    for tk in NEOCLOUD_FIRMS:
        # v5: prefer trailing-4q from the self-refreshing revenue series; fall back to CSV.
        neo_rev = _neocloud_trailing4(tk, asof)
        src = "auto"
        if neo_rev is None:
            neo = df[(df.metric == "neocloud_total_revenue") & (df.ticker == tk)]
            if neo.empty:
                continue
            neo_rev = float(neo.sort_values("d").iloc[-1].value_usd_low)
            src = "pinned"
        total += neo_rev
        contributors.append({"entity": _NEO_NAME.get(tk, tk), "value": neo_rev,
                             "basis": f"neocloud total ({src})", "tier": "T1"})

    return total, contributors


def cp_band(asof=None) -> dict:
    a = load()
    m = a["quasi_rent_margin"]
    out = {}
    for name, (dc, mc, sc, rc) in {"high": ("low", "high", "low", "high"),
                                    "mid": ("mid", "mid", "mid", "mid"),
                                    "low": ("high", "low", "high", "low")}.items():
        rev, _ = _ai_revenue(rc, asof=asof)
        uc = user_cost(dc, tickers=CP_FIRMS, share_corner=sc, asof=asof)["user_cost"]
        out[name] = (rev * m[mc]) / uc if uc else None
    rev_mid, contributors = _ai_revenue("mid", asof=asof)
    ucm = user_cost("mid", tickers=CP_FIRMS, asof=asof)
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


def cs_band(asof=None) -> dict:
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
        uc = user_cost({"low": "high", "mid": "mid", "high": "low"}[name], asof=asof)["user_cost"]
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
