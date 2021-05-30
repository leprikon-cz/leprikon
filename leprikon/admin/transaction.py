from bankreader.models import Transaction as BankreaderTransaction
from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.transaction import Transaction
from ..utils import amount_color, currency
from .export import AdminExportMixin
from .pdf import PdfExportAdminMixin
from .sendmail import SendMailAdminMixin
from .utils import datetime_with_by


class TransactionTypeListFilter(admin.ChoicesFieldListFilter):
    def choices(self, changelist):
        yield {
            "selected": self.lookup_val is None,
            "query_string": changelist.get_query_string({}, [self.lookup_kwarg, self.lookup_kwarg_isnull]),
            "display": _("All"),
        }
        none_title = ""
        for lookup, title in self.field.flatchoices:
            if lookup is None:
                none_title = title
                continue
            if self.field.model.transaction_types and lookup not in self.field.model.transaction_types:
                continue
            yield {
                "selected": force_text(lookup) == self.lookup_val,
                "query_string": changelist.get_query_string({self.lookup_kwarg: lookup}, [self.lookup_kwarg_isnull]),
                "display": title,
            }
        if none_title:
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": changelist.get_query_string(
                    {
                        self.lookup_kwarg_isnull: "True",
                    },
                    [self.lookup_kwarg],
                ),
                "display": none_title,
            }


class TransactionAdminMixin:
    date_hierarchy = "accounted"
    ordering = ("-accounted",)

    accounted_with_by = datetime_with_by("accounted", _("accounted time"))
    last_updated_with_by = datetime_with_by("last_updated", _("last updated time"))

    def is_closed(self, request, obj):
        return (
            obj
            and request.leprikon_site.max_closure_date
            and request.leprikon_site.max_closure_date > obj.accounted.date()
        )

    def has_delete_permission(self, request, obj=None):
        if self.is_closed(request, obj):
            return False
        else:
            return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            # it is strange, but obj given to this method contains values from request.POST
            # but we need to decide according to current state in database
            obj = self.model.objects.get(pk=obj.pk)
        if self.is_closed(request, obj):
            return tuple(set(readonly_fields).union(set(self.closed_fields)))
        else:
            return readonly_fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:

            def delete_selected(model_admin, request, queryset):
                if request.leprikon_site.max_closure_date:
                    queryset = queryset.filter(accounted__date__gt=request.leprikon_site.max_closure_date)
                return admin.actions.delete_selected(model_admin, request, queryset)

            actions["delete_selected"] = (delete_selected, *actions["delete_selected"][1:])
        return actions

    def amount_html(self, obj):
        return format_html(
            '<b style="color: {color}">{amount}</b>',
            color=amount_color(obj.amount),
            amount=currency(abs(obj.amount)),
        )

    amount_html.short_description = _("amount")
    amount_html.admin_order_field = "amount"
    amount_html.allow_tags = True

    def save_model(self, request, obj, form, change):
        if change:
            obj.last_updated = timezone.now()
            obj.last_updated_by = request.user
        else:
            obj.accounted = timezone.now()
            obj.accounted_by = request.user
        super().save_model(request, obj, form, change)


class TransactionBaseAdmin(
    TransactionAdminMixin, PdfExportAdminMixin, SendMailAdminMixin, AdminExportMixin, admin.ModelAdmin
):
    list_display = ("id", "accounted_with_by", "transaction_type", "amount", "last_updated_with_by", "note")
    closed_fields = ("accounted", "amount", "target_registration", "source_registration", "donor", "organization")
    list_editable = ("note",)
    raw_id_fields = ("target_registration", "source_registration", "bankreader_transaction", "pays_payment", "donor")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if self.model.transaction_types:
            form.base_fields["transaction_type"].choices = (
                (value, label)
                for value, label in Transaction.TRANSACTION_TYPE_LABELS.items()
                if value in self.model.transaction_types
            )
        return form

    def get_urls(self):
        populate_view = self.admin_site.admin_view(
            permission_required(f"{self.model._meta.app_label}.add_{self.model._meta.model_name}")(self.populate)
        )
        return [
            urls_url(r"populate.json$", populate_view, name="leprikon_subjectpayment_populate")
        ] + super().get_urls()

    def populate(self, request):
        try:
            return JsonResponse(
                {
                    "amount": get_object_or_404(
                        BankreaderTransaction,
                        id=int(request.GET["bankreader_transaction"]),
                    ).amount
                }
            )
        except (KeyError, ValueError):
            return HttpResponseBadRequest()


@admin.register(Transaction)
class TrancactionAdmin(TransactionBaseAdmin):
    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}
