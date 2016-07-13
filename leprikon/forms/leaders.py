from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from .form import FormMixin


class LeaderFilterForm(FormMixin, forms.Form):
    q           = forms.CharField(label=_('Search term'), required=False)
    club        = forms.ModelMultipleChoiceField(queryset=None, label=_('Club'), required=False)
    event       = forms.ModelMultipleChoiceField(queryset=None, label=_('Event'), required=False)

    def __init__(self, request, school_year=None, *args, **kwargs):
        super(LeaderFilterForm, self).__init__(*args, **kwargs)
        self.request = request

        school_year = school_year or request.school_year

        # filter lieaders by plugin settings
        self.leaders = school_year.leaders.all()

        leader_ids = [l[0] for l in self.leaders.values_list('id').order_by()]
        self.fields['club'  ].queryset = school_year.clubs.filter(leaders__id__in=leader_ids).distinct()
        self.fields['event' ].queryset = school_year.events.filter(leaders__id__in=leader_ids).distinct()

    def get_queryset(self):
        qs = self.leaders
        if not self.is_valid():
            return qs
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(user__first_name__icontains = word)
              | Q(user__last_name__icontains = word)
              | Q(description__icontains = word)
            )
        if self.cleaned_data['club']:
            qs = qs.filter(clubs__in = self.cleaned_data['club'])
        if self.cleaned_data['event']:
            qs = qs.filter(events__in = self.cleaned_data['event'])
        return qs.distinct()

