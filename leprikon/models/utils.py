from collections import namedtuple

from django.utils.functional import cached_property, lazy
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..utils import currency, paragraph


class PaymentStatusMixin:
    @property
    def receivable(self):
        return self.price - self.discount

    @property
    def balance(self):
        return self.paid - self.receivable

    @property
    def color(self):
        if self.overdue:
            return settings.LEPRIKON_COLOR_OVERDUE
        if self.amount_due:
            return settings.LEPRIKON_COLOR_NOTPAID
        if self.overpaid:
            return settings.LEPRIKON_COLOR_OVERPAID
        return settings.LEPRIKON_COLOR_PAID

    @property
    def title(self):
        titles = []
        if self.overdue:
            titles.append(_('overdue {}').format(currency(self.overdue)))
        if self.amount_due and (self.amount_due != self.overdue):
            titles.append(_('amount due {}').format(currency(self.amount_due)))
        if self.overpaid:
            titles.append(_('{} overpaid').format(currency(self.overpaid)))
        if self.balance == 0:
            titles.append(_('paid'))
        elif self.balance < 0 and not self.amount_due:  # self.due_from > self.current_date:
            titles.append(_('payment not requested yet'))
        return ', '.join(map(str, titles))

    def __repr__(self):
        return (
            '{type_name}(price={price}, discount={discount}, paid={paid}, balance={balance}, '
            'amount_due={amount_due}, overdue={overdue}, overpaid={overpaid})'.format(
                type_name=type(self).__name__,
                price=self.price,
                discount=self.discount,
                paid=self.paid,
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
            paid=self.paid + (other and other.paid),
            amount_due=self.amount_due + (other and other.amount_due),
            overdue=self.overdue + (other and other.overdue),
            overpaid=self.overpaid + (other and other.overpaid),
        )

    __radd__ = __add__


class PaymentStatus(
    PaymentStatusMixin,
    namedtuple('_PaymentsStatus', ('price', 'discount', 'paid', 'explanation', 'current_date', 'due_from', 'due_date'))
):
    @property
    def amount_due(self):
        return max(self.receivable - self.paid, 0) if self.due_from <= self.current_date else 0

    @property
    def overdue(self):
        return self.amount_due if self.due_date < self.current_date else 0

    @property
    def overpaid(self):
        return max(self.balance, 0)

    def __str__(self):
        return '<strong title="{title}" style="color: {color}">{balance}</strong>'.format(
            color=self.color,
            balance=currency(self.balance),
            title=self.title,
        )


class PaymentStatusSum(
    PaymentStatusMixin,
    namedtuple('_PaymentsStatusSum', ('price', 'discount', 'paid', 'amount_due', 'overdue', 'overpaid')),
):
    pass


class BankAccount:
    def __init__(self, iban):
        self.iban = iban

    @cached_property
    def country_code(self):
        return self.iban[:2]

    @cached_property
    def bank_code(self):
        return self.iban[4:8]

    @cached_property
    def account_prefix(self):
        return self.iban[8:14].lstrip('0')

    @cached_property
    def account_number(self):
        return self.iban[14:].lstrip('0')

    def __str__(self):
        return '%s%s%s/%s' % (
            self.account_prefix,
            self.account_prefix and '-',
            self.account_number,
            self.bank_code,
        )


def generate_variable_symbol(registration):
    # get base variable symol from the configured expression
    variable_symbol = eval(settings.LEPRIKON_VARIABLE_SYMBOL_EXPRESSION, {'reg': registration})

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


def html_help_text_with_default(default):
    return paragraph(_('Keep empty to use default value:\n{}').format(default))


lazy_html_help_text_with_default = lazy(html_help_text_with_default, str)
