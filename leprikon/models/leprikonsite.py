from time import time

from django.contrib.sites.models import Site
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django_pays.models import Gateway
from djangocms_text_ckeditor.fields import HTMLField

from ..conf import settings
from .account import AccountClosure
from .agreements import Agreement
from .organizations import Organization
from .printsetup import PrintSetup


class LeprikonSiteManager(models.Manager):
    _cached_site = None
    _cache_timestamp = None

    def get_current(self):
        now = time()
        if not self._cached_site or now - self._cache_timestamp > settings.LEPRIKON_SITE_CACHE_MAX_AGE:
            lookup_kwargs = {}
            if getattr(settings, "SITE_ID", ""):
                lookup_kwargs["pk"] = settings.SITE_ID
            self._cached_site = self.get_or_create(**lookup_kwargs)[0]
            self._cache_timestamp = now
        return self._cached_site

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "bill_print_setup",
                "reg_print_setup",
            )
        )


class LeprikonSite(Site):
    organization = models.ForeignKey(
        Organization,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("default organization"),
    )
    reg_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("default registration print setup"),
    )
    pr_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("default payment request print setup"),
    )
    bill_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("default bill print setup"),
    )
    user_agreement = HTMLField(_("user agreement"), blank=True, default="")
    user_agreement_changed = models.DateTimeField(_("last time user agreement changed"), blank=True, null=True)
    registration_agreements = models.ManyToManyField(
        Agreement,
        blank=True,
        related_name="+",
        verbose_name=_("default registration agreements"),
        help_text=_("Add legal agreements for the registration form."),
    )
    payment_gateway = models.ForeignKey(
        Gateway, blank=True, null=True, on_delete=models.SET_NULL, related_name="+", verbose_name=_("Payment Gateway")
    )

    objects = LeprikonSiteManager()

    class Meta:
        app_label = "leprikon"
        verbose_name = _("leprikon site")
        verbose_name_plural = _("leprikon sites")

    @cached_property
    def max_closure_date(self):
        return AccountClosure.objects.max_closure_date()

    @cached_property
    def url(self):
        return settings.LEPRIKON_URL or f"https://{self.domain}"
