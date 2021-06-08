from django import forms
from django.utils.translation import ugettext_lazy as _

from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from ..models.orderables import OrderableRegistration
from ..models.refundrequest import RefundRequest
from ..models.transaction import Transaction
from ..utils import comma_separated, currency, first_upper
from .fields import ReadonlyField
from .form import FormMixin


class RefundRequestBaseForm(FormMixin, forms.ModelForm):
    def __init__(self, registration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registration = registration
        self.readonly_fields = [
            ReadonlyField(label=first_upper(registration.subject.subject_type.name), value=registration.subject.name)
        ]
        if registration.subject.registration_type_participants:
            if len(registration.all_participants) > 1:
                label = _("Participants")
            else:
                label = _("Participant")
            self.readonly_fields.append(
                ReadonlyField(label=label, value=comma_separated(registration.all_participants))
            )
        elif registration.subject.registration_type_groups:
            self.readonly_fields.append(ReadonlyField(label=_("Contact person"), value=registration.group.full_name))
            if registration.group.name:
                self.readonly_fields.append(ReadonlyField(label=_("Group name"), value=registration.group.name))
        self.readonly_fields.append(
            ReadonlyField(label=_("Overpaid amount"), value=currency(registration.payment_status.overpaid))
        )


class RefundRequestForm(RefundRequestBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.registration = self.registration
        self.instance.requested_by_id = self.registration.user_id

    class Meta:
        model = RefundRequest
        fields = ["bank_account"]


class PaymentTransferForm(RefundRequestBaseForm):
    instance: Transaction

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_target_registration_ids = [
            registration.id
            for Registration in (CourseRegistration, EventRegistration, OrderableRegistration)
            for registration in Registration.objects.filter(user_id=self.registration.user_id)
            if registration.payment_status.amount_due
        ]
        registration_choices = self.fields["target_registration"].widget.choices
        registration_choices.queryset = registration_choices.queryset.filter(id__in=valid_target_registration_ids)
        self.instance.source_registration = self.registration
        self.instance.accounted_by_id = self.registration.user_id
        self.instance.transaction_type = Transaction.TRANSFER

    def clean(self):
        self.cleaned_data = super().clean()
        target_registration = self.cleaned_data.get("target_registration")
        if target_registration:
            self.instance.amount = min(
                self.registration.payment_status.overpaid,
                target_registration.payment_status.amount_due,
            )
        return self.cleaned_data

    class Meta:
        model = Transaction
        fields = ["target_registration"]


class DonationForm(RefundRequestBaseForm):
    instance: Transaction

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.source_registration = self.registration
        self.instance.accounted_by_id = self.registration.user_id
        self.instance.transaction_type = Transaction.DONATION_TRANSFER
        self.instance.amount = self.registration.payment_status.overpaid

    class Meta:
        model = Transaction
        fields = []
