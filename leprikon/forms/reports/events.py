from django import forms
from django.utils.translation import ugettext_lazy as _

from ..form import GetFormMixin


class EventPaymentsForm(GetFormMixin, forms.Form):
    date_start  = forms.DateField(label=_('Start date'))
    date_end    = forms.DateField(label=_('End date'))


class EventPaymentsStatusForm(GetFormMixin, forms.Form):
    date    = forms.DateField(label=_('Status for date'))


class EventStatsForm(GetFormMixin, forms.Form):
    date        = forms.DateField(label=_('Statistics for date'))
    paid_only   = forms.BooleanField(label=_('Count only paid registrations'), required=False)
