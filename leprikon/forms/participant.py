from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms

from ..forms.widgets import CheckboxSelectMultipleBootstrap
from ..models import Participant

from .form import FormMixin


class ParticipantForm(FormMixin, forms.ModelForm):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ParticipantForm, self).__init__(*args, **kwargs)
        self.fields['parents'].widget.choices.queryset = \
        self.fields['parents'].widget.choices.queryset.filter(user=self.user)
        self.fields['parents'].widget = CheckboxSelectMultipleBootstrap(
            choices = self.fields['parents'].widget.choices,
            attrs = {},
        )
        self.fields['parents'].help_text = None

    def save(self, commit=True):
        self.instance.user = self.user
        return super(ParticipantForm, self).save(commit)
    save.alters_data = True


    class Meta:
        model = Participant
        fields = [
            'first_name', 'last_name', 'birth_num',
            'age_group', 'insurance',
            'street', 'city', 'postal_code', 'citizenship',
            'email', 'phone',
            'school', 'school_other', 'school_class',
            'health',
            'parents',
        ]

