from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class Department(models.Model):
    name    = models.CharField(_('name'), max_length=50)
    code    = models.PositiveSmallIntegerField(_('department code'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('code', 'name')
        verbose_name        = _('department')
        verbose_name_plural = _('departments')

    def __str__(self):
        if self.code:
            return '{code} {name}'.format(code=self.code, name=self.name)
        else:
            return '{name}'.format(name=self.name)
