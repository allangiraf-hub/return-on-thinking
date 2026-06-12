"""The YTD-differencing logic is load-bearing for F1; pin it with a fixture."""
import pandas as pd
from potindicators import edgar


def test_ytd_differencing_recovers_quarters():
    df = pd.DataFrame({
        "start": pd.to_datetime(["2025-01-01"] * 3),
        "end": pd.to_datetime(["2025-03-31", "2025-06-30", "2025-09-30"]),
        "val": [10.0, 25.0, 45.0],
        "form": ["10-Q"] * 3,
        "filed": pd.to_datetime(["2025-04-20", "2025-07-20", "2025-10-20"]),
    })
    q = edgar.quarterly_values(df)
    assert list(q["usd"]) == [10.0, 15.0, 20.0]
