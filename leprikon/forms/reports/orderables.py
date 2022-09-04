from django import forms
from django.utils.translation import gettext_lazy as _

from ...models.orderables import Orderable
from ..form import FormMixin


class OrderablePaymentsForm(FormMixin, forms.Form):
    date_start = forms.DateField(label=_("Start date"))
    date_end = forms.DateField(label=_("End date"))


class OrderablePaymentsStatusForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Status for date"))


class OrderableStatsForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Statistics for date"))
    orderables = forms.ModelMultipleChoiceField(
        queryset=Orderable.objects.all(),
        label=_("Orderables"),
    )
    paid_only = forms.BooleanField(label=_("Count only paid registrations"), required=False)
    paid_later = forms.BooleanField(label=_("Count registrations paid later"), required=False)
    approved_later = forms.BooleanField(label=_("Count registrations approved later"), required=False)
    unique_participants = forms.BooleanField(label=_("Count only unique participants"), required=False)
    min_days = forms.IntegerField(
        label=_("Minimal number of days"),
        help_text=_("Count only participants attending events that last at least this number of days."),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        school_year = kwargs.pop("school_year")
        super().__init__(*args, **kwargs)
        self.fields["orderables"].queryset = Orderable.objects.filter(school_year=school_year)
