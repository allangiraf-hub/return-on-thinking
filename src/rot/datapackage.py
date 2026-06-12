"""Generate a Frictionless Data datapackage.json describing every published series.

Regenerated on each weekly run; lives at repo root and is included in releases,
so each Zenodo deposit carries its own machine-readable schema.
"""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from .config import ROOT, SERIES

LICENSE = {
    "name": "CC-BY-4.0",
    "title": "Creative Commons Attribution 4.0",
    "path": "https://creativecommons.org/licenses/by/4.0/",
}


def build() -> dict:
    resources = []
    for path in sorted(SERIES.glob("*.csv")):
        df = pd.read_csv(path, nrows=1)
        resources.append(
            {
                "name": path.stem,
                "path": f"data/series/{path.name}",
                "format": "csv",
                "schema": {"fields": [{"name": c, "type": "string" if c not in ("value",) else "number"} for c in df.columns]},
            }
        )
    resources.append(
        {
            "name": "deal-ledger",
            "path": "data/curated/ledger.csv",
            "format": "csv",
            "description": "AI financing deal ledger; every row carries a primary-source URL. Schema: schemas/ledger.schema.json",
        }
    )
    pkg = {
        "name": "return-on-thinking",
        "title": "The Return on Thinking - data on whether the AI boom pays for itself",
        "homepage": "https://returns.priceofthinking.com",
        "repository": "https://github.com/allangiraf-hub/return-on-thinking",
        "version": dt.date.today().isoformat(),
        "licenses": [LICENSE],
        "contributors": [{"title": "Allan Pedersen", "email": "allan@aroscapital.com", "role": "author"}],
        "description": "Compiled series on AI capital spending, financing fragility, and value coverage. Every row carries its public primary source URL, retrieval timestamp and evidence tier. Underlying facts remain the property of their sources (SEC, US Census, US Treasury, FRED, vast.ai, et al.). Cite the concept DOI when using this data.",
        "resources": resources,
    }
    (ROOT / "datapackage.json").write_text(json.dumps(pkg, indent=1))
    return pkg
