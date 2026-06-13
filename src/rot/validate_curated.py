"""CI gate: curated files must satisfy their schemas; ledger rows must cite."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from .config import CURATED, ROOT

LEDGER = CURATED / "ledger.csv"
SCHEMA = json.loads((ROOT / "schemas" / "ledger.schema.json").read_text())
URL_PATTERN = re.compile(SCHEMA["properties"]["primary_source_url"]["pattern"])


def check_ledger() -> list[str]:
    errors = []
    if not LEDGER.exists():
        return errors
    with open(LEDGER) as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            for field in SCHEMA["required"]:
                if not row.get(field):
                    errors.append(f"ledger.csv line {i}: missing {field}")
            url = row.get("primary_source_url", "")
            if url and not URL_PATTERN.match(url):
                errors.append(f"ledger.csv line {i}: primary_source_url not an allowed primary domain: {url}")
            if row.get("instrument") and row["instrument"] not in SCHEMA["properties"]["instrument"]["enum"]:
                errors.append(f"ledger.csv line {i}: bad instrument {row['instrument']}")
    return errors


AI_REV = CURATED / "ai_revenue.csv"
AI_METRICS = {"ai_arr", "cloud_segment_run_rate", "ai_bookings", "ai_silicon_run_rate",
              "supply_side_context", "lab_arr", "contracted_arr"}
AI_BASIS = {"realized", "contracted", "guidance", "third_party"}


def check_ai_revenue() -> list[str]:
    errors = []
    if not AI_REV.exists():
        return errors
    with open(AI_REV) as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            for field in ("ticker", "entity", "call_date", "metric", "value_usd_low", "sentence", "tier"):
                if not row.get(field):
                    errors.append(f"ai_revenue.csv line {i}: missing {field}")
            if row.get("metric") and row["metric"] not in AI_METRICS:
                errors.append(f"ai_revenue.csv line {i}: bad metric {row['metric']}")
            if row.get("basis") and row["basis"] not in AI_BASIS:
                errors.append(f"ai_revenue.csv line {i}: bad basis {row['basis']}")
            if row.get("tier") not in {"T1", "T2", "T3"}:
                errors.append(f"ai_revenue.csv line {i}: bad tier {row.get('tier')}")
    return errors


def main() -> None:
    errors = check_ledger() + check_ai_revenue()
    for e in errors:
        print(f"::error::{e}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
