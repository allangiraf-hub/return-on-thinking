"""Reproducibly derive the occupational AI-usage weights in
data/curated/occupations.csv from the Anthropic Economic Index task-level data.

Replaces the earlier chart-read SOC-major-group shares with a bottom-up
computation: join per-task Claude usage to each task's O*NET-SOC code, aggregate
to the 22 SOC major groups, normalise to the most-exposed group (=1.0), then
blend 50/50 with the structural prior (Allan's choice - the raw measured pattern
alone concentrates too hard on software and would understate the exposed base).

Data (Anthropic/EconomicIndex, release_2025_02_10; CC-BY/MIT), download once:
  https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/release_2025_02_10/onet_task_statements.csv
  https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/release_2025_02_10/onet_task_mappings.csv

Run:  python -m rot.derive_occupations_aei <statements.csv> <mappings.csv>
Validation (2026-07-06): computed shares match the prior chart-read values to
two significant figures (Computer&Mathematical 37.31% vs 37.2%, Arts 10.27% vs
10.3%, Office 7.87% vs 7.9%, ...), so this changes no published number; it makes
the weight reproducible instead of asserted.
"""
from __future__ import annotations

import re
import sys

import pandas as pd

from .config import CURATED


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower()).rstrip(".")


def derive(statements_csv: str, mappings_csv: str) -> pd.DataFrame:
    st = pd.read_csv(statements_csv)
    mp = pd.read_csv(mappings_csv)
    st["k"] = st["Task"].map(_norm)
    mp["k"] = mp["task_name"].map(_norm)
    st["soc"] = st["O*NET-SOC Code"].str[:2]
    task2soc = st.drop_duplicates("k").set_index("k")["soc"]
    mp["soc"] = mp["k"].map(task2soc)
    matched = mp["soc"].notna().mean()
    if matched < 0.98:
        raise SystemExit(f"task->SOC match rate only {matched:.1%}; check the input files")
    g = mp.dropna(subset=["soc"]).groupby("soc")["pct"].sum()
    share = (g / g.sum() * 100)          # group usage share (%)
    intensity = (g / g.max())            # normalised, most-exposed group = 1.0

    occ = pd.read_csv(CURATED / "occupations.csv", dtype={"soc": str})
    occ["soc"] = occ["soc"].astype(str).str.zfill(2)
    occ["prior"] = occ["source_note"].map(
        lambda n: float(m.group(1)) if (m := re.search(r"prior \(([0-9.]+)\)", str(n))) else None)
    occ["measured"] = occ["soc"].map(intensity).round(3)
    occ["ai_usage"] = (0.5 * occ["prior"] + 0.5 * occ["measured"]).round(3)
    occ["share"] = occ["soc"].map(share).round(2)
    occ["source_note"] = occ.apply(lambda r: (
        f"employment: BLS May-2023 (AEI release_2025_02_10, exact); ai_usage = 50/50 blend of prior "
        f"({r['prior']:g}) and AEI Feb-2025 Claude.ai usage share {r['share']:g}% (COMPUTED from task-level "
        f"onet_task_statements x onet_task_mappings, Handa et al. 2025), normalized to Computer&Mathematical=1.0"), axis=1)
    return occ[["soc", "group", "employment_m", "mean_wage_usd", "ai_usage", "source_note"]]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    out = derive(sys.argv[1], sys.argv[2])
    out.to_csv(CURATED / "occupations.csv", index=False)
    print(f"occupations.csv rewritten from AEI task-level data ({len(out)} SOC major groups).")


if __name__ == "__main__":
    main()
