from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.utils.translation import ugettext_lazy as _

from .form import FormMixin


class LeaderFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_('Search term'), required=False)

    def __init__(self, request, *args, **kwargs):
        super(LeaderFilterForm, self).__init__(*args, **kwargs)

