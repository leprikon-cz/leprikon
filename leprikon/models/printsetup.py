from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from filer.fields.file import FilerFileField


@python_2_unicode_compatible
class PrintSetup(models.Model):
    name        = models.CharField(_('name'), max_length=150)
    top         = models.IntegerField(_('margin top'), blank=True, default=20)
    left        = models.IntegerField(_('margin left'), blank=True, default=20)
    right       = models.IntegerField(_('margin right'), blank=True, default=20)
    bottom      = models.IntegerField(_('margin bottom'), blank=True, default=20)
    template    = FilerFileField(verbose_name=_('pdf template'), blank=True, null=True,
                                 on_delete=models.SET_NULL, related_name='+')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('name',)
        verbose_name        = _('print setup')
        verbose_name_plural = _('print setups')

    def __str__(self):
        return self.name
