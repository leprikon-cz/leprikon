from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..utils import currency
from .fields import BankAccountField
from .subjects import SubjectRegistration


class RefundRequest(models.Model):
    requested = models.DateTimeField(_("requested time"), default=timezone.now, editable=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("requested by"),
    )
    registration: SubjectRegistration = models.OneToOneField(
        SubjectRegistration,
        on_delete=models.PROTECT,
        related_name="refund_request",
        verbose_name=_("registration"),
    )
    bank_account = BankAccountField(_("bank account number"))

    class Meta:
        app_label = "leprikon"
        ordering = ("requested",)
        verbose_name = _("refund request")
        verbose_name_plural = _("refund requests")

    def __str__(self):
        return f"{self.registration}, {currency(self.amount)}"

    def clean(self):
        super().clean()
        if not self.amount:
            raise ValidationError({"registration": [_("Refund may only be requested for overpaid registrations.")]})

    @cached_property
    def amount(self):
        return self.registration and self.registration.payment_status.overpaid

    amount.short_description = _("amount")
