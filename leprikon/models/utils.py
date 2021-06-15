import re
from collections import namedtuple
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Union

from django.core.exceptions import ValidationError
from django.utils.functional import cached_property, lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from schwifty.exceptions import InvalidAccountCode
from schwifty.iban import IBAN

from ..conf import settings
from ..utils import currency, paragraph

Price = Union[Decimal, int]


class PaymentStatusMixin:
    price: Price
    discount: Price
    received: Price
    returned: Price
    amount_due: Price
    overdue: Price
    overpaid: Price

    @property
    def paid(self) -> Price:
        return self.received - self.returned

    @property
    def receivable(self) -> Price:
        return self.price - self.discount

    @property
    def balance(self) -> Price:
        return self.paid - self.receivable

    @property
    def color(self) -> str:
        if self.overdue:
            return settings.LEPRIKON_COLOR_OVERDUE
        if self.amount_due:
            return settings.LEPRIKON_COLOR_NOTPAID
        if self.overpaid:
            return settings.LEPRIKON_COLOR_OVERPAID
        return settings.LEPRIKON_COLOR_PAID

    @property
    def amount_due_color(self) -> str:
        if self.overdue:
            return settings.LEPRIKON_COLOR_OVERDUE
        if self.amount_due:
            return settings.LEPRIKON_COLOR_NOTPAID
        return settings.LEPRIKON_COLOR_PAID

    @property
    def overpaid_color(self) -> str:
        if self.overpaid:
            return settings.LEPRIKON_COLOR_OVERPAID
        return settings.LEPRIKON_COLOR_PAID

    @property
    def title(self) -> str:
        titles = []
        if self.amount_due and (self.amount_due != self.overdue):
            titles.append(_("amount due {}").format(currency(self.amount_due)))
        if self.overdue:
            titles.append(_("overdue {}").format(currency(self.overdue)))
        if self.overpaid:
            titles.append(_("{} overpaid").format(currency(self.overpaid)))
        if self.balance == 0:
            if self.receivable:
                titles.append(_("paid"))
            else:
                titles.append(_("payment not requested"))
        elif self.balance < 0 and not self.amount_due:  # self.due_from > self.current_date:
            titles.append(_("payment not requested yet"))
        return ", ".join(map(str, titles))

    def __xrepr__(self) -> str:
        return (
            "{type_name}(price={price}, discount={discount}, received={received}, returned={returned}, "
            "balance={balance}, amount_due={amount_due}, overdue={overdue}, overpaid={overpaid})".format(
                type_name=type(self).__name__,
                price=self.price,
                discount=self.discount,
                received=self.received,
                returned=self.returned,
                balance=self.balance,
                amount_due=self.amount_due,
                overdue=self.overdue,
                overpaid=self.overpaid,
            )
        )

    def __add__(self, other):
        return PaymentStatusSum(
            price=self.price + (other and other.price),
            discount=self.discount + (other and other.discount),
            received=self.received + (other and other.received),
            returned=self.returned + (other and other.returned),
            amount_due=self.amount_due + (other and other.amount_due),
            overdue=self.overdue + (other and other.overdue),
            overpaid=self.overpaid + (other and other.overpaid),
        )

    __radd__ = __add__


class PaymentStatus(
    PaymentStatusMixin,
    namedtuple(
        "_PaymentsStatus",
        ["price", "discount", "explanation", "received", "returned", "current_date", "due_from", "due_date"],
    ),
):
    explanation: str
    current_date: date
    due_from: date
    due_date: date

    @property
    def amount_due(self) -> Price:
        return max(self.receivable - self.paid, 0) if self.due_from and self.due_from <= self.current_date else 0

    @property
    def overdue(self) -> Price:
        return self.amount_due if self.due_date and self.due_date < self.current_date else 0

    @property
    def overpaid(self) -> Price:
        return max(self.balance, 0)

    def __str__(self) -> str:
        return format_html(
            '<strong title="{title}" style="color: {color}">{balance}</strong>',
            color=self.color,
            balance=currency(self.balance),
            title=self.title,
        )


