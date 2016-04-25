from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..models import Leader, Place, AgeGroup
from ..models.events import EventType, EventGroup, Event, EventRegistration

from .form import FormMixin


class EventFilterForm(FormMixin, forms.Form):
    q           = forms.CharField(label=_('Search term'), required=False)
    event_type  = forms.ModelMultipleChoiceField(queryset=None, label=_('Event type'), required=False)
    group       = forms.ModelMultipleChoiceField(queryset=None, label=_('Group'), required=False)
    leader      = forms.ModelMultipleChoiceField(queryset=None, label=_('Leader'), required=False)
    place       = forms.ModelMultipleChoiceField(queryset=None, label=_('Place'), required=False)
    age_group   = forms.ModelMultipleChoiceField(queryset=None, label=_('Age group'), required=False)
    past        = forms.BooleanField(label=_('Include past'), required=False)
    invisible   = forms.BooleanField(label=_('Show invisible'), required=False)

    def __init__(self, request, school_year=None, event_types=None, **kwargs):
        super(EventFilterForm, self).__init__(**kwargs)
        self.request = request

        school_year = school_year or request.school_year
        event_types = event_types or EventType.objects.all()
        event_types_list = list(event_types)

        # filter events by plugin settings
        self.events = school_year.events.filter(event_type__in=event_types_list)
        if not request.user.is_staff or 'invisible' not in request.GET:
            self.events = self.events.filter(public=True)

        event_ids = [e[0] for e in self.events.values_list('id').order_by()]
        self.fields['event_type'].queryset = event_types
        self.fields['group'     ].queryset = EventGroup.objects.filter(events__id__in=event_ids).distinct()
        self.fields['leader'    ].queryset = Leader.objects.filter(events__id__in=event_ids).distinct().order_by('user__first_name', 'user__last_name')
        self.fields['place'     ].queryset = Place.objects.filter(events__id__in=event_ids).distinct()
        self.fields['age_group' ].queryset = AgeGroup.objects.filter(events__id__in=event_ids).distinct()
        if len(event_types_list) == 1:
            del self.fields['event_type']
        if not request.user.is_staff:
            del self.fields['invisible']
        for f in self.fields:
            self.fields[f].help_text=None

    def get_queryset(self):
        qs = self.events
        if not self.is_valid():
            return qs
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(name__icontains = word)
              | Q(description__icontains = word)
            )
        if 'event_type' in self.cleaned_data and self.cleaned_data['event_type']:
            qs = qs.filter(event_type__in = self.cleaned_data['event_type'])
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

