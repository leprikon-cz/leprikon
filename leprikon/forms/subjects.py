from datetime import date
from json import dumps

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.forms.models import inlineformset_factory
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from verified_email_field.forms import VerifiedEmailField

from ..models.agegroup import AgeGroup
from ..models.courses import Course, CourseRegistration
from ..models.department import Department
from ..models.events import Event, EventRegistration
from ..models.fields import DAY_OF_WEEK
from ..models.leprikonsite import LeprikonSite
from ..models.place import Place
from ..models.roles import Leader, Parent, Participant
from ..models.school import School
from ..models.subjects import (
    Subject, SubjectGroup, SubjectRegistration, SubjectRegistrationGroup,
    SubjectRegistrationGroupMember, SubjectRegistrationParticipant,
    SubjectType,
)
from ..utils import get_age, get_birth_date
from .fields import AgreementBooleanField
from .form import FormMixin
from .widgets import RadioSelectBootstrap

User = get_user_model()


class SubjectFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_('Search term'), required=False)
    course_types = forms.ModelMultipleChoiceField(queryset=None, label=_('Course type'), required=False)
    event_types = forms.ModelMultipleChoiceField(queryset=None, label=_('Event type'), required=False)
    departments = forms.ModelMultipleChoiceField(queryset=None, label=_('Department'), required=False)
    groups = forms.ModelMultipleChoiceField(queryset=None, label=_('Group'), required=False)
    leaders = forms.ModelMultipleChoiceField(queryset=None, label=_('Leader'), required=False)
    places = forms.ModelMultipleChoiceField(queryset=None, label=_('Place'), required=False)
    age_groups = forms.ModelMultipleChoiceField(queryset=None, label=_('Age group'), required=False)
    days_of_week = forms.MultipleChoiceField(label=_('Day of week'),
                                             choices=tuple(sorted(DAY_OF_WEEK.items())), required=False)
    past = forms.BooleanField(label=_('Include past subjects'), required=False)
    reg_active = forms.BooleanField(label=_('Available for registration'), required=False)
    invisible = forms.BooleanField(label=_('Show invisible'), required=False)

    _models = {
        SubjectType.COURSE: Course,
        SubjectType.EVENT: Event,
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

        subject_ids = tuple(qs.order_by('id').values_list('id', flat=True).distinct())
        if len(subject_types) == 1:
            del self.fields['course_types']
            del self.fields['event_types']
        elif subject_type_type == SubjectType.COURSE:
            del self.fields['event_types']
            self.fields['course_types'].queryset = SubjectType.objects.filter(id__in=(st.id for st in subject_types))
        elif subject_type_type == SubjectType.EVENT:
            del self.fields['course_types']
            self.fields['event_types'].queryset = SubjectType.objects.filter(id__in=(st.id for st in subject_types))

        self.fields['departments'].queryset = Department.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields['departments'].queryset.count() == 0:
            del self.fields['departments']

        self.fields['groups'].queryset = SubjectGroup.objects.filter(subject_types__in=subject_types,
                                                                     subjects__id__in=subject_ids).distinct()
        if self.fields['groups'].queryset.count() == 0:
            del self.fields['groups']

        self.fields['leaders'].queryset = (Leader.objects.filter(subjects__id__in=subject_ids).distinct()
                                           .order_by('user__first_name', 'user__last_name'))
        if self.fields['leaders'].queryset.count() == 0:
            del self.fields['leaders']

        self.fields['places'].queryset = Place.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields['places'].queryset.count() == 0:
            del self.fields['places']

        self.fields['age_groups'].queryset = AgeGroup.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields['age_groups'].queryset.count() <= 1:
            del self.fields['age_groups']

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
                Q(name__icontains=word) |
                Q(description__icontains=word)
            )
        if self.cleaned_data.get('course_types'):
            qs = qs.filter(subject_type__in=self.cleaned_data['course_types'])
        elif self.cleaned_data.get('event_types'):
            qs = qs.filter(subject_type__in=self.cleaned_data['event_types'])
        if self.cleaned_data.get('departments'):
            qs = qs.filter(department__in=self.cleaned_data['departments'])
        if self.cleaned_data.get('groups'):
            qs = qs.filter(groups__in=self.cleaned_data['groups'])
        if self.cleaned_data.get('places'):
            qs = qs.filter(place__in=self.cleaned_data['places'])
        if self.cleaned_data.get('leaders'):
            qs = qs.filter(leaders__in=self.cleaned_data['leaders'])
        if self.cleaned_data.get('age_groups'):
            qs = qs.filter(age_groups__in=self.cleaned_data['age_groups'])
        if self.cleaned_data.get('days_of_week'):
            qs = qs.filter(times__day_of_week__in=self.cleaned_data['days_of_week'])
        if self.subject_type_type == SubjectType.EVENT and not self.cleaned_data['past']:
            qs = qs.filter(end_date__gte=now())
        if self.cleaned_data['reg_active']:
            qs = qs.filter(reg_from__lte=now()).exclude(reg_to__lte=now()).exclude(price=None)
        return qs.distinct()


