from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class SchoolYear(models.Model):
    year    = models.IntegerField(_('year'), unique=True)
    active  = models.BooleanField(_('active'), default=False)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-year',)
        verbose_name        = _('school year')
        verbose_name_plural = _('school years')

    def __str__(self):
        return self.name

    def delete(self):
        if self.clubs.count() or self.events.count():
            raise Exception(_('Can not delete sclool year with clubs or events.'))
        super(SchoolYear, self).delete()

    @cached_property
    def name(self):
        return '{}/{}'.format(self.year, self.year+1)

    @cached_property
    def all_clubs(self):
        return list(self.clubs.all())


