from __future__ import unicode_literals

from json import dumps

from django import forms
from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..models.agegroup import AgeGroup
from ..models.courses import Course, CourseRegistration
from ..models.events import Event, EventRegistration
from ..models.fields import DAY_OF_WEEK
from ..models.place import Place
from ..models.roles import Leader, Parent, Participant
from ..models.subjects import Subject, SubjectGroup, SubjectType
from ..utils import get_age, get_birth_date
from .form import FormMixin
from .widgets import RadioSelectBootstrap


class SubjectFilterForm(FormMixin, forms.Form):
    q           = forms.CharField(label=_('Search term'), required=False)
    event_types = forms.ModelMultipleChoiceField(queryset=None, label=_('Event type'), required=False)
    groups      = forms.ModelMultipleChoiceField(queryset=None, label=_('Group'), required=False)
    leaders     = forms.ModelMultipleChoiceField(queryset=None, label=_('Leader'), required=False)
    places      = forms.ModelMultipleChoiceField(queryset=None, label=_('Place'), required=False)
    age_groups  = forms.ModelMultipleChoiceField(queryset=None, label=_('Age group'), required=False)
    days_of_week = forms.MultipleChoiceField(label=_('Day of week'),
                                             choices=tuple(sorted(DAY_OF_WEEK.items())), required=False)
    past        = forms.BooleanField(label=_('Include past subjects'), required=False)
    reg_active  = forms.BooleanField(label=_('Available for registration'), required=False)
    invisible   = forms.BooleanField(label=_('Show invisible'), required=False)

    _models = {
        SubjectType.COURSE: Course,
        SubjectType.EVENT:  Event,
    }

    def __init__(self, subject_type_type, subject_types, school_year, is_staff, data, **kwargs):
        super(SubjectFilterForm, self).__init__(data=data, **kwargs)
        self.subject_type_type = subject_type_type

        # pre filter subjects by initial params
        qs = self._models[subject_type_type].objects.filter(school_year=school_year)
        if len(subject_types) == 1:
            qs = qs.filter(subject_type=subject_types[0])
        else:
            qs = qs.filter(subject_type__in=subject_types)
        if not is_staff or 'invisible' not in data:
            qs = qs.filter(public=True)
        self.qs = qs

        subject_ids = set(qs.order_by().values_list('id', flat=True))
        if len(subject_types) == 1:
            del self.fields['event_types']
        else:
            self.fields['event_types'].queryset = SubjectType.objects.filter(id__in=[st.id for st in subject_types])
        self.fields['groups'].queryset  = SubjectGroup.objects.filter(subject_types__in=subject_types,
                                                                      subjects__id__in = subject_ids).distinct()
        self.fields['leaders'].queryset = (Leader.objects.filter(subjects__id__in=subject_ids).distinct()
                                           .order_by('user__first_name', 'user__last_name'))
        self.fields['places'].queryset  = Place.objects.filter(subjects__id__in=subject_ids).distinct()
        self.fields['age_groups'].queryset = AgeGroup.objects.filter(subjects__id__in=subject_ids).distinct()
        if subject_type_type != SubjectType.COURSE:
            del self.fields['days_of_week']
        if subject_type_type != SubjectType.EVENT:
            del self.fields['past']
        if not is_staff:
            del self.fields['invisible']

        for f in self.fields:
            self.fields[f].help_text = None

    def get_queryset(self):
        if not self.is_valid():
            return self.qs
        qs = self.qs
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(name__icontains = word) |
                Q(description__icontains = word)
            )
        if self.cleaned_data.get('event_types'):
            qs = qs.filter(subject_type__in = self.cleaned_data['event_types'])
        if self.cleaned_data['groups']:
            qs = qs.filter(groups__in = self.cleaned_data['groups'])
        if self.cleaned_data['places']:
            qs = qs.filter(place__in = self.cleaned_data['places'])
        if self.cleaned_data['leaders']:
            qs = qs.filter(leaders__in = self.cleaned_data['leaders'])
        if self.cleaned_data['age_groups']:
            qs = qs.filter(age_groups__in = self.cleaned_data['age_groups'])
        if self.subject_type_type == SubjectType.COURSE and self.cleaned_data['days_of_week']:
            qs = qs.filter(times__day_of_week__in = self.cleaned_data['days_of_week'])
        if self.subject_type_type == SubjectType.EVENT and not self.cleaned_data['past']:
            qs = qs.filter(end_date__gte = now())
        if self.cleaned_data['reg_active']:
            qs = qs.filter(reg_from__lte=now()).exclude(reg_to__lte=now()).exclude(price=None)
        return qs.distinct()



class SubjectForm(FormMixin, forms.ModelForm):

    class Meta:
        model = Subject
        fields = ['description', 'risks', 'plan', 'evaluation']



