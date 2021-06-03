from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.refundrequest import RefundRequest
from ..utils import amount_color, currency
from .export import AdminExportMixin
from .filters import SchoolYearListFilter, SubjectListFilter, SubjectTypeListFilter
from .utils import datetime_with_by


@admin.register(RefundRequest)
class RefundRequestAdmin(AdminExportMixin, admin.ModelAdmin):
    date_hierarchy = "requested"
    ordering = ("-requested",)
    list_display = (
        "id",
        "requested_with_by",
        "registration",
        "amount_html",
        "bank_account",
    )
    list_export = (
        "id",
        "requested",
        "requested_by",
        "registration",
        "registration__variable_symbol",
        "amount",
        "bank_account",
        "iban",
        "bic",
    )
    list_filter = (
        ("registration__subject__school_year", SchoolYearListFilter),
        "registration__subject__department",
        "registration__subject__organization",
        ("registration__subject__subject_type", SubjectTypeListFilter),
        ("registration__subject", SubjectListFilter),
    )
    search_fields = (
        "registration__variable_symbol",
        "registration__subject__name",
        "registration__participants__first_name",
        "registration__participants__last_name",
        "registration__participants__birth_num",
    )
    raw_id_fields = ("registration",)

    def iban(self, obj):
        return obj.bank_account.compact

    iban.short_description = _("IBAN")

    def bic(self, obj):
        return obj.bank_account.bic

    bic.short_description = _("BIC (SWIFT)")

    def amount_html(self, obj):
        return format_html(
            '<b style="color: {color}">{amount}</b>',
            color=amount_color(obj.amount),
            amount=currency(abs(obj.amount)),
        )

    amount_html.short_description = _("amount")
    amount_html.admin_order_field = "amount"
    amount_html.allow_tags = True

    requested_with_by = datetime_with_by("requested", _("requested time"))

    def save_model(self, request, obj, form, change):
        if not change:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)
