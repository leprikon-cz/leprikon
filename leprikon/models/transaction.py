from collections import OrderedDict
from decimal import Decimal

from bankreader.models import Transaction as BankreaderTransaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django_pays.models import Payment as PaysPayment

from ..conf import settings
from ..utils import currency
from .fields import PriceField
from .leprikonsite import LeprikonSite
from .organizations import Organization
from .pdfmail import PdfExportAndMailMixin


class TransactionManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        if self.model.transaction_types:
            qs = qs.filter(transaction_type__in=self.model.transaction_types)
        return qs


class AbstractTransaction(models.Model):
    accounted = models.DateTimeField(_("accounted time"), default=timezone.now)
    accounted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("accounted by"),
    )
    last_updated = models.DateTimeField(_("last updated time"), editable=False, null=True)
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("last updated by"),
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        try:
            super().clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        if self.amount == 0:
            errors["amount"] = [_("Amount can not be zero.")]
        if self.accounted:
            max_closure_date = LeprikonSite.objects.get_current().max_closure_date
            if max_closure_date and self.accounted.date() <= max_closure_date:
                errors["accounted"] = [
                    _("Date must be after the last account closure ({}).").format(formats.date_format(max_closure_date))
                ]
        if errors:
            raise ValidationError(errors)


class Transaction(PdfExportAndMailMixin, AbstractTransaction):
    PAYMENT_CASH = "PAYMENT_CASH"
    PAYMENT_BANK = "PAYMENT_BANK"
    PAYMENT_ONLINE = "PAYMENT_ONLINE"
    RETURN_CASH = "RETURN_CASH"
    RETURN_BANK = "RETURN_BANK"
    TRANSFER = "TRANSFER"
    DONATION_CASH = "DONATION_CASH"
    DONATION_BANK = "DONATION_BANK"
    DONATION_ONLINE = "DONATION_ONLINE"
    DONATION_TRANSFER = "DONATION_TRANSFER"
    TRANSACTION_TYPE_LABELS = OrderedDict(
        [
            (PAYMENT_CASH, _("payment - cash")),
            (PAYMENT_BANK, _("payment - bank")),
            (PAYMENT_ONLINE, _("payment - online")),
            (RETURN_CASH, _("returned payment - cash")),
            (RETURN_BANK, _("returned payment - bank")),
            (TRANSFER, _("transfer between registrations")),
            (DONATION_CASH, _("donation - cash")),
            (DONATION_BANK, _("donation - bank")),
            (DONATION_ONLINE, _("donation - online")),
            (DONATION_TRANSFER, _("transfer from registration to donation")),
        ]
    )
    PAYMENTS = frozenset({PAYMENT_CASH, PAYMENT_BANK, PAYMENT_ONLINE, TRANSFER})
    RETURNS = frozenset({RETURN_CASH, RETURN_BANK, TRANSFER, DONATION_TRANSFER})
    SUBJECTS = frozenset(PAYMENTS.union(RETURNS))
    DONATIONS = frozenset({DONATION_CASH, DONATION_BANK, DONATION_ONLINE, DONATION_TRANSFER})
    BANKS = frozenset({PAYMENT_BANK, RETURN_BANK, DONATION_BANK})
    ONLINES = frozenset({PAYMENT_ONLINE, DONATION_ONLINE})

    # manager setup
    objects = TransactionManager()
    object_name = "transaction"
    transaction_types = None  # all

    # basic fields
    transaction_type = models.CharField(_("payment type"), max_length=30, choices=TRANSACTION_TYPE_LABELS.items())
    amount = PriceField(_("amount"), validators=[MinValueValidator(Decimal("0.01"))])
    note = models.CharField(_("note"), max_length=300, blank=True, default="")

    # not editable
    mail_sent = models.DateTimeField(_("mail sent"), editable=False, null=True)

    # subject payment fields
    source_registration = models.ForeignKey(
        "SubjectRegistration",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="returned_payments",
        verbose_name=_("source registration"),
        help_text=_("The payment will be deducted from this registration."),
    )
    target_registration = models.ForeignKey(
        "SubjectRegistration",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("target registration"),
        help_text=_("The payment will be added to this registration."),
    )

    # donation fields
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="leprikon_donations",
        verbose_name=_("donor user"),
    )
    organization = models.ForeignKey(
        Organization,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="donations",
        verbose_name=_("organization"),
    )

    # bank fields
    bankreader_transaction = models.OneToOneField(
        BankreaderTransaction,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_("bank account transaction"),
    )
    pays_payment = models.OneToOneField(
        PaysPayment,
        blank=True,
        editable=False,
        limit_choices_to={"status": PaysPayment.REALIZED},
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_("online payment"),
    )

    class Meta:
        app_label = "leprikon"
        ordering = ("accounted",)
        verbose_name = _("transaction")
        verbose_name_plural = _("transactions")

    def clean(self):
        errors = {}
        try:
            super().clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # prefill values
        if self.transaction_type == self.DONATION_TRANSFER and self.source_registration is not None:
            if not self.donor:
                self.donor = self.source_registration.user
            if not self.organization:
                self.organization = self.source_registration.organization

        mandatory_fields = []
        forbidden_fields = []

        if self.transaction_type in self.PAYMENTS:
            mandatory_fields.append("target_registration")
        elif self.transaction_type:
            forbidden_fields.append("target_registration")

        if self.transaction_type in self.RETURNS:
            mandatory_fields.append("source_registration")
        elif self.transaction_type:
            forbidden_fields.append("source_registration")

        if self.transaction_type in self.DONATIONS:
            mandatory_fields.append("donor")
            mandatory_fields.append("organization")
        elif self.transaction_type:
            forbidden_fields.append("donor")
            forbidden_fields.append("organization")

        if self.transaction_type and self.transaction_type not in self.BANKS:
            forbidden_fields.append("bankreader_transaction")

        if self.transaction_type and self.transaction_type not in self.ONLINES:
            forbidden_fields.append("pays_payment")

        for field in mandatory_fields:
            if not getattr(self, field):
                errors.setdefault(field, []).append(
                    _("This field is mandatory for transaction type {transaction_type}.").format(
                        transaction_type=self.transaction_type_label
                    )
                )
        for field in forbidden_fields:
            if getattr(self, field):
                errors.setdefault(field, []).append(
                    _("This field is forbidden for transaction type {transaction_type}.").format(
                        transaction_type=self.transaction_type_label
                    )
                )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.transaction_type_label} {currency(self.amount)}"

    @cached_property
    def transaction_type_label(self):
        return self.TRANSACTION_TYPE_LABELS.get(self.transaction_type, "-")

    transaction_type_label.short_description = _("payment type")

    def get_absolute_url(self):
        return reverse(f"leprikon:{self.object_name}_pdf", kwargs={"pk": self.pk, "slug": f"{self.slug}"})

    @cached_property
    def slug(self):
        return slugify(f"{self}-{self.id}")

    def send_mail(self, event="received"):
        with transaction.atomic():
            self.mail_sent = timezone.now()
            self.save()
            super().send_mail(event)
