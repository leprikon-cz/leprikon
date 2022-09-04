from django.utils.translation import gettext_lazy as _

from ..utils import attributes


class SendMailAdminMixin:
    actions = ("send_mail",)

    @attributes(short_description=_("Send selected items by e-mail"))
    def send_mail(self, request, queryset):
        for obj in queryset.all():
            obj.send_mail()
        self.message_user(request, _("Selected items were sent by e-mail."))
