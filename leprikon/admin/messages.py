from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.conf.urls import url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from ..forms.messages import MessageAdminForm
from ..models.messages import Message, MessageAttachment, MessageRecipient


class MessageAttachmentInlineAdmin(admin.TabularInline):
    model   = MessageAttachment
    extra   = 0

class MessageAdmin(admin.ModelAdmin):
    form            = MessageAdminForm
    inlines         = (MessageAttachmentInlineAdmin,)
    search_fields   = ('subject', 'text')
    list_display    = ('subject', 'created', 'recipients_count', 'sent_mails_count', 'recipients_viewed_count', 'action_links')
    actions         = ('send_mails_new', 'send_mails_all')

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

    def sent_mails_count(self, obj):
        return obj.recipients.exclude(sent_mail=None).count()
    sent_mails_count.short_description = _('sent emails count')

    def recipients_viewed_count(self, obj):
        return obj.recipients.exclude(viewed=None).count()
    recipients_viewed_count.short_description = _('viewed on site')

    def action_links(self, obj):
        return '<a href="{url}" title="{title}">{label}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                        MessageRecipient._meta.app_label,
                        MessageRecipient._meta.model_name,
                    )) + '?message={}'.format(obj.id),
            title   = _('show recipients details'),
            label   = _('recipients'),
        )
    action_links.allow_tags = True
    action_links.short_description = _('recipients')

    def send_mails_all(self, request, queryset):
        return render_to_response('admin/leprikon/messagerecipient/send_mails.html', {
            'title': _('Sending emails'),
            'recipients': queryset.filter(''),
            'options': form.cleaned_data['options'],
            'media':    self.media,
            'opts': self.model._meta,
        }, context_instance=RequestContext(request))
    send_mails_all.short_description = _('Send email to all recipients')

    def send_mails_new(self, request, queryset):
        return self.send_mails_all(request, queryset.filter(sent_mail=None))
    send_mails_new.short_description = _('Sent email to new recipients')



class MessageRecipientAdmin(admin.ModelAdmin):
    list_display    = ('recipient', 'sent', 'viewed', 'sent_mail')
    actions         = ('send_mails_new', 'send_mails_all')

    def get_model_perms(self, request):
        # hide the model from admin index
        return {}

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def send_mails_all(self, request, queryset):
        #raise Exception(request.POST)
        return render_to_response('admin/leprikon/messagerecipient/send_mails.html', {
            'title':        _('Sending emails'),
            'message':      get_object_or_404(Message, id=request.GET.get('message', 0)),
            'recipients':   queryset,
            'media':        self.media,
            'message_opts':       Message._meta,
            'opts':         self.model._meta,
        }, context_instance=RequestContext(request))
    send_mails_all.short_description = _('Send email to all recipients')

    def send_mails_new(self, request, queryset):
        return self.send_mails_all(request, queryset.filter(sent_mail=None))
    send_mails_new.short_description = _('Sent email to new recipients')

    def changelist_view(self, request, extra_context=None):
        message = get_object_or_404(Message, id=request.GET.get('message', 0))
        if extra_context is None:
            extra_context = {}
        extra_context.update({
            'title':    _('Recipients of message {}').format(message.subject),
            'message': message,
            'message_opts': Message._meta,
        })
        return super(MessageRecipientAdmin, self).changelist_view(request, extra_context)

    def get_urls(self):
        return [
            url(r'^send-mail/$', self.send_mail, name="{}_{}_send_mail".format(
                self.model._meta.app_label, self.model._meta.model_name,
            )),
        ] + super(MessageRecipientAdmin, self).get_urls()

    @transaction.atomic
    def send_mail(self, request):
        try:
            recipient_id = int(request.GET['recipient_id'])
        except:
            return HttpResponseBadRequest()
        recipient = get_object_or_404(MessageRecipient, id=recipient_id)
        recipient.send_mail()
        return HttpResponse('0', content_type="text/json")


