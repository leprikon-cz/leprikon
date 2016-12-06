from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import uuid

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.urlresolvers import reverse
from django.utils.functional import SimpleLazyObject
from django.utils.translation import ugettext_lazy as _
from json import dumps

from ..models import ClubRegistration, EventRegistration, Participant, Parent
from ..utils import get_age, get_birth_date
from .form import FormMixin
from .widgets import CheckboxSelectMultipleBootstrap, RadioSelectBootstrap



class AgreementForm(FormMixin, forms.Form):
    agreement = forms.BooleanField(label=_('Terms and Conditions agreement'),
        help_text=SimpleLazyObject(lambda:_('By checking the checkbox above I confirm that I have read, understood and agree with the '
            '<a href="{}" target="_blank">Terms and Conditions</a>.').format(reverse('leprikon:terms_conditions'))))



class RegistrationForm(FormMixin, forms.ModelForm):

    def __init__(self, subject, user, **kwargs):
        super(RegistrationForm, self).__init__(**kwargs)
        setattr(self.instance, self.subject_attr, subject)
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
                    self.fields['parent{}_{}'.format(n+1, field)].required = True

        # sub forms

        del kwargs['instance']

        class ParticipantSelectForm(FormMixin, forms.Form):
            participant = forms.ChoiceField(label=_('Choose'),
                choices = [('new', _('new participant'))] + list((p.id, p) for p in self.participants),
                initial = 'new',
                widget = RadioSelectBootstrap()
            )
        kwargs['prefix'] = 'participant_select'
        self.participant_select_form = ParticipantSelectForm(**kwargs)

        class ParentSelectForm(FormMixin, forms.Form):
            parent = forms.ChoiceField(label=_('Choose'),
                choices = [('new', _('new parent'))] + list((p.id, p) for p in self.parents),
                initial = 'new',
                widget = RadioSelectBootstrap()
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
        self.agreement_form = AgreementForm(**kwargs)

    def is_valid(self):
        return (self.participant_select_form.is_valid()
            and self.questions_form.is_valid()
            and self.parent1_select_form.is_valid()
            and self.parent2_select_form.is_valid()
            and self.agreement_form.is_valid()
            and super(RegistrationForm, self).is_valid())

    def save(self, commit=True):
        self.instance.answers = dumps(self.questions_form.cleaned_data)
        super(RegistrationForm, self).save(commit)

        # save / update participant
        if self.participant_select_form.cleaned_data['participant'] == 'new':
            try:
                participant = Participant.objects.get(user=self.instance.user, birth_num=self.instance.participant.birth_num)
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



class ClubRegistrationForm(RegistrationForm):
    subject_attr    = 'club'
    
    class Meta:
        model = ClubRegistration
        exclude = ('club', 'user', 'cancel_request', 'canceled')



class EventRegistrationForm(RegistrationForm):
    subject_attr    = 'event'
    
    class Meta:
        model = EventRegistration
        exclude = ('event', 'user', 'cancel_request', 'canceled', 'discount', 'explanation')



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
                    self.fields['parent{}_{}'.format(n+1, field)].required = True

