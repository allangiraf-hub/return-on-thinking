"""Historical backfill of the three numbers - v4.

Re-runs Cp, Cs and F at each past quarter-end from data we already hold, so the
dashboard shows a real TRAJECTORY rather than a single dot. The whole doctrine of
the project is "levels are unreliable, the movement is the signal" - which is
empty with one data point. This produces the movement.

What actually varies historically, and how sourced:
  - User cost (Cp & Cs denominator): perpetual inventory over filed quarterly
    capex TRUNCATED at each quarter-end (data/series/edgar_*_capex_q). Fully T1.
  - Cp numerator (AI revenue): the most recent figure a firm had STATED on an
    earnings call as of that quarter (data/curated/ai_revenue.csv, call_date
    filter). Zero before any firm disclosed AI revenue - an honest "switch-on".
  - F: trailing-4q capex vs operating cash flow per tier, truncated at quarter-end.
  - Cs numerator: the structural productivity-value flow (employment x wage x
    usage x effect x adoption x appropriability) is a forward PROJECTION and does
    not have a quarterly history; it is held at its assumption value, so only Cs's
    DENOMINATOR moves through history. Stated plainly on the page.

The risk-free rate is also taken as-of where the Treasury series reaches back,
else the assumptions fallback. Everything else (deltas, margins, adoption bands)
is a fixed assumption, so any movement on the fixed-mid line is real, not a
methods artifact - the project's core discipline.
"""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from .config import SITE_DATA
from .dials import cp_band, cs_band
from .fragility import fragility


def _quarter_ends(start: str, end: str) -> list[pd.Timestamp]:
    return list(pd.date_range(start=start, end=end, freq="QE"))


def _point(asof: pd.Timestamp) -> dict:
    cp = cp_band(asof=asof)
    cs = cs_band(asof=asof)
    frag = fragility(asof=asof)
    cs10 = {k: cs["cs"][k]["h10"] for k in ("low", "mid", "high")}
    q = f"{asof.year}-Q{(asof.month - 1)//3 + 1}"
    return {
        "quarter": q,
        "asof": asof.date().isoformat(),
        "cp": [cp["cp_low"], cp["cp_mid"], cp["cp_high"]],
        "cs10": [cs10["low"], cs10["mid"], cs10["high"]],
        "F": frag["F"], "stage": frag["stage"], "color": frag["color"],
        "ai_revenue_usd": cp["realized_ai_revenue_usd"],
        "user_cost_usd": cp["user_cost_mid_usd"],
        "K_total_usd": cp["K_total_mid_usd"],
    }


# The revision band on the fixed-mid line: not the wide assumption band, but the
# plausible restatement of the MID itself from data revisions and method tweaks.
# A move is only "called" when the mid leaves the prior quarter's revision band
# and stays out for the next quarter too (no single-quarter calls).
REVISION_BAND = 0.20  # +/-20% of the mid


def _mark_calls(series: list[dict], key: str) -> None:
    """Annotate each point with whether its mid 'called' a move vs the prior
    quarter's revision band, confirmed by the following quarter (2-quarter rule)."""
    mids = [p[key][1] if isinstance(p[key], list) else p[key] for p in series]
    for i, p in enumerate(series):
        called = None
        if i >= 1 and mids[i] is not None and mids[i - 1] is not None and mids[i - 1] > 0:
            prev = mids[i - 1]
            lo, hi = prev * (1 - REVISION_BAND), prev * (1 + REVISION_BAND)
            broke = mids[i] > hi or mids[i] < lo
            # confirmed only if the next quarter also stays beyond the prior band
            conf = (i + 1 < len(series) and mids[i + 1] is not None and
                    (mids[i + 1] > hi or mids[i + 1] < lo))
            if broke and conf:
                called = "up" if mids[i] > prev else "down"
        p.setdefault("calls", {})[key] = called


def backfill(start: str = "2023-03-31", end: str | None = None) -> dict:
    """Compute the quarterly trajectory and write docs/data/trajectory.json."""
    end = end or dt.date.today().isoformat()
    qends = _quarter_ends(start, end)
    series = [_point(qe) for qe in qends]
    # Append the live current-quarter snapshot (as of today) so the trajectory
    # connects continuously to the dashboard's live dot, rather than stopping at
    # the last completed quarter-end and hiding the latest (often largest) move.
    today = pd.Timestamp(dt.date.today())
    cur_q = f"{today.year}-Q{(today.month - 1)//3 + 1}"
    if not series or series[-1]["quarter"] != cur_q:
        cur = _point(today)
        cur["quarter"] = cur_q
        cur["provisional"] = True  # quarter not yet closed
        series.append(cur)
    for key in ("cp", "cs10", "F"):
        _mark_calls(series, key)

    payload = {
        "generated_at": dt.date.today().isoformat(),
        "revision_band": REVISION_BAND,
        "call_rule": (f"A move is 'called' only when the fixed-mid value leaves the prior "
                      f"quarter's +/-{int(REVISION_BAND*100)}% revision band AND the next quarter "
                      f"confirms it (two-quarter rule) - so single-quarter noise is never a call."),
        "note": ("Historical backfill. The capital stock (denominator) and F come from filed "
                 "capex/cash-flow truncated at each quarter-end; the Cp numerator is AI revenue "
                 "stated on or before each quarter; the Cs numerator is a fixed forward projection "
                 "(no quarterly history), so only its denominator moves. See methodology."),
        "series": series,
    }
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "trajectory.json").write_text(json.dumps(payload, indent=1, default=str))
    return {"quarters": len(series), "first": series[0]["quarter"], "last": series[-1]["quarter"]}
