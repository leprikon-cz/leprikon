from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import uuid

from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField

from ..conf import settings
from ..mailers import MessageMailer


@python_2_unicode_compatible
class Message(models.Model):
    sent        = models.DateTimeField(_('sent'), editable=False, auto_now_add=True)
    subject     = models.CharField(_('subject'), max_length=150)
    text        = HTMLField(_('text'), default='')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-sent',)
        verbose_name        = _('message')
        verbose_name_plural = _('messages')

    def __str__(self):
        return '{}'.format(self.subject)



@python_2_unicode_compatible
class MessageRecipient(models.Model):
    slug        = models.SlugField(editable=False)
    message     = models.ForeignKey(Message, verbose_name=_('message'), related_name='recipients')
    recipient   = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('recipient'), related_name='leprikon_messages')
    sent        = models.DateTimeField(_('sent'), editable=False, auto_now_add=True)
    received    = models.DateTimeField(_('received'), null=True, default=None)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-message__sent',)
        unique_together     = (('message', 'recipient'),)

    def __str__(self):
        return '{}'.format(self.recipient)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid4()
            while MessageRecipient.objects.filter(slug=self.slug).exists():
                self.slug = uuid.uuid4()
        new = self.id is None
        super(MessageRecipient, self).save(*args, **kwargs)
        if new:
            self.send_mail()

    def get_absolute_url(self):
        return reverse('leprikon:message_detail', args=(self.slug,))

    def send_mail(self):
        if self.recipient.email:
            MessageMailer().send_mail(self)

