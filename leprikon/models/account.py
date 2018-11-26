from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


class AccountClosureManager(models.Manager):

    def max_closure_date(self):
        return self.aggregate(closure_date=models.Max('closure_date'))['closure_date']


@python_2_unicode_compatible
class AccountClosure(models.Model):
    closure_date = models.DateField(_('closure date'), db_index=True)

    objects = AccountClosureManager()

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-closure_date',)
        verbose_name        = _('account closure')
        verbose_name_plural = _('account closures')

    def __str__(self):
        return str(self.closure_date)
