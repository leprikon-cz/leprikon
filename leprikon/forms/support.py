from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..conf import settings


class SupportForm(forms.Form):
    question = forms.CharField(
        label=_('Help needed?'),
        widget=forms.Textarea(attrs = {'class': 'form-control'}),
        required=False,
    )
    back = settings.LEPRIKON_PARAM_BACK

