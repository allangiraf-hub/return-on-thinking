# The Return on Thinking

Is the AI boom paying for itself - in money, and for the world?
Three measured dials and a map, from public primary sources, free to everyone.

**Site:** https://returns.priceofthinking.com (weekly ticker; quarterly map)
**Sister project:** [AI Boom Indicators](https://indicators.priceofthinking.com) - the stable chapter-9 companion to [*The Price of Thinking*](https://priceofthinking.com). This repo reuses its collector code as a dependency and extends it.

## The three dials

| Dial | Question | Cadence |
|---|---|---|
| Debt (F) | Whose money burns if it goes wrong - and where does the leverage sit? | weekly |
| Earnings (Cp) | Is the machinery paying for itself? Quasi-rents vs user cost, as a range | quarterly |
| Benefit (Cs) | Is the world getting value even where investors aren't? | quarterly |

Design documents: `value-coverage-framework.md` (theory, adversarially reviewed), `measurement-plan.md` (sources), `return-on-thinking-spec.md` (this system) - published with the methodology page.

## Principles

Every published number traces to a public primary source. Proprietary research (credited) calibrates assumptions, never appears as data. All contestable numbers live in `data/assumptions/v*.yaml`; bumping the version restates the entire back-series - movement on the map is never a method artifact. Levels are uncertain and published as ranges; only movements beyond the published band are called. This dashboard does not predict crashes, and says so.

## Run it

```
pip install -e .[dev]
python -m rot.cli weekly      # all collectors + ticker
python -m rot.cli vastai      # one collector
pytest -m "not network"       # offline tests
```

## Status

P0: scaffold + five collectors (edgar, fred, vastai, damodaran, census_c30) + weekly ticker.
P1 adds FMP (transcripts, quarterly statements), the assumptions file, the deal ledger harvest, and the first Cp band. See the spec for phases.

## Using the data

Compiled series (`data/series/`, `data/curated/`) are licensed **CC-BY-4.0** — use freely, cite the dataset DOI (on the website and each release). Machine-readable schema: `datapackage.json`. Quarterly snapshots are archived on Zenodo automatically via GitHub releases. Code is MIT. Underlying facts remain the property of their sources (SEC, US Census, US Treasury, FRED, vast.ai, et al.).
