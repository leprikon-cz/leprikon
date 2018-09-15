from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class School(models.Model):
    name    = models.CharField(_('name'),   max_length=50)
    street  = models.CharField(_('street'), max_length=50, blank=True, default='')
    city    = models.CharField(_('city'),   max_length=50, blank=True, default='')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('city', 'name')
        verbose_name        = _('school')
        verbose_name_plural = _('schools')

    def __str__(self):
        if self.address:
            return '{}, {}'.format(self.name, self.address)
        else:
            return self.name

    @cached_property
    def address(self):
        if self.street and self.city:
            return '{}, {}'.format(self.street, self.city)
        else:
            return self.street or self.city
