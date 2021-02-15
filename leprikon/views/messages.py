from django.urls import reverse_lazy as reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..forms.messages import MessageFilterForm
from ..models.messages import MessageRecipient
from .generic import BackViewMixin, DetailView, FilteredListView


class MessageListView(FilteredListView):
    model = MessageRecipient
    form_class = MessageFilterForm
    preview_template = "leprikon/message_preview.html"
    template_name = "leprikon/message_list.html"
    message_empty = _("No messages matching given query.")
    paginate_by = 10

    def get_title(self):
        return _("Messages")

    def get_form(self):
        return self.form_class(
            user=self.request.user,
            data=self.request.GET,
        )

    def get_queryset(self):
        return self.get_form().get_queryset()


class MessageDetailView(BackViewMixin, DetailView):
    back_url = reverse("leprikon:message_list")
    model = MessageRecipient

    def get_object(self):
        obj = super().get_object()
        if obj.viewed is None:
            obj.viewed = now()
            obj.save()
        return obj
