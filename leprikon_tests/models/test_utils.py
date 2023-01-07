from unittest import TestCase

from leprikon.models.utils import BankAccount


class TestBankAccount(TestCase):
    def test_constructor(self):
        for bank_account, iban, string in (
            ("298182774/0300", "CZ63 0300 0000 0002 9818 2774", "298182774/0300"),
            ("CZ63 0300 0000 0002 9818 2774", "CZ63 0300 0000 0002 9818 2774", "298182774/0300"),
            ("670100-2200420359/6210", "CZ77 6210 6701 0022 0042 0359", "670100-2200420359/6210"),
            ("LT97 3250 0783 1763 2841", "LT97 3250 0783 1763 2841", "LT97 3250 0783 1763 2841"),
        ):
            ba = BankAccount(bank_account)
            self.assertEqual(ba.formatted, iban)
            self.assertEqual(str(ba), string)
