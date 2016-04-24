from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms

from ..models import Participant

from .form import FormMixin


class ParticipantForm(FormMixin, forms.ModelForm):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ParticipantForm, self).__init__(*args, **kwargs)

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
        ]

