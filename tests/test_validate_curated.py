from rot.validate_curated import check_ledger


def test_empty_ledger_is_valid():
    assert check_ledger() == []
