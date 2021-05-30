from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from localflavor.generic.models import BICField, IBANField

from .fields import EmailField, PostalCodeField
from .printsetup import PrintSetup
from .utils import BankAccount


class Organization(models.Model):
    name = models.CharField(_("organization name"), max_length=150)
    street = models.CharField(_("street"), max_length=150, blank=True, default="")
    city = models.CharField(_("city"), max_length=150, blank=True, default="")
    postal_code = PostalCodeField(_("postal code"), blank=True, default="")
    email = EmailField(_("email address"), blank=True, default="")
    phone = models.CharField(_("phone"), max_length=30, blank=True, default="")
    company_num = models.CharField(_("company number"), max_length=8, blank=True, default="")
    vat_number = models.CharField(_("VAT number"), max_length=12, blank=True, default="")
    iban = IBANField(_("IBAN"), blank=True, default="")
    bic = BICField(_("BIC (SWIFT)"), blank=True, default="")
    donation_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("donation print setup"),
    )

    class Meta:
        app_label = "leprikon"
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")

    def __str__(self):
        return f"{self.name} ({self.bank_account})"

    @cached_property
    def address(self):
        return ", ".join(filter(bool, (self.street, self.city, self.postal_code)))

    address.short_description = _("address")

    @cached_property
    def bank_account(self):
        return self.iban and BankAccount(self.iban)

    bank_account.short_description = _("bank account")
