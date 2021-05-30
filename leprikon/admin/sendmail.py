from django.utils.translation import ugettext_lazy as _


class SendMailAdminMixin:
    actions = ("send_mail",)

    def send_mail(self, request, queryset):
        for obj in queryset.all():
            obj.send_mail()
        self.message_user(request, _("Selected items were sent by e-mail."))

    send_mail.short_description = _("Send selected items by e-mail")
