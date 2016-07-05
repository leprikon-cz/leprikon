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
    paginate_by         = 10

    def get_title(self):
        return _('Leaders in school year {}').format(self.request.school_year)

    def get_queryset(self):
        form = self.get_form()
        return form.get_queryset()

