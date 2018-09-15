from django.contrib.sites.models import Site, clear_site_cache
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from localflavor.generic.models import BICField, IBANField

from .fields import PostalCodeField
from .printsetup import PrintSetup
from .utils import BankAccount


class LeprikonSiteManager(models.Manager):

    def get_current(self, request=None):
        current_site = Site.objects.get_current(request)
        return self.get_or_create(site_ptr=current_site)[0]


class LeprikonSite(Site):
    company_name    = models.CharField(_('company name'), max_length=150, blank=True, null=True)
    street          = models.CharField(_('street'), max_length=150, blank=True, null=True)
    city            = models.CharField(_('city'), max_length=150, blank=True, null=True)
    postal_code     = PostalCodeField(_('postal code'), blank=True, null=True)
    email           = models.EmailField(_('email address'), blank=True, null=True)
    phone           = models.CharField(_('phone'), max_length=30, blank=True, null=True)
    company_num     = models.CharField(_('company number'), max_length=8, blank=True, null=True)
    vat_number      = models.CharField(_('VAT number'), max_length=10, blank=True, null=True)
    iban            = IBANField(_('IBAN'), blank=True, null=True)
    bic             = BICField(_('BIC (SWIFT)'), blank=True, null=True)
    bill_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                         verbose_name=_('bill print setup'), blank=True, null=True)
    registration_agreement  = HTMLField(_('registration agreement'), blank=True, default='')
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)
    user_agreement  = HTMLField(_('user agreement'), blank=True, default='')
    user_agreement_changed = models.DateTimeField(_('last time user agreement changed'), blank=True, null=True)

    objects = LeprikonSiteManager()

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('leprikon site')
        verbose_name_plural = _('leprikon sites')

    def get_company_name(self):
        return self.company_name or self.name

    @cached_property
    def bank_account(self):
        return self.iban and BankAccount(self.iban)


pre_save.connect(clear_site_cache, sender=LeprikonSite)
pre_delete.connect(clear_site_cache, sender=LeprikonSite)
