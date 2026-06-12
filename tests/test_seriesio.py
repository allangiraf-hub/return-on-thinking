import pandas as pd
import pytest

from rot import seriesio


def frame(**overrides):
    base = {
        "date": ["2026-01-01"], "value": [1.0], "unit": ["USD"],
        "source_url": ["https://example.gov"], "tier": ["T1"],
        "series_id": ["x"], "retrieved_at": ["2026-01-01T00:00:00+00:00"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_validate_passes():
    seriesio.validate(frame())


def test_validate_rejects_nan():
    with pytest.raises(ValueError, match="NaN"):
        seriesio.validate(frame(value=[float("nan")]))


def test_validate_rejects_bad_tier():
    with pytest.raises(ValueError, match="tiers"):
        seriesio.validate(frame(tier=["T9"]))


def test_validate_rejects_missing_column():
    df = frame().drop(columns=["source_url"])
    with pytest.raises(ValueError, match="missing"):
        seriesio.validate(df)
