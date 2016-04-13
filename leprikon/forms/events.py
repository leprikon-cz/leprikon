from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from json import dumps

from ..models import Leader, Place, AgeGroup
from ..models.events import EventGroup, Event, EventRegistration
from ..models.fields import DAY_OF_WEEK

from .fields import ReadonlyField
from .form import FormMixin
from .questions import QuestionsFormMixin

User = get_user_model()


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



class EventRegistrationPublicForm(FormMixin, QuestionsFormMixin, forms.ModelForm):

    from .parent import ParentForm as _ParentForm
    from .participant import ParticipantForm
    from .user import UserFormMixin
    from django.contrib.auth.forms import UserCreationForm

    class ParentForm(UserFormMixin, _ParentForm):
        pass

    def __init__(self, event, *args, **kwargs):
        self.event = event
        self.questions = self.event.event_type.all_questions + self.event.all_questions
        super(EventRegistrationPublicForm, self).__init__(*args, **kwargs)
        kwargs['prefix'] = 'parent'
        self.parent_form = self.ParentForm(user=User(), *args, **kwargs)
        kwargs['prefix'] = 'participant'
        self.participant_form = self.ParticipantForm(user=User(), *args, **kwargs)
        kwargs['prefix'] = 'user'
        self.user_form = self.UserCreationForm(*args, **kwargs)
        self.parent_form.fields['email'].required = True
        del self.participant_form.fields['parents']

    def is_valid(self):
        return super(EventRegistrationPublicForm, self).is_valid() \
            and self.parent_form.is_valid() \
            and self.participant_form.is_valid() \
            and self.user_form.is_valid()

    def save(self, commit=True):
        user = self.user_form.save()
        parent = self.parent_form.instance
        participant = self.participant_form.instance

        user.first_name = parent.first_name
        user.last_name  = parent.last_name
        user.email      = parent.email
        user.save()

        parent.user = user
        parent.save()

        participant.user = user
        participant.save()
        participant.parents.add(parent)

        self.instance.event         = self.event
        self.instance.participant   = participant
        self.instance.age_group     = participant.age_group
        self.instance.citizenship   = participant.citizenship
        self.instance.insurance     = participant.insurance
        self.instance.school        = participant.school
        self.instance.school_other  = participant.school_other
        self.instance.school_class  = participant.school_class
        self.instance.health        = participant.health
        return super(EventRegistrationPublicForm, self).save(commit)
    save.alters_data = True

    class Meta:
        model = EventRegistration
        fields = ()



class EventRegistrationBaseForm(QuestionsFormMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            self.event          = kwargs['instance'].event
            self.participant    = kwargs['instance'].participant
        else:
            self.event          = kwargs.pop('event')
            self.participant    = kwargs.pop('participant')
        self.questions          = self.event.event_type.all_questions + self.event.all_questions
        super(EventRegistrationBaseForm, self).__init__(*args, **kwargs)
        if not self.instance.id:
            for attr in ['age_group', 'citizenship', 'insurance', 'school', 'school_other', 'school_class', 'health']:
                self.initial[attr] = getattr(self.participant, attr)
        self.fields['age_group'].widget.choices.queryset = self.event.age_groups



class EventRegistrationForm(FormMixin, EventRegistrationBaseForm):

    def __init__(self, *args, **kwargs):
        super(EventRegistrationForm, self).__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_('Event'),       value=self.event),
            ReadonlyField(label=_('Participant'), value=self.participant),
        ]

    def save(self, commit=True):
        self.instance.event = self.event
        self.instance.participant = self.participant
        return super(EventRegistrationForm, self).save(commit)
    save.alters_data = True

    class Meta:
        model = EventRegistration
        fields = [
            'age_group', 'citizenship', 'insurance',
            'school', 'school_other', 'school_class', 'health',
        ]



class EventRegistrationAdminForm(forms.ModelForm):

    class Meta:
        model = EventRegistration
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EventRegistrationAdminForm, self).__init__(*args, **kwargs)
        self.fields['age_group'].widget.choices.queryset = kwargs['instance'].event.age_groups

