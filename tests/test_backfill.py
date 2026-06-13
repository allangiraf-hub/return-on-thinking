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
