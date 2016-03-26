from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms

from .form import FormMixin


class ConfirmForm(FormMixin, forms.Form):
    answer = forms.BooleanField()

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(ConfirmForm, self).__init__(*args, **kwargs)

    def save(self):
        return self.instance

