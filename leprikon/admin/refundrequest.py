from datetime import date
from random import randrange

from bankreader.models import Account
from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.leprikonsite import LeprikonSite
from ..models.refundrequest import RefundRequest
from ..models.utils import BankAccount
from ..utils import amount_color, ascii, currency
from .export import AdminExportMixin
from .filters import SchoolYearListFilter, SubjectListFilter, SubjectTypeListFilter
from .utils import datetime_with_by


@admin.register(RefundRequest)
class RefundRequestAdmin(AdminExportMixin, admin.ModelAdmin):
    actions = ("export_as_abo",)
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

    def export_as_abo(self, request, queryset):
        class AccountForm(forms.Form):
            account = forms.ModelChoiceField(label=Account._meta.verbose_name, queryset=Account.objects.all())
            constant_symbol = forms.IntegerField(label=_("Constant symbol"), max_value=9999, required=False)
            message = forms.CharField(label=_("Message for recipient"), max_length=35, required=False)

        if request.POST.get("post", "no") == "yes":
            form = AccountForm(request.POST)
            if form.is_valid():
                return self._export_as_abo(
                    queryset,
                    BankAccount(form.cleaned_data["account"].iban),
                    form.cleaned_data["constant_symbol"] or 0,
                    form.cleaned_data["message"] or "",
                )
        else:
            form = AccountForm()

        adminform = admin.helpers.AdminForm(
            form,
            [(None, {"fields": list(form.base_fields)})],
            {},
            None,
            model_admin=self,
        )

        return render(
            request,
            "leprikon/admin/action_form.html",
            dict(
                title=_("Export setup"),
                opts=self.model._meta,
                adminform=adminform,
                media=self.media + adminform.media,
                action="export_as_abo",
                action_checkbox_name=admin.helpers.ACTION_CHECKBOX_NAME,
                select_across=request.POST["select_across"],
                selected=request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME),
            ),
        )

    def _export_as_abo(self, queryset, bank_account: BankAccount, constant_symbol: int, message: str):
        batch_id = randrange(1, 1000)

        refund_requests: list[RefundRequest] = list(queryset)
        today = f"{date.today():%d%m%y}"
        message = ascii(message)
        site_name = ascii(LeprikonSite.objects.get_current().name)
        sum_amount = sum(rr.amount for rr in refund_requests if rr.amount)

        response = HttpResponse(content_type="text/abo; charset=ascii")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{ascii(str(self.model._meta.verbose_name))} {today} {batch_id}.abo"'

        lines = []

        # write header

        # header, date, customer name, customer number, batch number range, unused
        lines.append(f"UHL1{today}{site_name[:20].ljust(20)}0000000000001999000000000000")
        lines.append(f"1 1501 {batch_id:03}000 {bank_account.bank_code}")
        lines.append(f"2 {bank_account.account_code} {sum_amount}00 {today}")

        # write records

        for refund_request in refund_requests:
            if refund_request.amount:
                lines.append(
                    " ".join(
                        [
                            refund_request.bank_account.account_code,
                            str(refund_request.amount * 100),
                            str(refund_request.registration.variable_symbol),
                            f"{refund_request.bank_account.bank_code}{constant_symbol:04}",
                            "0",  # specific symbol
                            f"AV:{site_name[:35]}|{message[:35]}",
                        ]
                    )
                )

        # write footer

        lines.append("3 +")
        lines.append("5 +")
        lines.append("")

        response.write("\r\n".join(lines).encode("ascii", errors="ignore"))

        return response

    export_as_abo.short_description = _("Export selected records as ABO")
