from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import *


class MessageRecipientInlineAdmin(admin.TabularInline):
    model           = MessageRecipient
    readonly_fields = ('sent', 'received',)
    raw_id_fields   = ('recipient',)
    extra           = 0

    def get_formset(self, request, obj=None, **kwargs):
        if request.method == 'GET':
            try:
                recipients = map(int, request.GET['recipients'].split(','))
            except:
                recipients = []
            self.extra = len(recipients)
            Formset = super(MessageRecipientInlineAdmin, self).get_formset(request, obj, **kwargs)
            class FormsetWrapper(Formset):
                def __init__(self, **kwargs):
                    kwargs['initial'] = [{'recipient': r} for r in recipients]
                    super(FormsetWrapper, self).__init__(**kwargs)
            return FormsetWrapper
        else:
            return super(MessageRecipientInlineAdmin, self).get_formset(request, obj, **kwargs)

class MessageAttachmentInlineAdmin(admin.TabularInline):
    model   = MessageAttachment
    extra   = 0

class MessageAdmin(admin.ModelAdmin):
    inlines             = (MessageAttachmentInlineAdmin, MessageRecipientInlineAdmin)
    search_fields       = ('subject', 'text')
    list_display        = ('subject', 'sent', 'recipients_count', 'recipients_received_count')

    def recipients_count(self, obj):
        return obj.recipients.count()
    recipients_count.short_description = _('recipients count')

    def recipients_received_count(self, obj):
        return obj.recipients.exclude(received=None).count()
    recipients_received_count.short_description = _('received')


