"""The historical backfill must produce a real, sourced trajectory:
- the AI-attributed capital stock grows monotonically as capex accumulates;
- the earnings numerator is zero before any firm disclosed AI revenue, then
  switches on (no backward-projected guesses);
- the final backfilled point matches the live dial (continuity);
- the as-of truncation is monotone (a later cutoff never has a smaller stock).
"""
from __future__ import annotations

import pandas as pd

from rot.backfill import backfill, _point
from rot.dials import cp_band


def test_trajectory_shape_and_continuity():
    out = backfill(start="2023-03-31")
    import json
    from rot.config import SITE_DATA
    tj = json.loads((SITE_DATA / "trajectory.json").read_text())
    s = tj["series"]
    assert len(s) >= 12

    # capital stock grows monotonically (perpetual inventory over accumulating capex)
    Ks = [p["K_total_usd"] for p in s]
    assert all(b >= a - 1 for a, b in zip(Ks, Ks[1:])), "stock should not shrink over time"
    assert Ks[-1] > Ks[0] * 1.5, "stock should grow materially across the boom"

    # earnings numerator switches on: zero early, positive late
    rev = [p["ai_revenue_usd"] for p in s]
    assert rev[0] == 0, "no AI revenue disclosed at the start"
    assert rev[-1] > 0, "AI revenue disclosed by the latest quarter"

    # continuity: the final backfilled point matches the live cp_band mid
    live = cp_band()["cp_mid"]
    assert abs(s[-1]["cp"][1] - live) < 1e-6, "trajectory endpoint must equal the live dial"


def test_asof_truncation_is_monotone():
    early = _point(pd.Timestamp("2024-03-31"))["K_total_usd"]
    late = _point(pd.Timestamp("2025-03-31"))["K_total_usd"]
    assert late > early, "a later as-of cutoff must include more capex, so a larger stock"


def test_revenue_self_refresh_path():
    """v5: neocloud + cloud-segment revenue come from the auto-collected fmp_*
    series (trailing-4q / latest annual), and the contributors are tagged 'auto'
    when the series is present. Reconciles with the filings we validated against."""
    from rot.dials import _ai_revenue, _neocloud_trailing4
    import pandas as pd
    rev, contribs = _ai_revenue("mid")
    autos = [c for c in contribs if "(auto)" in c["basis"]]
    assert autos, "expected the self-refreshing series to drive neocloud/cloud lines"
    # CoreWeave trailing-4q must match the validated ~$6.23bn filing sum
    crwv = _neocloud_trailing4("CRWV", pd.Timestamp("2026-03-31"))
    assert crwv is not None and abs(crwv - 6.227e9) < 5e7


def test_debt_equity_split_active():
    """The blended required return must sit between the all-debt and all-equity
    bounds, and leaning on debt must lower the blended cost (debt is cheaper)."""
    from rot.usercost import user_cost, _debt_weight
    import pandas as pd
    u = user_cost("mid")
    assert u["r_debt"] < u["r_equity"], "debt return (rf+Baa) must be below equity (rf+ERP)"
    assert 0.0 <= u["debt_weight_mean"] <= 1.0
    # a heavily debt-funded neocloud should carry a non-trivial debt weight
    assert _debt_weight("CRWV", pd.Timestamp("2026-03-31")) > 0.1
