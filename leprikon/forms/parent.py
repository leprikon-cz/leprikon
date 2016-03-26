from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms

from ..models import Parent

from .form import FormMixin


class ParentForm(FormMixin, forms.ModelForm):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ParentForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance.user = self.user
        return super(ParentForm, self).save(commit)
    save.alters_data = True

    class Meta:
        model = Parent
        exclude = ['user']

