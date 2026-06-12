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


def main() -> None:
    errors = check_ledger()
    for e in errors:
        print(f"::error::{e}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