class SubjectForm(FormMixin, forms.ModelForm):

    class Meta:
        model = Subject
        fields = ['description', 'risks', 'plan', 'evaluation']


class SubjectAdminForm(FormMixin, forms.ModelForm):

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get('instance')
        leprikon_site = LeprikonSite.objects.get_current()

        # limit choices of groups
        groups_choices = self.fields['groups'].widget.choices
        groups_choices.queryset = groups_choices.queryset.filter(
            subject_types__subject_type=self.subject_type
        ).distinct()

        # limit choices of leaders
        leaders_choices = self.fields['leaders'].widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years=self.school_year)

        # limit choices of questions
        if instance:
            questions_choices = self.fields['questions'].widget.choices
            questions_choices.queryset = questions_choices.queryset.exclude(
                id__in=instance.subject_type.questions.values('id')
            )

        # limit choices of registration agreements
        registration_agreements_choices = self.fields['registration_agreements'].widget.choices
        registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
            id__in=leprikon_site.registration_agreements.values('id')
        )
        if instance:
            registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
                id__in=instance.subject_type.registration_agreements.values('id')
            )


class SchoolMixin:
    def _add_error_required(self, field_name):
        self.add_error(field_name, forms.ValidationError(
            self.fields[field_name].error_messages['required'],
            code='required',
        ))

    def clean(self):
        # check required school and class
        x_group = self.cleaned_data.get(self.x_group)
        if x_group and x_group.require_school:
            # require school
            school = self.cleaned_data.get('school')
            if school:
                if school == 'other':
                    self.cleaned_data['school'] = None
                    # require other school
                    if not self.cleaned_data.get('school_other'):
                        self._add_error_required('school_other')
                else:
                    self.cleaned_data['school'] = School.objects.get(
                        id=int(self.cleaned_data['school']),
                    )
            else:
                self._add_error_required('school')
            # require school class
            if not self.cleaned_data.get('school_class'):
                self._add_error_required('school_class')
        else:
            # delete school and class
            self.cleaned_data['school'] = None
            self.cleaned_data['school_other'] = ''
            self.cleaned_data['school_class'] = ''
        return self.cleaned_data


class BirthNumberMixin:
    def clean_birth_num(self):
        qs = SubjectRegistrationParticipant.objects.filter(
            registration__subject_id=self.subject.id,
            registration__canceled=None,
            birth_num=self.cleaned_data['birth_num'],
        )
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('Participant with this birth number has already been registered.'))
        return self.cleaned_data['birth_num']


