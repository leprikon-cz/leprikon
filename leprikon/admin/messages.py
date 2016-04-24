from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..forms.messages import MessageAdminForm
from ..models import *


class MessageRecipientInlineAdmin(admin.TabularInline):
    model           = MessageRecipient
    readonly_fields = ('sent', 'received',)
    raw_id_fields   = ('recipient',)
    extra           = 0

class MessageAdmin(admin.ModelAdmin):
    inlines             = (MessageRecipientInlineAdmin,)
    search_fields       = ('subject', 'text')
    list_display        = ('subject', 'sent', 'recipients_count', 'recipients_received_count')

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = MessageAdminForm
            #kwargs['initial'] = {'recipients': map(int, request.GET['recipients'].split(','))}
            #raise Exception(ids)
        return super(MessageAdmin, self).get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if obj:
            return super(MessageAdmin, self).get_inline_instances(request, obj)
        else:
            return []

    def get_changeform_initial_data(self, request):
        initial = super(MessageAdmin, self).get_changeform_initial_data(request)
        try:
            initial['recipients'] = map(int, initial['recipients'].split(','))
        except:
            initial['recipients'] = []
        return initial

    def recipients_count(self, obj):
        return obj.recipients.count()
    recipients_count.short_description = _('recipients count')

    def recipients_received_count(self, obj):
        return obj.recipients.exclude(received=None).count()
    recipients_received_count.short_description = _('received')


