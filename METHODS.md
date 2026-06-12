# Methods (P0 - ticker only)

Version: pre-v1. The full assumptions file (`data/assumptions/v1.yaml`) lands in P1;
until then the ticker publishes only directly observed series, no derived dials.

## Series now collected

- **edgar_{ticker}_{capex|ocf|debt_issued}_q** - SEC XBRL company facts, quarterly values derived
  by differencing year-to-date cash-flow figures within each fiscal year (logic inherited from
  potindicators and pinned by test). Tier T1.
- **fred_dgs10, fred_baa10y** - rate inputs for the future user-cost r. T1.
- **vastai_gpu_rental** - median marketplace rental price per tracked GPU model; append-only
  archive (cannot be backfilled). T1.
- **damodaran_implied_erp** - annual implied equity risk premium history (calibration input). T2.
- **census_datacenter_construction** - monthly data-centre construction put in place, US Census C30. T1.

## Ticker definitions

- **Financing headroom (F1, per hyperscaler):** trailing-4-quarter capex divided by
  trailing-4-quarter operating cash flow. Above 1.0, the AI build is consuming more than the
  whole company generates. This is a *firm-level* figure: hyperscaler cash flow comes mostly from
  non-AI businesses, so this is cross-subsidy capacity, not AI self-financing (see framework Section 2).
- All other ticker blocks are raw observed series with their source URLs.

## What this page does not claim

No crash prediction. No bubble verdict. The dials that interpret these series arrive with the
versioned assumptions file, as ranges, in P1.
