from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from ..models import Leader
from ..forms.leaders import LeaderFilterForm

from .generic import FilteredListView

class LeaderListView(FilteredListView):
    model               = Leader
    form_class          = LeaderFilterForm
    preview_template    = 'leprikon/leader_preview.html'
    template_name       = 'leprikon/leader_list.html'
    message_empty       = _('No leaders matching given query.')

    def get_title(self):
        return _('Leaders in school year {}').format(self.request.school_year)

    def get_queryset(self):
        qs = super(LeaderListView, self).get_queryset()
        qs = qs.filter(school_years=self.request.school_year)
        form = self.get_form()
        if form.is_valid():
            for word in form.cleaned_data['q'].split():
                qs = qs.filter(
                    Q(user__first_name__icontains = word)
                  | Q(user__last_name__icontains = word)
                  | Q(description__icontains = word)
                )
        return qs

