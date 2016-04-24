from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..models import Leader, Place, AgeGroup
from ..models.events import EventGroup, Event, EventRegistration

from .form import FormMixin


class EventFilterForm(FormMixin, forms.Form):
    q           = forms.CharField(label=_('Search term'), required=False)
    group       = forms.ModelMultipleChoiceField(queryset=None, label=_('Group'), required=False)
    leader      = forms.ModelMultipleChoiceField(queryset=None, label=_('Leader'), required=False)
    place       = forms.ModelMultipleChoiceField(queryset=None, label=_('Place'), required=False)
    age_group   = forms.ModelMultipleChoiceField(queryset=None, label=_('Age group'), required=False)
    past        = forms.BooleanField(label=_('Include past'), required=False)
    invisible   = forms.BooleanField(label=_('Show invisible'), required=False)

    def __init__(self, request, event_type, *args, **kwargs):
        super(EventFilterForm, self).__init__(*args, **kwargs)
        if event_type:
            self.fields['group' ].queryset = EventGroup.objects.filter(events__event_type = event_type).distinct()
        else:
            self.fields['group' ].queryset = EventGroup.objects.all()
        self.fields['leader'    ].queryset = Leader.objects.filter(school_years=request.school_year).order_by('user__first_name', 'user__last_name')
        self.fields['place'     ].queryset = Place.objects.all()
        self.fields['age_group' ].queryset = AgeGroup.objects.all()
        if not request.user.is_staff:
            del self.fields['invisible']
        for f in self.fields:
            self.fields[f].help_text=None

    def filter_queryset(self, request, qs):
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(name__icontains = word)
              | Q(description__icontains = word)
            )
        if self.cleaned_data['group']:
            qs = qs.filter(groups__in = self.cleaned_data['group'])
        if self.cleaned_data['place']:
            qs = qs.filter(place__in = self.cleaned_data['place'])
        if self.cleaned_data['leader']:
            qs = qs.filter(leaders__in = self.cleaned_data['leader'])
        if self.cleaned_data['age_group']:
            qs = qs.filter(age_groups__in = self.cleaned_data['age_group'])
        if not self.cleaned_data['past']:
            qs = qs.filter(end_date__gte = now())
        if request.user.is_staff and not self.cleaned_data['invisible']:
            qs = qs.filter(public=True)
        return qs



class EventForm(FormMixin, forms.ModelForm):

    class Meta:
        model = Event
        fields = ['description', 'risks', 'plan', 'evaluation']



class EventRegistrationAdminForm(forms.ModelForm):

    class Meta:
        model = EventRegistration
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EventRegistrationAdminForm, self).__init__(*args, **kwargs)
        self.fields['age_group'].widget.choices.queryset = kwargs['instance'].event.age_groups

