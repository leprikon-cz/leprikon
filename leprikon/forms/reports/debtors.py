from django import forms
from django.utils.translation import gettext_lazy as _

from ..form import FormMixin


class DebtorsForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Status for date"))
