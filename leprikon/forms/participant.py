from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..models import Participant
from ..utils import get_birth_date

from .form import FormMixin


class ParticipantForm(FormMixin, forms.ModelForm):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ParticipantForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance.user = self.user
        return super(ParticipantForm, self).save(commit)
    save.alters_data = True

    def clean_birth_num(self):
        try:
            get_birth_date(self.cleaned_data['birth_num'])
        except:
            raise forms.ValidationError(_('Failed to parse birth day'), code='invalid')
        return self.cleaned_data['birth_num']

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

