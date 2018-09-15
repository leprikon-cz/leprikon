from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from .form import FormMixin


class LeaderFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_('Search term'), required=False)

    def __init__(self, school_year, *args, **kwargs):
        super(LeaderFilterForm, self).__init__(*args, **kwargs)
        self.qs = school_year.leaders.all()

    def get_queryset(self):
        if not self.is_valid():
            return self.qs
        qs = self.qs
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(user__first_name__icontains = word) |
                Q(user__last_name__icontains = word) |
                Q(description__icontains = word)
            )
        return qs.distinct()
