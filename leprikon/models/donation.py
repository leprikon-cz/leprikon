from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..utils import currency
from .printsetup import PrintSetup
from .transaction import Transaction


class Donation(Transaction):
    object_name = "donation"
    transaction_types = Transaction.DONATIONS

    class Meta:
        proxy = True
        verbose_name = _("donation")
        verbose_name_plural = _("donations")

    def __str__(self):
        return f"{self.donor}, {currency(self.amount)}"

    @cached_property
    def all_recipients(self):
        return [self.donor]

    def get_print_setup(self, event):
        return self.organization.donation_print_setup or PrintSetup()
