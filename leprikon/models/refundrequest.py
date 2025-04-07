from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ..utils import attributes, currency
from .activities import Registration
from .fields import BankAccountField


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
    registration: Registration = models.OneToOneField(
        Registration,
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

    @attributes(short_description=_("amount"))
    @cached_property
    def amount(self):
        return self.registration and self.registration.payment_status.overpaid
