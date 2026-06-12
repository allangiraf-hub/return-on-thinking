"""Central configuration: paths, universe, tags, series. Companion to METHODS.md."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
CURATED = DATA / "curated"
SERIES = DATA / "series"
ASSUMPTIONS = DATA / "assumptions"
DOCS = ROOT / "docs"
SITE_DATA = DOCS / "data"

EDGAR_USER_AGENT = "return-on-thinking (allan@aroscapital.com)"

UNIVERSE_FILE = CURATED / "universe.csv"   # ticker,bucket  (CIK resolved at runtime)

# XBRL tags in fallback order (inherited from potindicators; see its README).
TAG_CAPEX = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
]
TAG_OCF = ["NetCashProvidedByUsedInOperatingActivities"]
TAG_DEBT_ISSUED = [
    "ProceedsFromIssuanceOfLongTermDebt",
    "ProceedsFromIssuanceOfSeniorLongTermDebt",
    "ProceedsFromNotesPayable",
]

# FRED series for the user-cost r and macro context.
FRED_SERIES = {
    "DGS10": "10-year Treasury constant maturity (%)",
    "BAA10Y": "Moody's Baa corporate bond spread over 10-year Treasury (%)",
}

GPU_MODELS = ["H100 SXM", "H100 PCIE", "H200", "A100 SXM4", "RTX 4090", "B200"]

DAMODARAN_HISTIMPL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histimpl.xls"

# Census C30 (Value of Construction Put in Place) - data centre line.
CENSUS_VIP_API = "https://api.census.gov/data/timeseries/eits/vip"
