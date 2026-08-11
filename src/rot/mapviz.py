"""Assemble the quarterly dials + map payloads for the website.

Writes docs/data/dials.json (the three dials with bands) and docs/data/map.json,
whose trail is REBUILT from the restated back-series (trajectory.json) on every
run - not appended to. The map plots the private-vs-social coverage quadrant;
Cs uses the 10-year horizon for the axis, with the 30-year value carried alongside.

v5.2 (2026-08-11 audit): the trail used to be append-only, so points written
under superseded assumptions were never restated - map.json's 2026-Q2 point was
still carrying the pre-July F 0.664 / Cs 0.640 while trajectory.json restated the
same quarter. Nothing on the site rendered that array (index.html draws the trail
from trajectory.json), but it was served publicly and contradicted the project's
rule that any assumption change republishes the whole back-series. It is now
derived, so it self-heals; the declared map.trail_quarters is finally honoured
(it was defined-but-unused, the code hard-coding 8).
"""
from __future__ import annotations

import datetime as dt
import json

from .config import SITE_DATA
from .assumptions import load
from .dials import cp_band, cs_band, cp_ecosystem_band
from .fragility import fragility
from .ticker import build as build_ticker  # reuse F1 etc.

MAP_FILE = SITE_DATA / "map.json"
TRAJ_FILE = SITE_DATA / "trajectory.json"

# Single source of truth for the version string the site prints (v5.2 audit:
# this was hard-coded to "v5" here while the methodology page and the working
# paper had moved to v5.2).
METHODOLOGY_VERSION = "v5.2"


def _trail_from_trajectory(n: int, q: str, point: dict) -> list:
    """Last `n` quarters of the restated back-series, with the live point last.

    trajectory.json holds [low, mid, high] triples per quarter, the same shape
    the map point uses, so the restated history maps straight across."""
    if not TRAJ_FILE.exists():
        return [point]
    series = json.loads(TRAJ_FILE.read_text()).get("series", [])
    trail = []
    for r in series:
        if r.get("quarter") == q:
            continue  # the live point supersedes any backfilled current quarter
        trail.append({
            "quarter": r["quarter"], "generated_at": r.get("asof", ""),
            "cp": r["cp"], "cs10": r["cs10"], "cs30": r.get("cs30", r["cs10"]),
            "F": r["F"], "stage": r["stage"], "color": r["color"],
            "restated": True,
        })
    return trail[-(max(1, n) - 1):] + [point] if n > 1 else [point]


def _quarter_label(d: dt.date) -> str:
    return f"{d.year}-Q{(d.month - 1)//3 + 1}"


def assemble() -> dict:
    cp = cp_band()
    cs = cs_band()
    cs10 = {k: cs["cs"][k]["h10"] for k in ("low", "mid", "high")}
    cs30 = {k: cs["cs"][k]["h30"] for k in ("low", "mid", "high")}
    frag = fragility()
    now = dt.date.today()
    q = _quarter_label(now)

    point = {
        "quarter": q, "generated_at": now.isoformat(),
        "cp": [cp["cp_low"], cp["cp_mid"], cp["cp_high"]],
        "cs10": [cs10["low"], cs10["mid"], cs10["high"]],
        "cs30": [cs30["low"], cs30["mid"], cs30["high"]],
        "F": frag["F"], "stage": frag["stage"], "color": frag["color"],
    }

    # Trail: rebuilt from the restated back-series so it can never carry a
    # superseded vintage (v5.2 audit). Falls back to the current point alone if
    # the trajectory has not been built yet (first run / fresh checkout).
    n_trail = int(load()["map"].get("trail_quarters", 4))
    trail = _trail_from_trajectory(n_trail, q, point)

    qr_flow = cp["realized_ai_revenue_usd"] * load()["quasi_rent_margin"]["mid"]
    flows = {"private_earnings_flow_usd": qr_flow,
             "social_value_flow_usd": cs["cs"]["mid"]["annual_flow_usd"],
             "capital_cost_usd": cp["user_cost_mid_usd"]}
    dials = {
        "generated_at": now.isoformat(), "quarter": q,
        "earnings_cp": cp,
        "earnings_cp_ecosystem": cp_ecosystem_band(),
        "benefit_cs": cs,
        "fragility_f": frag,
        "flows": flows,
        "methodology_version": METHODOLOGY_VERSION,
    }
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "dials.json").write_text(json.dumps(dials, indent=1, default=str))
    MAP_FILE.write_text(json.dumps({
        "generated_at": now.isoformat(),
        "trail": trail,
        "historical_booms": _historical_booms(),
        "thresholds": {"breakeven": 1.0},
    }, indent=1))

    # detail payloads for the three dial pages
    import pandas as pd
    from .seriesio import read_series as _rs
    from .config import CURATED as _CUR
    def _series_json(sid, keep=120, cols=("date","value")):
        try:
            df = _rs(sid).sort_values("date").tail(keep)
        except FileNotFoundError:
            return None
        df = df.assign(date=df["date"].dt.date.astype(str))
        return json.loads(df[list(cols)].to_json(orient="records"))
    detail = {
        "construction": _series_json("census_datacenter_construction"),
        "gpu_rental": _series_json("vastai_gpu_rental", keep=4000, cols=("date","value","gpu_model")) if (SITE_DATA.parent.parent/"data"/"series"/"vastai_gpu_rental.csv").exists() else None,
        "elec": {st: _series_json(f"eia_elec_price_{st}") for st in ("va","tx","oh","ia","or","az")},
        "ai_revenue": json.loads(pd.read_csv(_CUR/"ai_revenue.csv").to_json(orient="records")) if (_CUR/"ai_revenue.csv").exists() else [],
        "ledger": json.loads(pd.read_csv(_CUR/"ledger.csv").to_json(orient="records")) if (_CUR/"ledger.csv").exists() else [],
    }
    (SITE_DATA/"detail.json").write_text(json.dumps(detail, indent=1, default=str))
    build_ticker()  # refresh the weekly ticker too
    return {"quarter": q, "cp_mid": cp["cp_mid"], "cs10_mid": cs10["mid"], "F": frag["F"], "stage": frag["stage"]}


def _historical_booms() -> list:
    """Sourced placements of past technology booms - real economic-history figures,
    placed ORDINALLY on the same axes (cross-era units differ; see caveat per row).
    Replaces the earlier hand-drawn schematic curves."""
    import pandas as pd
    from .config import CURATED as _C
    p = _C / "historical_booms.csv"
    if not p.exists():
        return []
    df = pd.read_csv(p)
    out = []
    for _, r in df.iterrows():
        out.append({
            "id": r.id, "name": r["name"], "era": r.era,
            "cp": [float(r.cp_low), float(r.cp_high)],
            "cs": [float(r.cs_low), float(r.cs_high)],
            "stage": r.fragility_stage, "color": r.fragility_color,
            "citation": r.citation, "caveat": r.caveat,
        })
    return out
