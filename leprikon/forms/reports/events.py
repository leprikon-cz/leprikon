from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..form import FormMixin


class EventPaymentsForm(FormMixin, forms.Form):
    date_start  = forms.DateField(label=_('Start date'))
    date_end    = forms.DateField(label=_('End date'))



class EventPaymentsStatusForm(FormMixin, forms.Form):
    date    = forms.DateField(label=_('Status for date'))
