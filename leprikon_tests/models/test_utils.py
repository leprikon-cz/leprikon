from datetime import date, datetime, timezone

import pytest

from leprikon.models.utils import BankAccount, change_year


@pytest.mark.parametrize(
    "bank_account, iban, string",
    (
        ("298182774/0300", "CZ63 0300 0000 0002 9818 2774", "298182774/0300"),
        ("CZ63 0300 0000 0002 9818 2774", "CZ63 0300 0000 0002 9818 2774", "298182774/0300"),
        ("670100-2200420359/6210", "CZ77 6210 6701 0022 0042 0359", "670100-2200420359/6210"),
        ("LT97 3250 0783 1763 2841", "LT97 3250 0783 1763 2841", "LT97 3250 0783 1763 2841"),
    ),
)
def test_constructor(bank_account: str, iban: str, string: str):
    ba = BankAccount(bank_account)
    assert ba.iban.formatted == iban
    assert str(ba) == string


# test of change_year that covers leap year handling
@pytest.mark.parametrize("d,result", [
    (None, None),
    (date(2024, 1, 1), date(2025, 1, 1)),
    (date(2024, 2, 28), date(2025, 2, 28)), 
    (date(2024, 2, 29), date(2025, 2, 28)), 
    (datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc), datetime(2025, 1, 1, 9, 30, 0, tzinfo=timezone.utc)),
    (datetime(2024, 2, 28, 9, 30, 0, tzinfo=timezone.utc), datetime(2025, 2, 28, 9, 30, 0, tzinfo=timezone.utc)), 
    (datetime(2024, 2, 29, 9, 30, 0, tzinfo=timezone.utc), datetime(2025, 2, 28, 9, 30, 0, tzinfo=timezone.utc)), 
])
def test_change_year_leap_year(d, result):
    assert change_year(d, 1) == result
