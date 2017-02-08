from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import ugettext_lazy as _
from localflavor.generic.models import BICField, IBANField

from .fields import PostalCodeField
from .printsetup import PrintSetup


class LeprikonSiteManager(models.Manager):

    def get_current(self, request=None):
        return Site.objects.get_current(request).leprikonsite



class LeprikonSite(Site):
    street          = models.CharField(_('street'), max_length=150, blank=True, null=True)
    city            = models.CharField(_('city'), max_length=150, blank=True, null=True)
    postal_code     = PostalCodeField(_('postal code'), blank=True, null=True)
    email           = models.EmailField(_('email address'), blank=True, null=True)
    phone           = models.CharField(_('phone'), max_length=30, blank=True, null=True)
    street          = models.CharField(_('street'), max_length=150, blank=True, null=True)
    company_num     = models.CharField(_('company number'), max_length=8, blank=True, null=True)
    vat_number      = models.CharField(_('VAT number'), max_length=10, blank=True, null=True)
    iban            = IBANField(_('IBAN'), blank=True, null=True)
    bic             = BICField(_('BIC (SWIFT)'), blank=True, null=True)
    bill_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                         verbose_name=_('bill print setup'), blank=True, null=True)
    agreement       = models.TextField(_('registration agreement'), blank=True, null=True)
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)

    objects = LeprikonSiteManager()

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('leprikon site')
        verbose_name_plural = _('leprikon sites')
