from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from localflavor.generic.models import BICField, IBANField

from .fields import EmailField, PostalCodeField
from .utils import BankAccount


class Organization(models.Model):
    name = models.CharField(_('organization name'), max_length=150)
    street = models.CharField(_('street'), max_length=150, blank=True, null=True)
    city = models.CharField(_('city'), max_length=150, blank=True, null=True)
    postal_code = PostalCodeField(_('postal code'), blank=True, null=True)
    email = EmailField(_('email address'), blank=True, null=True)
    phone = models.CharField(_('phone'), max_length=30, blank=True, null=True)
    company_num = models.CharField(_('company number'), max_length=8, blank=True, null=True)
    vat_number = models.CharField(_('VAT number'), max_length=10, blank=True, null=True)
    iban = IBANField(_('IBAN'), blank=True, null=True)
    bic = BICField(_('BIC (SWIFT)'), blank=True, null=True)

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def __str__(self):
        return f'{self.name} ({self.bank_account})'

    @cached_property
    def address(self):
        return ', '.join(filter(bool, (self.street, self.city, self.postal_code)))
    address.short_description = _('address')

    @cached_property
    def bank_account(self):
        return self.iban and BankAccount(self.iban)
    bank_account.short_description = _('bank account')
