"""Assemble the quarterly dials + map payloads for the website.

Writes docs/data/dials.json (the three dials with bands) and appends the
current (Cp, Cs) position to docs/data/map.json's trail. The map plots the
private-vs-social coverage quadrant; Cs uses the 10-year horizon for the axis,
with the 30-year value carried alongside.
"""
from __future__ import annotations

import datetime as dt
import json

from .config import SITE_DATA
from .dials import cp_band, cs_band
from .fragility import fragility
from .ticker import build as build_ticker  # reuse F1 etc.

MAP_FILE = SITE_DATA / "map.json"


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

    # append to trail (idempotent within a quarter)
    trail = []
    if MAP_FILE.exists():
        trail = json.loads(MAP_FILE.read_text()).get("trail", [])
    trail = [p for p in trail if p["quarter"] != q] + [point]
    trail = trail[-8:]  # keep last 8 quarters

    dials = {
        "generated_at": now.isoformat(), "quarter": q,
        "earnings_cp": cp,
        "benefit_cs": cs,
        "fragility_f": frag,
        "methodology_version": "v1",
    }
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "dials.json").write_text(json.dumps(dials, indent=1, default=str))
    MAP_FILE.write_text(json.dumps({
        "generated_at": now.isoformat(),
        "trail": trail,
        "historical_paths": _historical_paths(),
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


def _historical_paths() -> list:
    """Digitized illustrative trajectories of past technology booms (static).
    Coordinates are (private coverage, social coverage) at successive phases -
    schematic, for visual comparison, sourced in METHODS.md."""
    return [
        {"name": "Railways 1840s-70s", "kind": "productive_bubble",
         "points": [[0.15, 0.6], [0.3, 0.9], [0.55, 1.3]]},
        {"name": "Telecoms fibre 1996-2006", "kind": "productive_bubble",
         "points": [[0.12, 0.5], [0.25, 0.8], [0.45, 1.15]]},
        {"name": "Cloud 2012-19 (ended well)", "kind": "healthy_boom",
         "points": [[0.5, 0.7], [0.8, 1.0], [1.1, 1.25]]},
    ]
