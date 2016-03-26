from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..models import SchoolYear


class SchoolYearForm(forms.Form):
    school_year = forms.ModelChoiceField(label=_('School year'),
        queryset = SchoolYear.objects.all(),
        empty_label = None,
    )
    back = settings.LEPRIKON_PARAM_BACK