class RegistrationForm(FormMixin, forms.ModelForm):

    def __init__(self, subject, user, **kwargs):
        super(RegistrationForm, self).__init__(**kwargs)
        self.instance.subject = subject
        self.instance.user = user
        self.participants = user.leprikon_participants.exclude(
            birth_num__in=self.instance.subject.active_registrations.values_list('participant_birth_num', flat=True)
        )
        self.parents = user.leprikon_parents.all()

        self.fields['participant_age_group'].widget.choices.queryset = self.instance.subject.age_groups

        # dynamically required fields
        try:
            if get_age(get_birth_date(kwargs['data']['participant_birth_num'])) < 18:
                self.fields['has_parent1'].required = True
            else:
                self.fields['participant_phone'].required = True
                self.fields['participant_email'].required = True
        except:
            pass

        try:
            has_parent = ['has_parent1' in kwargs['data'], 'has_parent2' in kwargs['data']]
        except:
            has_parent = [False, False]
        for n in range(2):
            if has_parent[n]:
                for field in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                    self.fields['parent{}_{}'.format(n + 1, field)].required = True

        # sub forms

        del kwargs['instance']

        class ParticipantSelectForm(FormMixin, forms.Form):
            participant = forms.ChoiceField(
                label   = _('Choose'),
                choices = [('new', _('new participant'))] + list((p.id, p) for p in self.participants),
                initial = 'new',
                widget  = RadioSelectBootstrap(),
            )
        kwargs['prefix'] = 'participant_select'
        self.participant_select_form = ParticipantSelectForm(**kwargs)

        class ParentSelectForm(FormMixin, forms.Form):
            parent = forms.ChoiceField(
                label   = _('Choose'),
                choices = [('new', _('new parent'))] + list((p.id, p) for p in self.parents),
                initial = 'new',
                widget  = RadioSelectBootstrap(),
            )
        kwargs['prefix'] = 'parent1_select'
        self.parent1_select_form = ParentSelectForm(**kwargs)
        kwargs['prefix'] = 'parent2_select'
        self.parent2_select_form = ParentSelectForm(**kwargs)

        kwargs['prefix'] = 'questions'
        self.questions_form = type(str('QuestionsForm'), (FormMixin, forms.Form), dict(
            (q.name, q.get_field()) for q in self.instance.subject.all_questions
        ))(**kwargs)

        kwargs['prefix'] = 'agreement'
        self.agreement_form = self.AgreementForm(**kwargs)

    def is_valid(self):
        return (
            self.participant_select_form.is_valid() and
            self.questions_form.is_valid() and
            self.parent1_select_form.is_valid() and
            self.parent2_select_form.is_valid() and
            self.agreement_form.is_valid() and
            super(RegistrationForm, self).is_valid()
        )

    def save(self, commit=True):
        self.instance.price = self.instance.subject.price
        self.instance.answers = dumps(self.questions_form.cleaned_data)
        super(RegistrationForm, self).save(commit)

        # send mail
        try:
            self.instance.send_mail()
        except:
            import traceback
            from raven.contrib.django.models import client
            traceback.print_exc()
            client.captureException()

        # save / update participant
        if self.participant_select_form.cleaned_data['participant'] == 'new':
            try:
                participant = Participant.objects.get(
                    user        = self.instance.user,
                    birth_num   = self.instance.participant.birth_num,
                )
            except Participant.DoesNotExist:
                participant = Participant()
                participant.user = self.instance.user
        else:
            participant = Participant.objects.get(id=self.participant_select_form.cleaned_data['participant'])
        for attr in ['first_name', 'last_name', 'birth_num', 'age_group', 'street', 'city', 'postal_code',
                     'citizenship', 'insurance', 'phone', 'email', 'school', 'school_other', 'school_class', 'health']:
            setattr(participant, attr, getattr(self.instance.participant, attr))
        participant.save()

        # save / update first parent
        if self.instance.parent1:
            if self.parent1_select_form.cleaned_data['parent'] == 'new':
                parent = Parent()
                parent.user = self.instance.user
            else:
                parent = Parent.objects.get(id=self.parent1_select_form.cleaned_data['parent'])
            for attr in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                setattr(parent, attr, getattr(self.instance.parent1, attr))
            parent.save()

        # save / update second parent
        if self.instance.parent2:
            if self.parent2_select_form.cleaned_data['parent'] == 'new':
                parent = Parent()
                parent.user = self.instance.user
            else:
                parent = Parent.objects.get(id=self.parent2_select_form.cleaned_data['parent'])
            for attr in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                setattr(parent, attr, getattr(self.instance.parent2, attr))
            parent.save()

    class AgreementForm(FormMixin, forms.Form):
        agreement = forms.BooleanField(
            label       = _('Terms and Conditions agreement'),
        )



class CourseRegistrationForm(RegistrationForm):

    class Meta:
        model = CourseRegistration
        exclude = ('subject', 'user', 'cancel_request', 'canceled')



class EventRegistrationForm(RegistrationForm):

    class Meta:
        model = EventRegistration
        exclude = ('subject', 'user', 'cancel_request', 'canceled')



class RegistrationAdminForm(forms.ModelForm):

    def __init__(self, data=None, *args, **kwargs):
        super(RegistrationAdminForm, self).__init__(data, *args, **kwargs)
        self.fields['participant_age_group'].widget.choices.queryset = kwargs['instance'].subject.age_groups

        try:
            age = get_age(get_birth_date(data['participant_birth_num']), kwargs['instance'].created.date())
        except:
            age = get_age(get_birth_date(kwargs['instance'].participant.birth_num), kwargs['instance'].created.date())
        if age < 18:
            self.fields['has_parent1'].required = True
        else:
            self.fields['participant_phone'].required = True
            self.fields['participant_email'].required = True

        try:
            has_parent = ['has_parent1' in data, 'has_parent2' in data]
        except:
            has_parent = [kwargs['instance'].has_parent1, kwargs['instance'].has_parent2]
        for n in range(2):
            if has_parent[n]:
                for field in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                    self.fields['parent{}_{}'.format(n + 1, field)].required = True
