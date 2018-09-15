from django import forms
from django.utils.translation import ugettext_lazy as _

from ..form import GetFormMixin


class CoursePaymentsForm(GetFormMixin, forms.Form):
    date_start  = forms.DateField(label=_('Start date'))
    date_end    = forms.DateField(label=_('End date'))


class CoursePaymentsStatusForm(GetFormMixin, forms.Form):
    date    = forms.DateField(label=_('Status for date'))


class CourseStatsForm(GetFormMixin, forms.Form):
    date        = forms.DateField(label=_('Statistics for date'))
    paid_only   = forms.BooleanField(label=_('Count only paid registrations'), required=False)
