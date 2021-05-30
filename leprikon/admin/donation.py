from django.contrib import admin

from ..models.donation import Donation
from .transaction import TransactionBaseAdmin, TransactionTypeListFilter


@admin.register(Donation)
class DonationAdmin(TransactionBaseAdmin):
    exclude = ("target_registration",)
    list_display = (
        "id",
        "accounted_with_by",
        "download_tag",
        "transaction_type_label",
        "amount_html",
        "organization",
        "donor",
        "last_updated_with_by",
        "mail_sent",
        "note",
    )
    list_export = (
        "id",
        "accounted",
        "accounted_by",
        "transaction_type_label",
        "amount",
        "organization",
        "donor__username",
        "donor",
        "last_updated",
        "last_updated_by",
        "mail_sent",
        "note",
    )
    list_filter = (
        ("transaction_type", TransactionTypeListFilter),
        "organization",
        "donor",
    )
    search_fields = (
        "donor__first_name",
        "donor__last_name",
        "donor__email",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["donor"].required = True
        form.base_fields["organization"].required = True
        return form
