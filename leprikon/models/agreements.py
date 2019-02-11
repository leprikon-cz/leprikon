from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField


@python_2_unicode_compatible
class Agreement(models.Model):
    name        = models.CharField(_('name'), max_length=50, unique=True)
    order       = models.IntegerField(_('order'), blank=True, default=0)
    heading     = models.CharField(_('heading'), max_length=50, blank=True, default='')
    agreement   = HTMLField(_('agreement'), blank=True, default='')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('legal agreement')
        verbose_name_plural = _('legal agreements')

    def __str__(self):
        return self.name

    @cached_property
    def all_options(self):
        return list(self.options.all())


@python_2_unicode_compatible
class AgreementOption(models.Model):
    agreement   = models.ForeignKey(Agreement, verbose_name=_('agreement'), related_name='options')
    name        = models.CharField(_('name'), max_length=50)
    order       = models.IntegerField(_('order'), blank=True, default=0)
    required    = models.BooleanField(_('required'), default=False)
    option      = HTMLField(_('option'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        unique_together     = (('agreement', 'name'),)
        verbose_name        = _('agreement option')
        verbose_name_plural = _('agreement options')

    def __str__(self):
        return self.name
