from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils import first_upper


class StatGroup(models.Model):
    name = models.CharField(_("name"), max_length=50)
    order = models.IntegerField(_("order"), blank=True, default=0)

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("group for statistics")
        verbose_name_plural = _("groups for statistics")

    def __str__(self):
        return self.name

    def title(self):
        return first_upper(self.name)
