from django.utils.translation import ugettext_lazy as _

from ..forms.billing_info import BillingInfoForm
from ..models.roles import BillingInfo
from ..utils import reverse_with_back
from .generic import CreateView, DeleteView, ListView, UpdateView


class GetQerysetMixin:
    def get_queryset(self):
        return self.request.user.leprikon_billing_info.all()


class BillingInfoListView(GetQerysetMixin, ListView):
    add_label = _("add billing information")
    preview_template = "leprikon/billing_info_preview.html"

    def get_title(self):
        return _("Billing information")

    def get_add_url(self):
        return reverse_with_back(self.request, "leprikon:billing_info_create")


class GetFromKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class BillingInfoCreateView(GetFromKwargsMixin, GetQerysetMixin, CreateView):
    form_class = BillingInfoForm
    title = _("New billing information")

    def get_message(self):
        return _("New billing information {} have been created.").format(self.object)


class BillingInfoUpdateView(GetFromKwargsMixin, GetQerysetMixin, UpdateView):
    form_class = BillingInfoForm
    message = _("Billing information have been updated.")
    title = _("Change billing information")


class BillingInfoDeleteView(GetQerysetMixin, DeleteView):
    model = BillingInfo
    title = _("Delete billing information")
    message = _("Billing information have been deleted.")

    def get_question(self):
        return _("Do You really want to delete the billing information: {}?").format(self.object)
