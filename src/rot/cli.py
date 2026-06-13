"""CLI: python -m rot.cli {weekly|ticker|<collector>}"""
from __future__ import annotations

import sys
import traceback

from .collectors import census_c30, damodaran, edgar, eia, fmp, fmp_revenue, fred, treasury, vastai
from . import backfill as backfill_mod, datapackage, mapviz, ticker

COLLECTORS = {
    "edgar": edgar.run,
    "fred": fred.run,
    "treasury": treasury.run,
    "fmp": fmp.run,
    "fmp_revenue": fmp_revenue.run,
    "eia": eia.run,
    "vastai": vastai.run,
    "damodaran": damodaran.run,
    "census_c30": census_c30.run,
}


def weekly() -> int:
    """Run all collectors; a single dead source must not kill the run
    (the canary reports it), but the job exits nonzero so CI flags it."""
    failures = []
    for name, fn in COLLECTORS.items():
        try:
            written = fn()
            print(f"[ok] {name}: {written}")
        except Exception:
            failures.append(name)
            print(f"[FAIL] {name}")
            traceback.print_exc()
    try:
        mapviz.assemble()
        print('[ok] dials + map assembled')
    except Exception:
        print('[FAIL] assemble'); traceback.print_exc(); failures.append('assemble')
    try:
        print('[ok] trajectory:', backfill_mod.backfill())
    except Exception:
        print('[FAIL] backfill'); traceback.print_exc(); failures.append('backfill')
    datapackage.build()
    print(f"[ok] ticker built; failures: {failures or 'none'}")
    return 1 if failures else 0


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    if cmd == "weekly":
        raise SystemExit(weekly())
    if cmd == "assemble":
        print(mapviz.assemble())
        return
    if cmd == "backfill":
        print(backfill_mod.backfill())
        return
    if cmd == "ticker":
        ticker.build()
        return
    if cmd in COLLECTORS:
        print(COLLECTORS[cmd]())
        return
    raise SystemExit(f"unknown command {cmd!r}; options: weekly, ticker, {', '.join(COLLECTORS)}")


if __name__ == "__main__":
    main()
