from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils import first_upper
from .statgroup import StatGroup


class AgeGroup(models.Model):
    name = models.CharField(_("name"), max_length=50)
    min_age = models.PositiveSmallIntegerField(_("minimal age"), blank=True, null=True)
    max_age = models.PositiveSmallIntegerField(_("maximal age"), blank=True, null=True)
    order = models.IntegerField(_("order"), blank=True, default=0)
    require_school = models.BooleanField(_("require school"), default=True)
    stat_group = models.ForeignKey(
        StatGroup, on_delete=models.PROTECT, related_name="+", verbose_name=_("group for statistics")
    )

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("age group")
        verbose_name_plural = _("age groups")

    def __str__(self):
        return self.name

    def title(self):
        return first_upper(self.name)
