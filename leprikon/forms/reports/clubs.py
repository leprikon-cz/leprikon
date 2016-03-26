from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..form import FormMixin


class ClubPaymentsForm(FormMixin, forms.Form):
    date_start  = forms.DateField(label=_('Start date'))
    date_end    = forms.DateField(label=_('End date'))



class ClubPaymentsStatusForm(FormMixin, forms.Form):
    date    = forms.DateField(label=_('Status for date'))



