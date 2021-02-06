from django.utils.translation import ugettext_lazy as _

from ..forms.leaders import LeaderFilterForm
from ..models.roles import Leader
from .generic import FilteredListView


class LeaderListView(FilteredListView):
    model = Leader
    form_class = LeaderFilterForm
    preview_template = "leprikon/leader_preview.html"
    template_name = "leprikon/leader_list.html"
    message_empty = _("No leaders matching given query.")
    paginate_by = 10

    def get_title(self):
        return _("Leaders in school year {}").format(self.request.school_year)

    def get_form(self):
        return self.form_class(
            school_year=self.request.school_year,
            data=self.request.GET,
        )

    def get_queryset(self):
        return self.get_form().get_queryset()
