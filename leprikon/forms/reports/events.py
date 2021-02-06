from django import forms
from django.utils.translation import ugettext_lazy as _

from ...models.events import Event
from ..form import FormMixin


class EventPaymentsForm(FormMixin, forms.Form):
    date_start = forms.DateField(label=_("Start date"))
    date_end = forms.DateField(label=_("End date"))


class EventPaymentsStatusForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Status for date"))


class EventStatsForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Statistics for date"))
    events = forms.ModelMultipleChoiceField(
        queryset=Event.objects.all(),
        label=_("Events"),
    )
    paid_only = forms.BooleanField(label=_("Count only paid registrations"), required=False)

    def __init__(self, *args, **kwargs):
        school_year = kwargs.pop("school_year")
        super().__init__(*args, **kwargs)
        self.fields["events"].queryset = Event.objects.filter(school_year=school_year)
