from __future__ import unicode_literals

from collections import namedtuple

from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..utils import currency


class PaymentStatus(namedtuple('_PaymentsStatus', ('price', 'discount', 'paid'))):

    @property
    def receivable(self):
        return self.price - self.discount

    @property
    def balance(self):
        return self.paid - self.receivable

    @property
    def color(self):
        if self.balance == 0:
            return settings.LEPRIKON_COLOR_PAID
        elif self.balance < 0:
            return settings.LEPRIKON_COLOR_NOTPAID
        else:
            return settings.LEPRIKON_COLOR_OVERPAID

    @property
    def title(self):
        if self.balance == 0:
            return _('paid')
        elif self.balance < 0:
            return _('{} let to pay').format(currency(-self.balance))
        else:
            return _('{} overpaid').format(currency(self.balance))

    def __repr__(self):
        return 'PaymentStatus(price={price}, discount={discount}, paid={paid}, balance={balance})'.format(
            price       = self.price,
            discount    = self.discount,
            paid        = self.paid,
            balance     = self.balance,
        )

    def __add__(self, other):
        if other == 0:
            return self
        return PaymentStatus(
            price       = self.price    + other.price,
            discount    = self.discount + other.discount,
            paid        = self.paid     + other.paid,
        )

    __radd__ = __add__
