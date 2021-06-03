from typing import Optional

import pytest
from django.core.exceptions import ValidationError
from schwifty import IBAN

from .fields import parse_bank_account
from .utils import BankAccount


@pytest.mark.parametrize(
    "bank_account,expected_bank_account",
    [
        ("298182774/0300", BankAccount("CZ6303000000000298182774")),
        ("5083412002/5500", BankAccount("CZ2155000000005083412002")),
        ("670100-2200420359/6210", BankAccount("CZ7762106701002200420359")),
        ("5083412002 / 5500", BankAccount("CZ2155000000005083412002")),
        ("670100 - 2200420359 / 6210", BankAccount("CZ7762106701002200420359")),
        (IBAN("CZ6303000000000298182774"), BankAccount("CZ6303000000000298182774")),
        (BankAccount("CZ6303000000000298182774"), BankAccount("CZ6303000000000298182774")),
        (None, None),
    ],
)
def test_parse_bank_account(bank_account: Optional[str], expected_bank_account: BankAccount) -> None:
    """Given valid account number or None you get BankAccount or None."""

    assert parse_bank_account(bank_account) == expected_bank_account


@pytest.mark.parametrize(
    "invalid_bank_account",
    [
        "123456",
        "CZ6303000000000298182774",
        "CZ63 0300 0000 0002 9818 2774",
    ],
)
def test_parse_invalid_bank_account(invalid_bank_account: str) -> None:
    """Given invalid account number you get ValidationError."""
    with pytest.raises(ValidationError):
        parse_bank_account(invalid_bank_account)
