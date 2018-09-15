from django import forms
from django.utils.translation import ugettext_lazy as _

from ..form import GetFormMixin


class DebtorsForm(GetFormMixin, forms.Form):
    date = forms.DateField(label=_('Status for date'))
