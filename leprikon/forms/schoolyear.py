from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..models.schoolyear import SchoolYear


class SchoolYearForm(forms.Form):
    school_year = forms.ModelChoiceField(
        label       = _('School year'),
        queryset    = SchoolYear.objects.all(),
        empty_label = None,
    )
    back = settings.LEPRIKON_PARAM_BACK

    def __init__(self, request, *args, **kwargs):
        kwargs['initial'] = {'school_year': request.school_year}
        super(SchoolYearForm, self).__init__(*args, **kwargs)
        if not request.user.is_staff:
            self.fields['school_year'].queryset = (
                self.fields['school_year'].queryset.filter(active=True)
            )
