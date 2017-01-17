from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class Insurance(models.Model):
    code    = models.CharField(_('code'), max_length=10, unique=True)
    name    = models.CharField(_('name'), max_length=150)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('code',)
        verbose_name        = _('insurance company')
        verbose_name_plural = _('insurance companies')

    def __str__(self):
        return '{} - {}'.format(self.code, self.name)