class PaymentStatusSum(
    PaymentStatusMixin,
    namedtuple(
        "_PaymentStatusSum",
        ["price", "discount", "received", "returned", "amount_due", "overdue", "overpaid"],
    ),
):
    pass


class BankAccount(IBAN):
    czech_bban_regex = re.compile(r"(([0-9]{1,6})\s?-\s?)?([0-9]{1,10})\s?/\s?([0-9]{4})")
    czech_bban_weights = (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)

    def _validate_czech(self, part: str) -> bool:
        check = 0
        for i, n in enumerate(reversed(part)):
            check += int(n) * self.czech_bban_weights[i]
        if check % 11:
            raise InvalidAccountCode()

    def __init__(self, bank_account: str):
        match = self.czech_bban_regex.match(bank_account)
        if match:
            x, prefix, account, bank_code = match.groups()
            self._validate_czech(prefix or "")
            self._validate_czech(account)
            account_code = (prefix or "").zfill(6) + account.zfill(10)
            bank_account = f"CZ??{bank_code}{account_code}"
        super().__init__(bank_account)

    @cached_property
    def account_prefix(self):
        return self.account_code[:6].lstrip("0")

    @cached_property
    def account_number(self):
        return self.account_code[6:].lstrip("0")

    def __str__(self):
        if self.country_code == "CZ":
            return "%s%s%s/%s" % (
                self.account_prefix,
                self.account_prefix and "-",
                self.account_number,
                self.bank_code,
            )
        else:
            return self.formatted


def parse_bank_account(bank_account: Any) -> BankAccount:
    if isinstance(bank_account, BankAccount):
        return bank_account
    if isinstance(bank_account, IBAN):
        return BankAccount(bank_account.compact)
    if not isinstance(bank_account, str):
        bank_account = str(bank_account)
    try:
        return BankAccount(bank_account)
    except ValueError:
        raise ValidationError(
            message=_("Enter a valid account number."),
            code="invalid",
        )


def generate_variable_symbol(registration):
    # get base variable symol from the configured expression
    variable_symbol = eval(settings.LEPRIKON_VARIABLE_SYMBOL_EXPRESSION, {"reg": registration})

    # add check digit
    odd_sum = 0
    even_sum = 0
    for i, char in enumerate(str(variable_symbol)):
        if i % 2:
            even_sum += int(char)
        else:
            odd_sum += int(char)
    check_digit = (odd_sum * 3 + even_sum) % 10
    return variable_symbol * 10 + check_digit


def help_text_with_html_default(help_text, html_default):
    keep_empty = paragraph(_("Keep empty to use default value:"))
    return mark_safe(
        "{}{}{}".format(
            paragraph(help_text),
            keep_empty,
            html_default,
        )
        if help_text
        else "{}{}".format(
            keep_empty,
            html_default,
        )
    )


lazy_help_text_with_html_default = lazy(help_text_with_html_default, str)


def help_text_with_default(help_text, default):
    keep_empty_default = _("Keep empty to use default value: {}").format(default)
    return paragraph("{}\n\n{}".format(help_text, keep_empty_default) if help_text else keep_empty_default)


lazy_help_text_with_default = lazy(help_text_with_default, str)


def change_year(d, year_delta):
    if isinstance(d, date):
        try:
            return date(d.year + year_delta, d.month, d.day)
        except ValueError:
            # handle leap-year
            return date(d.year + year_delta, d.month, d.day - 1)
    else:
        try:
            return datetime(d.year + year_delta, d.month, d.day)
        except ValueError:
            # handle leap-year
            return datetime(d.year + year_delta, d.month, d.day - 1, d.hour, d.minute, d.second)


def shorten(string, length):
    if len(string) <= length:
        return string
    half = length // 2 - 1
    return f"{string[:half]}...{string[half + 3 - length:]}"
