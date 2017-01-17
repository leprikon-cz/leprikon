from __future__ import unicode_literals

from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from .form import FormMixin


class LeaderFilterForm(FormMixin, forms.Form):
    q           = forms.CharField(label=_('Search term'), required=False)

    def __init__(self, request, school_year=None, *args, **kwargs):
        super(LeaderFilterForm, self).__init__(*args, **kwargs)
        self.request = request
        school_year = school_year or request.school_year

        # pre filter leaders by initial params
        self.leaders = school_year.leaders.all()

    def get_queryset(self):
        qs = self.leaders
        if not self.is_valid():
            return qs
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(user__first_name__icontains = word) |
                Q(user__last_name__icontains = word) |
                Q(description__icontains = word)
            )
        return qs.distinct()
