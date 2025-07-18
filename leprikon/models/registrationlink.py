from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from .activities import ActivityType, ActivityVariant
from .leprikonsite import LeprikonSite
from .schoolyear import SchoolYear


class RegistrationLink(models.Model):
    school_year = models.ForeignKey(
        SchoolYear,
        editable=False,
        on_delete=models.CASCADE,
        related_name="registration_links",
        verbose_name=_("school year"),
    )
    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.CASCADE, related_name="registration_links", verbose_name=_("activity type")
    )
    slug = models.SlugField(editable=False, max_length=64)
    name = models.CharField(_("name"), max_length=50)
    reg_from = models.DateTimeField(_("registration active from"))
    reg_to = models.DateTimeField(_("registration active to"))
    activity_variants = models.ManyToManyField(
        ActivityVariant, blank=False, related_name="registration_links", verbose_name=_("activities")
    )

    class Meta:
        app_label = "leprikon"
        ordering = ("reg_from", "reg_to")
        verbose_name = _("registration link")
        verbose_name_plural = _("registration links")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("leprikon:registration_link", args=(self.slug,))

    @cached_property
    def link(self):
        return LeprikonSite.objects.get_current().url + self.get_absolute_url()

    @property
    def registration_allowed(self):
        now = timezone.now()
        return (self.reg_from <= now) and (self.reg_to > now)
