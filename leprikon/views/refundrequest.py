from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..forms.refundrequest import DonationForm, PaymentTransferForm, RefundRequestForm
from ..models.refundrequest import RefundRequest
from ..models.subjects import SubjectRegistration
from .generic import CreateView, DeleteView, UpdateView


class RegistrationMixin:
    def dispatch(self, request, pk, **kwargs):
        self.registration = get_object_or_404(
            SubjectRegistration,
            pk=pk,
            user=request.user,
        ).subjectregistration
        if not self.registration.payment_status.overpaid:
            raise Http404
        return super().dispatch(request, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["registration"] = self.registration
        return kwargs


class RefundRequestCreateView(RegistrationMixin, CreateView):
    form_class = RefundRequestForm
    title = _("New refund request")

    def get_message(self):
        return _("Refund request have been created.")


class RefundRequestQuerysetMixin:
    def get_queryset(self):
        return RefundRequest.objects.filter(registration__user=self.request.user)


class RefundRequestUpdateView(RefundRequestQuerysetMixin, UpdateView):
    form_class = RefundRequestForm
    message = _("Refund request has been updated.")
    title = _("Update refund request")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["registration"] = self.object.registration.subjectregistration
        return kwargs


class RefundRequestDeleteView(RefundRequestQuerysetMixin, DeleteView):
    model = RefundRequest
    title = _("Cancel refund request")
    message = _("Refund request has been canceled.")

    def get_question(self):
        return _("Do You really want to cancel the refund request: {}?").format(self.object)


class PaymentTransferCreateView(RegistrationMixin, CreateView):
    form_class = PaymentTransferForm
    title = _("New payment transfer")

    instructions = _(
        "The payment may only be transferred to a registration, "
        "for which the payment is required. "
        "If You have submitted new registration recently, "
        "You may need to wait until the payment is requested for that registration."
    )

    def get_message(self):
        return _("The payment has been transferred.")


class DonationCreateView(RegistrationMixin, CreateView):
    form_class = DonationForm
    title = _("New donation")

    instructions = _("If You wish, You may transfer the overpaid amount to a donation for our organization.")

    def get_message(self):
        return _("Thank You. Your support is very appreciated.")
