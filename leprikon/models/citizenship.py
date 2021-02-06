from django.db import models
from django.utils.translation import ugettext_lazy as _


class Citizenship(models.Model):
    name = models.CharField(_("name"), max_length=50)
    order = models.IntegerField(_("order"), blank=True, default=0)
    require_birth_num = models.BooleanField(_("require birth number"), default=True)

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("citizenship")
        verbose_name_plural = _("citizenships")

    def __str__(self):
        return self.name