class RegistrationParticipantForm(FormMixin, BirthNumberMixin, SchoolMixin, forms.ModelForm):
    x_group = 'age_group'

    school = forms.ChoiceField(
        label=_('School'),
        choices=lambda: (
            [('', '---------')] + [
                (school.id, school) for school in School.objects.all()
            ] + [('other', _('other school'))]
        ),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # choices for age group
        self.fields['age_group'].widget.choices.queryset = self.subject.age_groups
        if self.subject.age_groups.count() == 1:
            self.fields['age_group'].initial = self.subject.age_groups.first()

        # initial school
        if School.objects.count() == 0:
            self.fields['school'].initial = 'other'

        # prepare data
        prefix = self.prefix + '-'
        data = {
            key[len(prefix):]: value
            for key, value in kwargs.get('data', {}).items()
            if key.startswith(prefix)
        }

        # dynamically required fields
        try:
            age = get_age(get_birth_date(data['birth_num']))
        except Exception:
            age = None

        if age is not None and age < 18:
            self.fields['has_parent1'].required = True
        else:
            self.fields['phone'].required = True
            self.fields['email'].required = True

        has_parent = ['has_parent1' in data, 'has_parent2' in data]
        for n in range(2):
            if has_parent[n]:
                for field in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                    self.fields['parent{}_{}'.format(n + 1, field)].required = True

        class ParticipantSelectForm(FormMixin, forms.Form):
            participant = forms.ChoiceField(
                label=_('Choose'),
                choices=[('new', _('new participant'))] + list((p.id, p) for p in self.user_participants),
                initial='new',
                widget=RadioSelectBootstrap(),
            )

        kwargs['prefix'] = self.prefix + '-participant_select'
        self.participant_select_form = ParticipantSelectForm(**kwargs)

        class ParentSelectForm(FormMixin, forms.Form):
            parent = forms.ChoiceField(
                label=_('Choose'),
                choices=[('new', _('new parent'))] + list((p.id, p) for p in self.user_parents),
                initial='new',
                widget=RadioSelectBootstrap(),
            )

        kwargs['prefix'] = self.prefix + '-parent1_select'
        self.parent1_select_form = ParentSelectForm(**kwargs)
        kwargs['prefix'] = self.prefix + '-parent2_select'
        self.parent2_select_form = ParentSelectForm(**kwargs)

        kwargs['prefix'] = self.prefix + '-questions'
        self.questions_form = type(str('QuestionsForm'), (FormMixin, forms.Form), dict(
            (q.name, q.get_field()) for q in self.subject.all_questions
        ))(**kwargs)

    @cached_property
    def required_forms(self):
        return [
            super(RegistrationParticipantForm, self),
            self.participant_select_form,
            self.questions_form,
            self.parent1_select_form,
            self.parent2_select_form,
        ]

    def is_valid(self):
        # validate all required forms
        results = [form.is_valid() for form in self.required_forms]
        return all(results)

    @cached_property
    def errors(self):
        return {
            (form.prefix + '-' + field_name if form.prefix else field_name): error
            for form in self.required_forms
            for field_name, error in form.errors.items()
        }

    def save(self, commit=True):
        with transaction.atomic():
            return self._save(commit)

    def _save(self, commit):
        # set answers
        self.instance.answers = dumps(self.questions_form.cleaned_data)

        # create
        super().save(commit)

        # save / update participant
        if self.participant_select_form.cleaned_data['participant'] == 'new':
            try:
                participant = Participant.objects.get(
                    user=self.instance.registration.user,
                    birth_num=self.instance.birth_num,
                )
            except Participant.DoesNotExist:
                participant = Participant()
                participant.user = self.instance.registration.user
        else:
            participant = Participant.objects.get(id=self.participant_select_form.cleaned_data['participant'])
        for attr in ['first_name', 'last_name', 'birth_num', 'age_group', 'street', 'city', 'postal_code',
                     'citizenship', 'phone', 'email', 'school', 'school_other', 'school_class', 'health']:
            setattr(participant, attr, getattr(self.instance, attr))
        participant.save()

        # save / update first parent
        if self.instance.parent1:
            if self.parent1_select_form.cleaned_data['parent'] == 'new':
                parent = Parent()
                parent.user = self.instance.registration.user
            else:
                parent = Parent.objects.get(id=self.parent1_select_form.cleaned_data['parent'])
            for attr in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                setattr(parent, attr, getattr(self.instance.parent1, attr))
            parent.save()

        # save / update second parent
        if self.instance.parent2:
            if self.parent2_select_form.cleaned_data['parent'] == 'new':
                parent = Parent()
                parent.user = self.instance.registration.user
            else:
                parent = Parent.objects.get(id=self.parent2_select_form.cleaned_data['parent'])
            for attr in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                setattr(parent, attr, getattr(self.instance.parent2, attr))
            parent.save()
        return self.instance


class RegistrationGroupForm(FormMixin, SchoolMixin, forms.ModelForm):
    x_group = 'target_group'

    school = forms.ChoiceField(
        label=_('School'),
        choices=lambda: (
            [('', '---------')] + [
                (school.id, school) for school in School.objects.all()
            ] + [('other', _('other school'))]
        ),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # choices for age group
        self.fields['target_group'].widget.choices.queryset = self.subject.target_groups
        if self.subject.target_groups.count() == 1:
            self.fields['target_group'].initial = self.subject.target_groups.first()

        # initial school
        self.fields['school'].initial = 'other' if School.objects.count() == 0 else None

        kwargs['prefix'] = self.prefix + '-questions'
        self.questions_form = type(str('QuestionsForm'), (FormMixin, forms.Form), dict(
            (q.name, q.get_field()) for q in self.subject.all_questions
        ))(**kwargs)

    @cached_property
    def required_forms(self):
        return [
            super(RegistrationGroupForm, self),
            self.questions_form,
        ]

    def is_valid(self):
        # validate all required forms
        results = [form.is_valid() for form in self.required_forms]
        return all(results)

    @cached_property
    def errors(self):
        return {
            (form.prefix + '-' + field_name if form.prefix else field_name): error
            for form in self.required_forms
            for field_name, error in form.errors.items()
        }

    def save(self, commit=True):
        # set answers
        self.instance.answers = dumps(self.questions_form.cleaned_data)

        # create
        return super().save(commit)


class RegistrationGroupMemberForm(FormMixin, forms.ModelForm):
    pass


class RegistrationForm(FormMixin, forms.ModelForm):
    def __init__(self, subject, user, **kwargs):
        super(RegistrationForm, self).__init__(**kwargs)
        self.user = user
        self.instance.subject = subject

        # choices for subject_variant
        if self.instance.subject.all_variants:
            self.fields['subject_variant'].widget.choices.queryset = self.instance.subject.variants
        else:
            del self.fields['subject_variant']

        # sub forms
        if subject.registration_type_participants:
            registered_birth_nums = list(SubjectRegistrationParticipant.objects.filter(
                registration_id__in=self.instance.subject.active_registrations.values('id')
            ).values_list('birth_num', flat=True))

            participant_form = type(
                RegistrationParticipantForm.__name__,
                (RegistrationParticipantForm, ),
                {
                    'subject': subject,
                    'user_participants': user.leprikon_participants.exclude(
                        birth_num__in=registered_birth_nums,
                    ) if user.is_authenticated() else [],
                    'user_parents': user.leprikon_parents.all() if user.is_authenticated() else []
                }
            )

            self.participants_formset = inlineformset_factory(
                SubjectRegistration,
                SubjectRegistrationParticipant,
                form=participant_form,
                fk_name='registration',
                exclude=[],
                extra=subject.max_participants_count,
                min_num=subject.min_participants_count,
                max_num=subject.max_participants_count,
                validate_min=True,
                validate_max=True,
            )(kwargs.get('data'), instance=self.instance)

        elif subject.registration_type_groups:
            group_form = type(
                RegistrationGroupForm.__name__,
                (RegistrationGroupForm, ),
                {'subject': subject}
            )

            self.group_formset = inlineformset_factory(
                SubjectRegistration,
                SubjectRegistrationGroup,
                form=group_form,
                fk_name='registration',
                exclude=[],
                extra=1,
                min_num=1,
                max_num=1,
                validate_min=True,
                validate_max=True,
            )(kwargs.get('data'), instance=self.instance)

            self.group_members_formset = inlineformset_factory(
                SubjectRegistration,
                SubjectRegistrationGroupMember,
                form=RegistrationGroupMemberForm,
                fk_name='registration',
                exclude=[],
                extra=subject.max_group_members_count,
                min_num=subject.min_group_members_count,
                max_num=subject.max_group_members_count,
                validate_min=True,
                validate_max=True,
            )(kwargs.get('data'), instance=self.instance)

        del kwargs['instance']

        if not user.is_authenticated():
            kwargs['prefix'] = 'email'
            self.email_form = self.EmailForm(**kwargs)

        self.agreement_forms = []
        for agreement in self.instance.subject.all_registration_agreements:
            kwargs['prefix'] = 'agreement_%s' % agreement.id
            form_attributes = {
                'agreement': agreement,
                'options': {},
            }
            for option in agreement.all_options:
                option_id = 'option_%s' % option.id
                form_attributes[option_id] = AgreementBooleanField(
                    label=option.option,
                    allow_disagree=not option.required,
                )
                form_attributes['options'][option_id] = option
            AgreementForm = type(str('AgreementForm'), (FormMixin, forms.Form), form_attributes)
            self.agreement_forms.append(AgreementForm(**kwargs))

    @cached_property
    def required_forms(self):
        required_forms = [
            super(RegistrationForm, self),
        ] + self.agreement_forms
        if not self.user.is_authenticated:
            required_forms.append(self.email_form)
        return required_forms

    @cached_property
    def all_forms(self):
        all_forms = self.required_forms
        if self.instance.subject.registration_type_participants:
            all_forms += self.participants_formset.forms
        elif self.instance.subject.registration_type_groups:
            all_forms += self.group_formset.forms + self.group_members_formset.forms
        return all_forms

    def is_valid(self):
        # validate all required forms
        results = [form.is_valid() for form in self.required_forms]
        if self.instance.subject.registration_type_participants:
            results.append(self.participants_formset.is_valid())
        elif self.instance.subject.registration_type_groups:
            results += [
                self.group_formset.is_valid(),
                self.group_members_formset.is_valid(),
            ]
        return all(results)

    @cached_property
    def errors(self):
        return {
            (form.prefix + field_name if form.prefix else field_name): error
            for form in self.all_forms
            for field_name, error in form.errors.items()
        }

    def save(self, commit=True):
        with transaction.atomic():
            return self._save(commit)

    def _save(self, commit):
        # set user
        if self.user.is_authenticated():
            self.instance.user = self.user
        else:
            email = self.email_form.cleaned_data['email'].lower()
            user = User.objects.filter(email=email).first()
            if not user:
                username_base = email.split('@')[0]
                username_max_length = User._meta.get_field('username').max_length
                user = User(
                    username=username_base[:username_max_length],
                    email=email,
                )
                user.set_password(get_random_string())
                while not user.pk:
                    try:
                        with transaction.atomic():
                            user.save()
                    except IntegrityError:
                        user.username = '.'.join((
                            username_base[:(username_max_length - 4)],
                            get_random_string(3),
                        ))
            self.instance.user = user

        # set price
        self.instance.price = (
            self.instance.subject_variant.price
            if self.instance.subject_variant
            else self.instance.subject.price
        )

        # create
        super().save(commit)

        if self.instance.subject.registration_type_participants:
            # save participants
            self.participants_formset.user = self.instance.user
            self.participants_formset.save()

        elif self.instance.subject.registration_type_groups:
            # save group
            self.group_formset.save()

            # save group members
            self.group_members_formset.save()

        # save additional questions
        self.instance.questions.set(self.instance.subject.all_questions)

        # save legal agreements
        self.instance.agreements.set(self.instance.subject.all_registration_agreements)

        # save agreement options
        for agreement_form in self.agreement_forms:
            for option_id, checked in agreement_form.cleaned_data.items():
                if checked:
                    self.instance.agreement_options.add(agreement_form.options[option_id])

        # send mail
        self.instance.send_mail()
        return self.instance

    class EmailForm(FormMixin, forms.Form):
        email = VerifiedEmailField(label=_('Your email'), fieldsetup_id='RegistrationEmailForm')


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
        super().__init__(data, *args, **kwargs)

        if 'subject_variant' in self.fields:
            self.fields['subject_variant'].widget.choices.queryset = self.subject.variants

        # choices for agreement options
        instance = kwargs.get('instance')
        self.fields['agreement_options'].widget.choices = tuple(
            (agreement.name, tuple((option.id, option.name) for option in agreement.all_options))
            for agreement in (instance.all_agreements if instance else self.subject.all_registration_agreements)
        )


class SchoolAdminMixin:
    def _add_error_required(self, field_name):
        self.add_error(field_name, forms.ValidationError(
            self.fields[field_name].error_messages['required'],
            code='required',
        ))

    def clean(self):
        # check required school and class
        x_group = self.cleaned_data.get(self.x_group)
        if x_group and x_group.require_school:
            # require school
            if self.cleaned_data.get('school'):
                self.cleaned_data['school_other'] = ''
            elif not self.cleaned_data.get('school_other'):
                self._add_error_required('school_other')
            # require school class
            if not self.cleaned_data.get('school_class'):
                self._add_error_required('school_class')
        else:
            # delete school and class
            self.cleaned_data['school'] = None
            self.cleaned_data['school_other'] = ''
            self.cleaned_data['school_class'] = ''
        return self.cleaned_data


class RegistrationParticipantAdminForm(BirthNumberMixin, SchoolAdminMixin, forms.ModelForm):
    x_group = 'age_group'

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get('instance')

        self.fields['age_group'].widget.choices.queryset = self.subject.age_groups
        if self.subject.age_groups.count() == 1:
            self.fields['age_group'].initial = self.subject.age_groups.first()

        questions = self.obj.all_questions if self.obj else self.subject.all_questions
        answers = instance.get_answers() if instance else {}
        for q in questions:
            self.fields['q_' + q.name].initial = answers.get(q.name)

        created_date = self.obj.created.date() if self.obj else date.today()
        try:
            age = get_age(get_birth_date(data['birth_num']), created_date)
        except Exception:
            age = get_age(get_birth_date(instance.birth_num), created_date) if instance else None
        if age is not None:
            if age < 18:
                self.fields['has_parent1'].required = True
            else:
                self.fields['phone'].required = True
                self.fields['email'].required = True

        try:
            has_parent = ['has_parent1' in data, 'has_parent2' in data]
        except TypeError:
            has_parent = [instance.has_parent1, instance.has_parent2] if instance else [False, False]
        for n in range(2):
            if has_parent[n]:
                for field in ['first_name', 'last_name', 'street', 'city', 'postal_code', 'phone', 'email']:
                    self.fields['parent{}_{}'.format(n + 1, field)].required = True

    def save(self, commit=True):
        self.instance.answers = dumps({
            q.name: self.cleaned_data['q_' + q.name]
            for q in (self.obj.all_questions if self.obj else self.subject.all_questions)
        })
        return super().save(commit)


class RegistrationGroupAdminForm(SchoolAdminMixin, forms.ModelForm):
    x_group = 'target_group'

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get('instance')

        self.fields['target_group'].widget.choices.queryset = self.subject.target_groups

        questions = self.obj.all_questions if self.obj else self.subject.all_questions
        answers = instance.get_answers() if instance else {}
        for q in questions:
            self.fields['q_' + q.name].initial = answers.get(q.name)

    def save(self, commit=True):
        self.instance.answers = dumps({
            q.name: self.cleaned_data['q_' + q.name]
            for q in (self.obj.all_questions if self.obj else self.subject.all_questions)
        })
        return super().save(commit)
