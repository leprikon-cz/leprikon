from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..models import Participant
from ..utils import get_birth_date

from .form import FormMixin


class ParticipantForm(FormMixin, forms.ModelForm):

    def __init__(self, user, **kwargs):
        self.user = user
        super(ParticipantForm, self).__init__(**kwargs)

    def validate_unique(self):
        self.instance.user = self.user
        super(ParticipantForm, self).validate_unique()

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

