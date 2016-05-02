from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import uuid

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

from ..models import ClubRegistration, EventRegistration
from ..utils import get_age, get_birth_date
from .form import FormMixin
from .parent import ParentForm
from .participant import ParticipantForm
from .questions import QuestionsFormMixin
from .widgets import CheckboxSelectMultipleBootstrap, RadioSelectBootstrap

User = get_user_model()


class ParticipantSelectForm(FormMixin, forms.Form):
    participant = forms.ChoiceField(label=_('Participant'), widget=RadioSelectBootstrap())

    def __init__(self, user, participants, **kwargs):
        super(ParticipantSelectForm, self).__init__(**kwargs)
        self.all_participants = participants
        self.fields['participant'].choices = self.all_participants.items() + [('new', _('new participant'))]
        self.fields['participant'].widget.choices = self.fields['participant'].choices



class RegistrationPartialForm(FormMixin, forms.ModelForm):

    def __init__(self, subject, **kwargs):
        super(RegistrationPartialForm, self).__init__(**kwargs)
        self.fields['age_group'].widget.choices.queryset = subject.age_groups

    class Meta:
        model = EventRegistration
        fields = [
            'age_group', 'citizenship', 'insurance',
            'school', 'school_other', 'school_class', 'health',
        ]



class ParentSelectForm(FormMixin, forms.Form):
    parents = forms.MultipleChoiceField(label=_('Parents'), widget=CheckboxSelectMultipleBootstrap(), required=False)

    def __init__(self, user, **kwargs):
        super(ParentSelectForm, self).__init__(**kwargs)
        try:
            self.all_parents = dict((parent.id, parent) for parent in user.leprikon_parents.all())
        except:
            self.all_parents = {}
        self.fields['parents'].choices = self.all_parents.items() + [('new', _('new parent'))]
        self.fields['parents'].widget.choices = self.fields['parents'].choices



class UserSelectForm(FormMixin, forms.Form):
    create_account = forms.BooleanField(label=_('Create account'), initial=True, required=False,
                    help_text=_('Having user account allows you to view and easily manage your registrations, payments, etc.'))



class UserForm(FormMixin, UserCreationForm):
    pass



class RegistrationForm(FormMixin, QuestionsFormMixin, forms.ModelForm):

    def __init__(self, user, **kwargs):
        self.user       = user
        self.questions  = self.subject.all_questions
        super(RegistrationForm, self).__init__(**kwargs)
        del kwargs['instance']

        try:
            participants = dict((participant.id, participant) for participant in user.leprikon_participants.exclude(
                id__in=[reg.participant_id for reg in self.subject.all_registrations]
            ))
        except:
            participants = {}
        

        kwargs['prefix'] = 'participant_select'
        self.participant_select_form = ParticipantSelectForm(user=user, participants=participants, **kwargs)

        kwargs['prefix'] = 'participant'
        self.participant_form = ParticipantForm(user=user, **kwargs)

        kwargs['prefix'] = 'registration_partial'
        self.registration_partial_form = RegistrationPartialForm(subject=self.subject, **kwargs)

        kwargs['prefix'] = 'parent_select'
        self.parent_select_form = ParentSelectForm(user=user, **kwargs)

        kwargs['prefix'] = 'parent'
        self.parent_form = ParentForm(user=user, **kwargs)

        kwargs['prefix'] = 'user_select'
        self.user_select_form = UserSelectForm(**kwargs)

        kwargs['prefix'] = 'user'
        self.user_form = UserForm(**kwargs)
        self.user_form.fields['username'].help_text = None

    def is_valid(self):
        # validate participant
        if not self.participant_select_form.is_valid():
            return False
        if self.participant_select_form.cleaned_data['participant']=='new':
            self.registration_partial_form.is_bound = False
            if not self.participant_form.is_valid():
                return False
            birth_num = self.participant_form.cleaned_data['birth_num']
        else:
            self.participant_form.is_bound = False
            if not self.registration_partial_form.is_valid():
                return False
            birth_num = self.participant_select_form.all_participants[
                int(self.participant_select_form.cleaned_data['participant'])
            ].birth_num

        # check age
        if get_age(get_birth_date(birth_num)) < 18:
            self.parent_select_form.fields['parents'].required = self.parent_select_form.fields['parents'].widget.required = True

        # validate parents
        if not self.parent_select_form.is_valid():
            self.parent_form.is_bound = False
            return False
        if 'new' in self.parent_select_form.cleaned_data['parents']:
            if not self.parent_form.is_valid():
                return False
        else:
            self.parent_form.is_bound = False

        # validate user
        if self.user.is_anonymous():
            if not self.user_select_form.is_valid():
                self.user_form.is_bound = False
                return False
            if self.user_select_form.cleaned_data['create_account']:
                if not self.user_form.is_valid():
                    return False

        return super(RegistrationForm, self).is_valid()


    def save(self, commit=True):
        if self.user.is_anonymous():
            if self.user_select_form.cleaned_data['create_account']:
                self.user = self.user_form.save()
            else:
                # create inactive user
                self.user = User()
                self.user.is_active = False
                self.user.username = str(uuid.uuid4())[:30]
                while User.objects.filter(username=self.user.username).exists():
                    self.user.username = str(uuid.uuid4())[:30]
                self.user.save()
            new_user = True
        else:
            new_user = False

        if self.participant_select_form.cleaned_data['participant']=='new':
            self.participant_form.user = self.user
            participant = self.participant_form.save()
        else:
            participant = self.participant_select_form.all_participants[
                int(self.participant_select_form.cleaned_data['participant'])
            ]
            # update existing participant
            for attr in ['age_group', 'citizenship', 'insurance',
                         'school', 'school_other', 'school_class', 'health']:
                setattr(participant, attr, self.registration_partial_form.cleaned_data[attr])
            participant.save()

        parents = []
        for parent_id in self.parent_select_form.cleaned_data['parents']:
            if parent_id == 'new':
                self.parent_form.user = self.user
                parents.append(self.parent_form.save())
            else:
                parents.append(self.parent_select_form.all_parents[int(parent_id)])

        if new_user:
            if parents:
                self.user.first_name    = parents[0].first_name
                self.user.last_name     = parents[0].last_name
                self.user.email         = parents[0].email or participant.email
            else:
                self.user.first_name    = participant.first_name
                self.user.last_name     = participant.last_name
                self.user.email         = participant.email
            self.user.save()

        setattr(self.instance, self.subject_attr, self.subject)
        self.instance.participant   = participant
        self.instance.age_group     = participant.age_group
        self.instance.citizenship   = participant.citizenship
        self.instance.insurance     = participant.insurance
        self.instance.school        = participant.school
        self.instance.school_other  = participant.school_other
        self.instance.school_class  = participant.school_class
        self.instance.health        = participant.health
        super(RegistrationForm, self).save(commit=True)
        self.instance.parents       = parents
        return self.instance
    save.alters_data = True



class EventRegistrationForm(RegistrationForm):
    subject_attr    = 'event'
    
    class Meta:
        model = EventRegistration
        fields = ()

    def __init__(self, event, **kwargs):
        self.subject    = event
        super(EventRegistrationForm, self).__init__(**kwargs)



class ClubRegistrationForm(RegistrationForm):
    subject_attr    = 'club'
    
    class Meta:
        model = ClubRegistration
        fields = ()

    def __init__(self, club, **kwargs):
        self.subject    = club
        super(ClubRegistrationForm, self).__init__(**kwargs)

