from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..utils import first_upper


class TargetGroup(models.Model):
    name = models.CharField(_("name"), max_length=50)
    order = models.IntegerField(_("order"), blank=True, default=0)
    require_school = models.BooleanField(_("require school"), default=True)

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("target group")
        verbose_name_plural = _("target groups")

    def __str__(self):
        return self.name

    def title(self):
        return first_upper(self.name)
