from datetime import date
from random import randrange
from typing import List

from bankreader.models import Account
from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..models.leprikonsite import LeprikonSite
from ..models.refundrequest import RefundRequest
from ..models.utils import BankAccount
from ..utils import amount_color, ascii, attributes, currency, localeconv
from .export import AdminExportMixin
from .filters import ActivityListFilter, ActivityTypeListFilter, SchoolYearListFilter
from .utils import datetime_with_by


@admin.register(RefundRequest)
class RefundRequestAdmin(AdminExportMixin, admin.ModelAdmin):
    actions = AdminExportMixin.actions + ("export_payment_orders",)
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
        ("registration__activity__school_year", SchoolYearListFilter),
        "registration__activity__department",
        "registration__activity__organization",
        ("registration__activity__activity_type", ActivityTypeListFilter),
        ("registration__activity", ActivityListFilter),
    )
    search_fields = (
        "registration__variable_symbol",
        "registration__activity__name",
        "registration__participants__first_name",
        "registration__participants__last_name",
        "registration__participants__birth_num",
    )
    raw_id_fields = ("registration",)

    @attributes(short_description=_("IBAN"))
    def iban(self, obj: RefundRequest):
        return obj.bank_account.iban.compact

    @attributes(short_description=_("BIC (SWIFT)"))
    def bic(self, obj):
        return obj.bank_account.iban.bic

    @attributes(admin_order_field="amount", short_description=_("amount"))
    def amount_html(self, obj):
        return mark_safe(
            format_html(
                '<b style="color: {color}">{amount}</b>',
                color=amount_color(obj.amount),
                amount=currency(abs(obj.amount)),
            )
        )

    requested_with_by = datetime_with_by("requested", _("requested time"))

    def save_model(self, request, obj, form, change):
        if not change:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_("Export selected records as payment orders"))
    def export_payment_orders(self, request, queryset):
        class ExportForm(forms.Form):
            account = forms.ModelChoiceField(label=Account._meta.verbose_name, queryset=Account.objects.all())
            format = forms.ChoiceField(
                label=_("Format"),
                choices=[
                    ("abo", "ABO"),
                    ("cfd", "CFD"),
                ],
                widget=forms.RadioSelect,
            )
            constant_symbol = forms.IntegerField(
                label=_("Constant symbol"), initial=308, max_value=9999, required=False
            )
            message = forms.CharField(label=_("Message for recipient"), max_length=35, required=False)

        if request.POST.get("post", "no") == "yes":
            form = ExportForm(request.POST)
            if form.is_valid():
                if form.cleaned_data["format"] == "cfd":
                    return self._export_as_cfd(
                        queryset,
                        BankAccount(form.cleaned_data["account"].iban),
                        form.cleaned_data["constant_symbol"] or 0,
                        form.cleaned_data["message"] or "",
                    )
                return self._export_as_abo(
                    queryset,
                    BankAccount(form.cleaned_data["account"].iban),
                    form.cleaned_data["constant_symbol"] or 0,
                    form.cleaned_data["message"] or "",
                )
        else:
            form = ExportForm()

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
                action="export_payment_orders",
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
        amount_cents = round(sum_amount * 100)

        response = HttpResponse(content_type="text/abo; charset=ascii")
        response["Content-Disposition"] = (
            f'attachment; filename="{ascii(str(self.model._meta.verbose_name))} {today} {batch_id}.abo"'
        )

        lines = []

        # write header

        # header, date, customer name, customer number, batch number range, unused
        lines.append(f"UHL1{today}{site_name[:20].ljust(20)}0000000000001999000000000000")
        lines.append(f"1 1501 {batch_id:03}000 {bank_account.iban.bank_code}")
        lines.append(f"2 {str(bank_account).split('/')[0]} {amount_cents} {today}")

        # write records

        for refund_request in refund_requests:
            if refund_request.amount:
                lines.append(
                    " ".join(
                        [
                            str(refund_request.bank_account).split("/")[0],
                            str(round(refund_request.amount * 100)),
                            str(refund_request.registration.variable_symbol),
                            f"{refund_request.bank_account.iban.bank_code}{constant_symbol:04}",
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

    def _export_as_cfd(self, queryset, bank_account: BankAccount, constant_symbol: int, message: str):
        currency = localeconv["int_curr_symbol"].strip()
        refund_requests: list[RefundRequest] = list(queryset)
        today = f"{date.today():%y%m%d}"
        site_name = ascii(LeprikonSite.objects.get_current().name)

        response = HttpResponse(content_type="text/cfd; charset=ascii")
        response["Content-Disposition"] = (
            f'attachment; filename="{ascii(str(self.model._meta.verbose_name))} {today}.cfd"'
        )

        lines = []

        for n, refund_request in enumerate(refund_requests[:1000], start=1):
            if refund_request.amount:
                receiver_account: BankAccount = refund_request.bank_account
                lines.extend(
                    [
                        f"HD:11 {today} {bank_account.iban.bank_code} {n} {refund_request.bank_account.iban.bank_code}",
                        f"KC:{str(round(refund_request.amount * 100)).rjust(15, '0')} 000000 {currency}",
                        f"UD:{bank_account.account_prefix} {bank_account.account_number} SENDER",
                        f"DI:{cfd_multiline(site_name)}",
                        f"UK:{receiver_account.account_prefix} {receiver_account.account_number} RECEIVER",
                        f"AK:{0}",  # specific symbol
                        f"KI:{cfd_multiline(str(refund_request.registration.user))}",
                        f"EC:{constant_symbol:04}",
                        f"ZK:{refund_request.registration.variable_symbol}",
                        f"AV:{cfd_multiline(message + ' ' + str(refund_request.registration))}",
                    ]
                )

        lines.append("")  # File must end with CRLF
        response.write("\r\n".join(lines).encode("ascii", errors="ignore"))

        return response


def cfd_multiline(s: str) -> str:
    lines: List[str] = []
    line = ""
    for word in s.split():
        if len(word) > 35:
            continue
        if len(line) + len(word) > 34:
            lines.append(line)
            line = ""
        line = line + " " + word if line else word
    lines.append(line)
    return ascii("\r\n   ".join(lines[:4])).upper()
