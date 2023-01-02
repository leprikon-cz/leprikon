from django import forms
from django.contrib import admin
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..forms.messages import MessageAdminForm
from ..models.messages import Message, MessageAttachment, MessageRecipient
from ..utils import attributes


def messagerecipient_send_mails(request, message, recipients, media):
    return render(
        request,
        "admin/leprikon/messagerecipient/send_mails.html",
        {
            "title": _("Sending emails"),
            "message": message,
            "recipients": recipients,
            "media": media,
            "message_opts": Message._meta,
            "opts": MessageRecipient._meta,
        },
    )


class SendMessageAdminMixin:
    actions = ("send_message", "add_to_message")

    def get_message_recipients(self, request, queryset):
        raise NotImplementedError("{} must implement method get_message_recipients".format(self.__class__.__name__))

    @attributes(short_description=_("Send message"))
    def send_message(self, request, queryset):
        request.method = "GET"
        request.leprikon_message_recipients = [r.id for r in self.get_message_recipients(request, queryset)]
        return admin.site._registry[Message].changeform_view(request, form_url=reverse("admin:leprikon_message_add"))

    @attributes(short_description=_("Add recipients to existing message"))
    def add_to_message(self, request, queryset):
        class MessageForm(forms.Form):
            message = forms.ModelChoiceField(
                label=_("Target message"),
                help_text=_("Recipients will be added to selected message."),
                queryset=Message.objects.all(),
            )

        if request.POST.get("post", "no") == "yes":
            form = MessageForm(request.POST)
            if form.is_valid():
                message = form.cleaned_data["message"]
                for recipient in self.get_message_recipients(request, queryset):
                    MessageRecipient.objects.get_or_create(message=message, recipient=recipient)
                return HttpResponseRedirect(
                    reverse("admin:leprikon_messagerecipient_changelist") + "?message={}".format(message.id)
                )
        else:
            form = MessageForm()
        return render(
            request,
            "admin/leprikon/message/add_recipients.html",
            {
                "title": _("Select target message"),
                "queryset": queryset,
                "opts": self.model._meta,
                "form": form,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )


class MessageAttachmentInlineAdmin(admin.TabularInline):
    model = MessageAttachment
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    form = MessageAdminForm
    inlines = (MessageAttachmentInlineAdmin,)
    list_display = ("subject", "created", "recipients", "action_links")
    search_fields = ("subject", "text")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        try:
            initial["recipients"] = request.leprikon_message_recipients
        except Exception:
            pass
        return initial

    @attributes(short_description=_("recipients"))
    def recipients(self, obj):
        return mark_safe(
            (
                '<a href="{recipients_url}">'
                '    <span title="{all_title}">{all_count}</span>'
                '  / <span title="{mails_title}">{mails_count}</span>'
                '  / <span title="{viewed_title}">{viewed_count}</span>'
                "</a> "
            ).format(
                recipients_url=reverse("admin:leprikon_messagerecipient_changelist") + "?message={}".format(obj.id),
                all_title=_("recipients count"),
                mails_title=_("sent mail"),
                viewed_title=_("viewed on site"),
                all_count=obj.recipients.count(),
                mails_count=obj.recipients.exclude(sent_mail=None).count(),
                viewed_count=obj.recipients.exclude(viewed=None).count(),
            )
        )

    @attributes(short_description=_("actions"))
    def action_links(self, obj):
        return mark_safe(
            (
                '<a href="{recipients_url}" class="button" title="{recipients_title}">{recipients}</a> '
                '<a href="{send_mails_all_url}" class="button" title="{send_mails_all_title}">{send_mails_all}</a> '
                '<a href="{send_mails_new_url}" class="button" title="{send_mails_new_title}">{send_mails_new}</a> '
            ).format(
                recipients=_("recipients"),
                recipients_title=_("show recipients details"),
                recipients_url=(reverse("admin:leprikon_messagerecipient_changelist") + "?message={}".format(obj.id)),
                send_mails_all=_("send mails"),
                send_mails_all_title=_("send mail to all recipients"),
                send_mails_all_url=reverse("admin:leprikon_message_send_mails") + "?message={}".format(obj.id),
                send_mails_new=_("send unsent"),
                send_mails_new_title=_("send mails to new recipients only"),
                send_mails_new_url=reverse("admin:leprikon_message_send_mails") + "?message={}&new=1".format(obj.id),
            )
        )

    def get_urls(self):
        return [
            path("send-mails/", self.admin_site.admin_view(self.send_mails), name="leprikon_message_send_mails"),
        ] + super().get_urls()

    def send_mails(self, request):
        try:
            message_id = int(request.GET["message"])
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        message = get_object_or_404(Message, id=message_id)
        recipients = message.recipients.all()
        if request.GET.get("new", False):
            recipients = recipients.filter(sent_mail=None)
        return messagerecipient_send_mails(request, message, recipients, self.media)


@admin.register(MessageRecipient)
class MessageRecipientAdmin(admin.ModelAdmin):
    list_display = ("recipient", "sent", "viewed", "sent_mail")
    actions = ("send_mails",)

    # hide the model from admin index
    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @attributes(short_description=_("Send email to selected recipients"))
    def send_mails(self, request, queryset):
        return messagerecipient_send_mails(
            request,
            message=get_object_or_404(Message, id=request.GET.get("message", 0)),
            recipients=queryset,
            media=self.media,
        )

    def changelist_view(self, request, extra_context=None):
        message = get_object_or_404(Message, id=request.GET.get("message", 0))
        if extra_context is None:
            extra_context = {}
        extra_context.update(
            {
                "title": _("Recipients of message {}").format(message.subject),
                "message": message,
                "message_opts": Message._meta,
            }
        )
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        return [
            path(
                "send-mail/",
                self.admin_site.admin_view(self.send_mail),
                name="leprikon_messagerecipient_send_mail",
            )
        ] + super().get_urls()

    @transaction.atomic
    def send_mail(self, request):
        try:
            recipient_id = int(request.GET["recipient_id"])
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        recipient = get_object_or_404(MessageRecipient, id=recipient_id)
        recipient.send_mail()
        return HttpResponse("0", content_type="text/json")
