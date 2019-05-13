from time import time

from django.contrib.sites.models import Site
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django_pays.models import Gateway
from djangocms_text_ckeditor.fields import HTMLField
from localflavor.generic.models import BICField, IBANField

from ..conf import settings
from .account import AccountClosure
from .agreements import Agreement
from .fields import EmailField, PostalCodeField
from .printsetup import PrintSetup
from .utils import BankAccount


class LeprikonSiteManager(models.Manager):
    _cached_site = None
    _cache_timestamp = None

    def get_current(self):
        now = time()
        if not self._cached_site or now - self._cache_timestamp > settings.LEPRIKON_SITE_CACHE_MAX_AGE:
            lookup_kwargs = {}
            if getattr(settings, 'SITE_ID', ''):
                lookup_kwargs['pk'] = settings.SITE_ID
            self._cached_site = self.get_or_create(**lookup_kwargs)[0]
            self._cache_timestamp = now
        return self._cached_site

    def get_queryset(self):
        return super(LeprikonSiteManager, self).get_queryset().select_related(
            'bill_print_setup',
            'reg_print_setup',
        )


class LeprikonSite(Site):
    company_name    = models.CharField(_('company name'), max_length=150, blank=True, null=True)
    street          = models.CharField(_('street'), max_length=150, blank=True, null=True)
    city            = models.CharField(_('city'), max_length=150, blank=True, null=True)
    postal_code     = PostalCodeField(_('postal code'), blank=True, null=True)
    email           = EmailField(_('email address'), blank=True, null=True)
    phone           = models.CharField(_('phone'), max_length=30, blank=True, null=True)
    company_num     = models.CharField(_('company number'), max_length=8, blank=True, null=True)
    vat_number      = models.CharField(_('VAT number'), max_length=10, blank=True, null=True)
    iban            = IBANField(_('IBAN'), blank=True, null=True)
    bic             = BICField(_('BIC (SWIFT)'), blank=True, null=True)
    bill_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                         verbose_name=_('bill print setup'), blank=True, null=True)
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)
    user_agreement  = HTMLField(_('user agreement'), blank=True, default='')
    user_agreement_changed = models.DateTimeField(_('last time user agreement changed'), blank=True, null=True)
    old_registration_agreement = HTMLField(
        _('old registration agreement'), blank=True, default='',
        help_text=_('This agreement will be removed in future version. Please, use registration agreements below.'),
    )
    registration_agreements = models.ManyToManyField(
        Agreement, verbose_name=_('registration agreements'), blank=True, related_name='+',
        help_text=_('Add legal agreements for the registration form.'),
    )
    payment_gateway = models.ForeignKey(Gateway, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('Payment Gateway'), blank=True, null=True)

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

    @cached_property
    def max_closure_date(self):
        return AccountClosure.objects.max_closure_date()
