from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from ..utils import first_upper


@python_2_unicode_compatible
class AgeGroup(models.Model):
    name    = models.CharField(_('name'), max_length=50)
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('age group')
        verbose_name_plural = _('age groups')

    def __str__(self):
        return self.name

    def title(self):
        return first_upper(self.name)
