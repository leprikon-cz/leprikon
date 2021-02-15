from datetime import date
from json import dumps

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from sentry_sdk import capture_message

from ..models.agegroup import AgeGroup
from ..models.citizenship import Citizenship
from ..models.courses import Course, CourseRegistration, CourseRegistrationPeriod
from ..models.department import Department
from ..models.events import Event, EventRegistration
from ..models.fields import DAY_OF_WEEK
from ..models.leprikonsite import LeprikonSite
from ..models.orderables import Orderable, OrderableRegistration
from ..models.place import Place
from ..models.roles import BillingInfo, Leader, Parent, Participant
from ..models.school import School
from ..models.schoolyear import SchoolYearPeriod
from ..models.subjects import (
    Subject,
    SubjectGroup,
    SubjectRegistration,
    SubjectRegistrationBillingInfo,
    SubjectRegistrationGroup,
    SubjectRegistrationGroupMember,
    SubjectRegistrationParticipant,
    SubjectType,
)
from ..models.targetgroup import TargetGroup
from ..utils import get_age, get_birth_date, get_gender
from .fields import AgreementBooleanField
from .form import FormMixin
from .widgets import CheckboxSelectMultipleBootstrap, RadioSelectBootstrap

User = get_user_model()


class SubjectFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_("Search term"), required=False)
    course_types = forms.ModelMultipleChoiceField(queryset=None, label=_("Course type"), required=False)
    event_types = forms.ModelMultipleChoiceField(queryset=None, label=_("Event type"), required=False)
    orderable_types = forms.ModelMultipleChoiceField(queryset=None, label=_("Orderable event type"), required=False)
    departments = forms.ModelMultipleChoiceField(queryset=None, label=_("Department"), required=False)
    groups = forms.ModelMultipleChoiceField(queryset=None, label=_("Group"), required=False)
    leaders = forms.ModelMultipleChoiceField(queryset=None, label=_("Leader"), required=False)
    places = forms.ModelMultipleChoiceField(queryset=None, label=_("Place"), required=False)
    age_groups = forms.ModelMultipleChoiceField(queryset=None, label=_("Age group"), required=False)
    target_groups = forms.ModelMultipleChoiceField(queryset=None, label=_("Target group"), required=False)
    days_of_week = forms.MultipleChoiceField(
        label=_("Day of week"), choices=tuple(sorted(DAY_OF_WEEK.items())), required=False
    )
    past = forms.BooleanField(label=_("Include past subjects"), required=False)
    reg_active = forms.BooleanField(label=_("Available for registration"), required=False)
    invisible = forms.BooleanField(label=_("Show invisible"), required=False)

    _models = {
        SubjectType.COURSE: Course,
        SubjectType.EVENT: Event,
        SubjectType.ORDERABLE: Orderable,
    }

    def __init__(self, subject_type_type, subject_types, school_year, is_staff, data, **kwargs):
        super().__init__(data=data, **kwargs)
        self.subject_type_type = subject_type_type

        # pre filter subjects by initial params
        qs = self._models[subject_type_type].objects.filter(school_year=school_year)
        if len(subject_types) == 1:
            qs = qs.filter(subject_type=subject_types[0])
        else:
            qs = qs.filter(subject_type__in=subject_types)
        if not is_staff or "invisible" not in data:
            qs = qs.filter(public=True)
        self.qs = qs

        subject_ids = tuple(qs.order_by("id").values_list("id", flat=True).distinct())
        if len(subject_types) == 1:
            del self.fields["course_types"]
            del self.fields["event_types"]
            del self.fields["orderable_types"]
        elif subject_type_type == SubjectType.COURSE:
            del self.fields["event_types"]
            del self.fields["orderable_types"]
            self.fields["course_types"].queryset = SubjectType.objects.filter(id__in=(st.id for st in subject_types))
        elif subject_type_type == SubjectType.EVENT:
            del self.fields["course_types"]
            del self.fields["orderable_types"]
            self.fields["event_types"].queryset = SubjectType.objects.filter(id__in=(st.id for st in subject_types))
        elif subject_type_type == SubjectType.ORDERABLE:
            del self.fields["course_types"]
            del self.fields["event_types"]
            self.fields["orderable_types"].queryset = SubjectType.objects.filter(id__in=(st.id for st in subject_types))

        self.fields["departments"].queryset = Department.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields["departments"].queryset.count() == 0:
            del self.fields["departments"]

        self.fields["groups"].queryset = SubjectGroup.objects.filter(
            subject_types__in=subject_types, subjects__id__in=subject_ids
        ).distinct()
        if self.fields["groups"].queryset.count() == 0:
            del self.fields["groups"]

        self.fields["leaders"].queryset = (
            Leader.objects.filter(subjects__id__in=subject_ids)
            .distinct()
            .order_by("user__first_name", "user__last_name")
        )
        if self.fields["leaders"].queryset.count() == 0:
            del self.fields["leaders"]

        self.fields["places"].queryset = Place.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields["places"].queryset.count() == 0:
            del self.fields["places"]

        self.fields["age_groups"].queryset = AgeGroup.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields["age_groups"].queryset.count() <= 1:
            del self.fields["age_groups"]

        self.fields["target_groups"].queryset = TargetGroup.objects.filter(subjects__id__in=subject_ids).distinct()
        if self.fields["target_groups"].queryset.count() <= 1:
            del self.fields["target_groups"]

        if subject_type_type != SubjectType.COURSE:
            del self.fields["days_of_week"]
        if subject_type_type != SubjectType.EVENT:
            del self.fields["past"]
        if not is_staff:
            del self.fields["invisible"]

        for f in self.fields:
            self.fields[f].help_text = None

    def get_queryset(self):
        if not self.is_valid():
            return self.qs
        qs = self.qs
        for word in self.cleaned_data["q"].split():
            qs = qs.filter(Q(name__icontains=word) | Q(description__icontains=word))
        if self.cleaned_data.get("course_types"):
            qs = qs.filter(subject_type__in=self.cleaned_data["course_types"])
        elif self.cleaned_data.get("event_types"):
            qs = qs.filter(subject_type__in=self.cleaned_data["event_types"])
        elif self.cleaned_data.get("orderable_types"):
            qs = qs.filter(subject_type__in=self.cleaned_data["orderable_types"])
        if self.cleaned_data.get("departments"):
            qs = qs.filter(department__in=self.cleaned_data["departments"])
        if self.cleaned_data.get("groups"):
            qs = qs.filter(groups__in=self.cleaned_data["groups"])
        if self.cleaned_data.get("places"):
            qs = qs.filter(place__in=self.cleaned_data["places"])
        if self.cleaned_data.get("leaders"):
            qs = qs.filter(leaders__in=self.cleaned_data["leaders"])
        if self.cleaned_data.get("age_groups"):
            qs = qs.filter(age_groups__in=self.cleaned_data["age_groups"])
        if self.cleaned_data.get("target_groups"):
            qs = qs.filter(target_groups__in=self.cleaned_data["target_groups"])
        if self.cleaned_data.get("days_of_week"):
            qs = qs.filter(times__day_of_week__in=self.cleaned_data["days_of_week"])
        if self.subject_type_type == SubjectType.EVENT and not self.cleaned_data["past"]:
            qs = qs.filter(end_date__gte=now())
        if self.cleaned_data["reg_active"]:
            qs = qs.filter(reg_from__lte=now()).exclude(reg_to__lte=now()).exclude(price=None)
        return qs.distinct()


class SubjectForm(FormMixin, forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["description", "risks", "plan", "evaluation"]


class SubjectAdminForm(forms.ModelForm):
    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get("instance")
        leprikon_site = LeprikonSite.objects.get_current()

        # limit choices of groups
        self.fields["groups"].widget.choices.queryset = self.subject_type.groups.all()

        # limit choices of leaders
        leaders_choices = self.fields["leaders"].widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years=self.school_year)

        # limit choices of questions
        if instance:
            questions_choices = self.fields["questions"].widget.choices
            questions_choices.queryset = questions_choices.queryset.exclude(
                id__in=instance.subject_type.questions.values("id")
            )

        # limit choices of registration agreements
        registration_agreements_choices = self.fields["registration_agreements"].widget.choices
        registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
            id__in=leprikon_site.registration_agreements.values("id")
        )
        if instance:
            registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
                id__in=instance.subject_type.registration_agreements.values("id")
            )


class SchoolMixin:
    def _add_error_required(self, field_name):
        self.add_error(
            field_name,
            ValidationError(
                self.fields[field_name].error_messages["required"],
                code="required",
            ),
        )

    def clean(self):
        # check required school and class
        x_group = self.cleaned_data.get(self.x_group)
        if x_group and x_group.require_school:
            # require school
            school = self.cleaned_data.get("school")
            if school:
                if school == "other":
                    self.cleaned_data["school"] = None
                    # require other school
                    if not self.cleaned_data.get("school_other"):
                        self._add_error_required("school_other")
                else:
                    self.cleaned_data["school"] = School.objects.get(
                        id=int(self.cleaned_data["school"]),
                    )
            else:
                self._add_error_required("school")
            # require school class
            if not self.cleaned_data.get("school_class"):
                self._add_error_required("school_class")
        else:
            # delete school and class
            self.cleaned_data["school"] = None
            self.cleaned_data["school_other"] = ""
            self.cleaned_data["school_class"] = ""
        return self.cleaned_data


class RegistrationParticipantFormMixin:
    def clean_birth_num(self):
        if self.cleaned_data["birth_num"]:
            qs = SubjectRegistrationParticipant.objects.filter(
                registration__subject_id=self.subject.id,
                registration__canceled=None,
                birth_num=self.cleaned_data["birth_num"],
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_("Participant with this birth number has already been registered."))
        return self.cleaned_data["birth_num"]

    def _setup_required_fields(self):
        self.all_citizenships = list(Citizenship.objects.all())

        # set default values
        created_date = date.today()
        age = None
        citizenship = self.all_citizenships[0]

        # try to use values from existing object (update)
        try:
            created_date = self.obj.created.date()
            age = get_age(self.instance.birth_date, created_date)
            citizenship = self.instance.citizenship
        except AttributeError:
            pass

        prefix = self.prefix + "-"
        data = {key[len(prefix) :]: value for key, value in self.data.items() if key.startswith(prefix)}

        if data:
            # try to use citizenship from request data (post)
            try:
                citizenship = self.fields["citizenship"].clean(data.get("citizenship"))
            except ValidationError:
                pass

        # set required field based on citizenship
        if citizenship.require_birth_num:
            self.hide_birth_num = False
            self.fields["birth_num"].required = True
            self.fields["birth_date"].required = False
            self.fields["gender"].required = False
        else:
            self.hide_birth_num = True
            self.fields["birth_num"].required = False
            self.fields["birth_date"].required = True
            self.fields["gender"].required = True

        if data:
            # try to use age from request data (post)
            try:
                if citizenship.require_birth_num:
                    age = get_age(
                        get_birth_date(self.fields["birth_num"].clean(data.get("birth_num"))),
                        created_date,
                    )
                else:
                    age = get_age(self.fields["birth_date"].clean(data.get("birth_date")), created_date)
            except ValidationError:
                pass

        # set required field based on age
        if age is not None and age < 18:
            self.hide_parents = False
            self.fields["has_parent1"].required = True
        else:
            self.hide_parents = True
            self.fields["phone"].required = True
            self.fields["email"].required = True

        # set required field based on has_parentX
        if data:
            has_parent = ["has_parent1" in data, "has_parent2" in data]
        else:
            has_parent = [self.instance.has_parent1, self.instance.has_parent2] if self.instance else [False, False]
        for n in range(2):
            if has_parent[n]:
                for field in ["first_name", "last_name", "street", "city", "postal_code", "phone", "email"]:
                    self.fields["parent{}_{}".format(n + 1, field)].required = True

    def _set_birth_date_gender(self):
        if self.instance.citizenship.require_birth_num:
            self.instance.birth_date = get_birth_date(self.instance.birth_num)
            self.instance.gender = get_gender(self.instance.birth_num)
        else:
            self.instance.birth_num = None


class RegistrationParticipantForm(FormMixin, RegistrationParticipantFormMixin, SchoolMixin, forms.ModelForm):
    x_group = "age_group"

    school = forms.ChoiceField(
        label=_("School"),
        choices=lambda: (
            [("", "---------")]
            + [(school.id, school) for school in School.objects.all()]
            + [("other", _("other school"))]
        ),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # choices for age group
        self.fields["age_group"].widget.choices.queryset = self.subject.age_groups
        if self.subject.age_groups.count() == 1:
            self.fields["age_group"].initial = self.subject.age_groups.first()

        # initial school
        if School.objects.count() == 0:
            self.fields["school"].initial = "other"

        self._setup_required_fields()

        class ParticipantSelectForm(FormMixin, forms.Form):
            participant = forms.ChoiceField(
                label=_("Choose"),
                choices=[("new", _("new participant"))] + list((p.id, p) for p in self.user_participants),
                initial="new",
                widget=RadioSelectBootstrap(),
            )

        kwargs["prefix"] = self.prefix + "-participant_select"
        self.participant_select_form = ParticipantSelectForm(**kwargs)

        class ParentSelectForm(FormMixin, forms.Form):
            parent = forms.ChoiceField(
                label=_("Choose"),
                choices=[("new", _("new parent"))] + list((p.id, p) for p in self.user_parents),
                initial="new",
                widget=RadioSelectBootstrap(),
            )

        kwargs["prefix"] = self.prefix + "-parent1_select"
        self.parent1_select_form = ParentSelectForm(**kwargs)
        kwargs["prefix"] = self.prefix + "-parent2_select"
        self.parent2_select_form = ParentSelectForm(**kwargs)

        kwargs["prefix"] = self.prefix + "-questions"
        self.questions_form = type(
            str("QuestionsForm"),
            (FormMixin, forms.Form),
            dict((q.name, q.get_field()) for q in self.subject.all_questions),
        )(**kwargs)

    @cached_property
    def required_forms(self):
        return [
            super(),
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
            (form.prefix + "-" + field_name if form.prefix else field_name): error
            for form in self.required_forms
            for field_name, error in form.errors.items()
        }

    def save(self, commit=True):
        with transaction.atomic():
            return self._save(commit)

    def _save(self, commit):
        # set answers
        self.instance.answers = dumps(self.questions_form.cleaned_data)

        # set birth date and gender
        self._set_birth_date_gender()

        # create
        super().save(commit)

        # save / update participant
        if "participant" not in self.participant_select_form.cleaned_data:
            capture_message(
                "Invalid participant_select_form",
                "warning",
                extras={
                    "participant_select_form_data": self.participant_select_form.data,
                    "participant_select_form_is_valid": self.participant_select_form.is_valid(),
                    "participant_select_form_cleaned_data": self.participant_select_form.cleaned_data,
                },
            )
            self.participant_select_form.cleaned_data["participant"] = "new"
        if self.participant_select_form.cleaned_data["participant"] == "new":
            participant = Participant()
            participant.user = self.instance.registration.user
        else:
            participant = Participant.objects.get(id=self.participant_select_form.cleaned_data["participant"])
        for attr in [
            "first_name",
            "last_name",
            "birth_num",
            "birth_date",
            "gender",
            "age_group",
            "street",
            "city",
            "postal_code",
            "citizenship",
            "phone",
            "email",
            "school",
            "school_other",
            "school_class",
            "health",
        ]:
            setattr(participant, attr, getattr(self.instance, attr))
        participant.save()

        # save / update first parent
        if self.instance.parent1:
            if self.parent1_select_form.cleaned_data["parent"] == "new":
                parent = Parent()
                parent.user = self.instance.registration.user
            else:
                parent = Parent.objects.get(id=self.parent1_select_form.cleaned_data["parent"])
            for attr in ["first_name", "last_name", "street", "city", "postal_code", "phone", "email"]:
                setattr(parent, attr, getattr(self.instance.parent1, attr))
            parent.save()

        # save / update second parent
        if self.instance.parent2:
            if self.parent2_select_form.cleaned_data["parent"] == "new":
                parent = Parent()
                parent.user = self.instance.registration.user
            else:
                parent = Parent.objects.get(id=self.parent2_select_form.cleaned_data["parent"])
            for attr in ["first_name", "last_name", "street", "city", "postal_code", "phone", "email"]:
                setattr(parent, attr, getattr(self.instance.parent2, attr))
            parent.save()
        return self.instance


class RegistrationGroupForm(FormMixin, SchoolMixin, forms.ModelForm):
    x_group = "target_group"

    school = forms.ChoiceField(
        label=_("School"),
        choices=lambda: (
            [("", "---------")]
            + [(school.id, school) for school in School.objects.all()]
            + [("other", _("other school"))]
        ),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # choices for target group
        self.fields["target_group"].widget.choices.queryset = self.subject.target_groups
        if self.subject.target_groups.count() == 1:
            self.fields["target_group"].initial = self.subject.target_groups.first()

        # initial school
        self.fields["school"].initial = "other" if School.objects.count() == 0 else None

        kwargs["prefix"] = self.prefix + "-questions"
        self.questions_form = type(
            str("QuestionsForm"),
            (FormMixin, forms.Form),
            dict((q.name, q.get_field()) for q in self.subject.all_questions),
        )(**kwargs)

    @cached_property
    def required_forms(self):
        return [
            super(),
            self.questions_form,
        ]

    def is_valid(self):
        # validate all required forms
        results = [form.is_valid() for form in self.required_forms]
        return all(results)

    @cached_property
    def errors(self):
        return {
            (form.prefix + "-" + field_name if form.prefix else field_name): error
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


class RegistrationBillingInfoForm(FormMixin, forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = SubjectRegistrationBillingInfo
        exclude = ["registration"]


class RegistrationForm(FormMixin, forms.ModelForm):
    def __init__(self, subject, user, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        self.instance.subject = subject

        # choices for subject_variant
        if self.instance.subject.all_variants:
            self.fields["subject_variant"].widget.choices.queryset = self.instance.subject.variants
        else:
            del self.fields["subject_variant"]

        # sub forms
        if subject.registration_type_participants:
            registered_birth_nums = list(
                SubjectRegistrationParticipant.objects.filter(
                    registration_id__in=self.instance.subject.active_registrations.values("id"),
                    birth_num__isnull=False,
                ).values_list("birth_num", flat=True)
            )

            participant_form = type(
                RegistrationParticipantForm.__name__,
                (RegistrationParticipantForm,),
                {
                    "subject": subject,
                    "user_participants": user.leprikon_participants.exclude(
                        birth_num__in=registered_birth_nums,
                    ),
                    "user_parents": list(user.leprikon_parents.all()),
                },
            )

            self.participants_formset = inlineformset_factory(
                SubjectRegistration,
                SubjectRegistrationParticipant,
                form=participant_form,
                fk_name="registration",
                exclude=[],
                extra=subject.max_participants_count,
                min_num=subject.min_participants_count,
                max_num=subject.max_participants_count,
                validate_min=True,
                validate_max=True,
            )(kwargs.get("data"), instance=self.instance)

        elif subject.registration_type_groups:
            group_form = type(RegistrationGroupForm.__name__, (RegistrationGroupForm,), {"subject": subject})

            self.group_formset = inlineformset_factory(
                SubjectRegistration,
                SubjectRegistrationGroup,
                form=group_form,
                fk_name="registration",
                exclude=[],
                extra=1,
                min_num=1,
                max_num=1,
                validate_min=True,
                validate_max=True,
            )(kwargs.get("data"), instance=self.instance)

            self.group_members_formset = inlineformset_factory(
                SubjectRegistration,
                SubjectRegistrationGroupMember,
                form=RegistrationGroupMemberForm,
                fk_name="registration",
                exclude=[],
                extra=subject.max_group_members_count,
                min_num=subject.min_group_members_count,
                max_num=subject.max_group_members_count,
                validate_min=True,
                validate_max=True,
            )(kwargs.get("data"), instance=self.instance)

        del kwargs["instance"]

        self.agreement_forms = []
        for agreement in self.instance.subject.all_registration_agreements:
            kwargs["prefix"] = "agreement_%s" % agreement.id
            form_attributes = {
                "agreement": agreement,
                "options": {},
            }
            for option in agreement.all_options:
                option_id = "option_%s" % option.id
                form_attributes[option_id] = AgreementBooleanField(
                    label=option.option,
                    allow_disagree=not option.required,
                )
                form_attributes["options"][option_id] = option
            AgreementForm = type(str("AgreementForm"), (FormMixin, forms.Form), form_attributes)
            self.agreement_forms.append(AgreementForm(**kwargs))

        self.user_billing_info = list(self.user.leprikon_billing_info.all())

        class BillingInfoSelectForm(FormMixin, forms.Form):
            billing_info = forms.ChoiceField(
                label=_("Choose"),
                choices=[
                    ("none", _("no billing information")),
                ]
                + list((bi.id, bi) for bi in self.user_billing_info)
                + [
                    ("new", _("new billing information")),
                ],
                initial="none",
                widget=RadioSelectBootstrap(),
            )

        kwargs["prefix"] = "billing_info_select"
        self.billing_info_select_form = BillingInfoSelectForm(**kwargs)

        kwargs["prefix"] = "billing_info"
        self.billing_info_form = RegistrationBillingInfoForm(**kwargs)

    @cached_property
    def required_forms(self):
        return [
            super(),
            self.billing_info_select_form,
        ] + self.agreement_forms

    @cached_property
    def all_forms(self):
        all_forms = self.required_forms
        if self.instance.subject.registration_type_participants:
            all_forms += self.participants_formset.forms
        elif self.instance.subject.registration_type_groups:
            all_forms += self.group_formset.forms + self.group_members_formset.forms
        if (
            not self.billing_info_select_form.is_valid()
            or self.billing_info_select_form.cleaned_data["billing_info"] != "none"
        ):
            all_forms.append(self.billing_info_form)
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
        if (
            not self.billing_info_select_form.is_valid()
            or self.billing_info_select_form.cleaned_data["billing_info"] != "none"
        ):
            results.append(self.billing_info_form.is_valid())
        return all(results)

    @cached_property
    def errors(self):
        return {
            (form.prefix + field_name if form.prefix else field_name): error
            for form in self.all_forms
            for field_name, error in form.errors.items()
        }

    @transaction.atomic
    def save(self, commit=True):
        # set user
        self.instance.created_by = self.user
        self.instance.user = self.user

        # set price
        self.instance.price = (
            self.instance.subject_variant.price if self.instance.subject_variant else self.instance.subject.price
        )

        # create
        super().save(True)

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

        if self.billing_info_select_form.cleaned_data["billing_info"] != "none":

            # save registration billing info
            registration_billing_info = self.billing_info_form.save(commit=False)
            registration_billing_info.registration = self.instance
            registration_billing_info.save()

            # save / update user billing info
            if self.billing_info_select_form.cleaned_data["billing_info"] == "new":
                billing_info = BillingInfo()
                billing_info.user = self.instance.user
            else:
                billing_info = BillingInfo.objects.get(id=self.billing_info_select_form.cleaned_data["billing_info"])
            for attr in [
                "name",
                "street",
                "city",
                "postal_code",
                "company_num",
                "vat_number",
                "contact_person",
                "phone",
                "email",
                "employee",
            ]:
                setattr(billing_info, attr, getattr(registration_billing_info, attr))
            billing_info.save()

        self.instance.generate_variable_symbol_and_slug()
        self.instance.send_mail()
        return self.instance


class CourseRegistrationForm(RegistrationForm):
    periods = forms.ModelMultipleChoiceField(
        queryset=SchoolYearPeriod.objects.all(),
        widget=CheckboxSelectMultipleBootstrap(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_periods = self.instance.subject.course.school_year_division.periods.filter(
            end__gte=date.today(),
        )
        if self.instance.subject.course.allow_period_selection:
            self.fields["periods"].widget.choices.queryset = self.available_periods
        else:
            del self.fields["periods"]

    class Meta:
        model = CourseRegistration
        exclude = ("subject", "user", "cancelation_requested", "cancelation_requested_by", "canceled", "canceled_by")

    @transaction.atomic
    def save(self, commit=True):
        super().save()
        CourseRegistrationPeriod.objects.bulk_create(
            CourseRegistrationPeriod(
                registration=self.instance,
                period=period,
            )
            for period in self.cleaned_data.get("periods", self.available_periods)
        )
        return self.instance


class EventRegistrationForm(RegistrationForm):
    class Meta:
        model = EventRegistration
        exclude = ("subject", "user", "cancelation_requested", "cancelation_requested_by", "canceled", "canceled_by")


class OrderableRegistrationForm(RegistrationForm):
    class Meta:
        model = OrderableRegistration
        exclude = ("subject", "user", "cancelation_requested", "cancelation_requested_by", "canceled", "canceled_by")


class RegistrationAdminForm(forms.ModelForm):
    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if "subject_variant" in self.fields:
            self.fields["subject_variant"].widget.choices.queryset = self.subject.variants

        # choices for agreement options
        instance = kwargs.get("instance")
        self.fields["agreement_options"].widget.choices = tuple(
            (agreement.name, tuple((option.id, option.name) for option in agreement.all_options))
            for agreement in (instance.all_agreements if instance else self.subject.all_registration_agreements)
        )


class SchoolAdminMixin:
    def _add_error_required(self, field_name):
        self.add_error(
            field_name,
            ValidationError(
                self.fields[field_name].error_messages["required"],
                code="required",
            ),
        )

    def clean(self):
        # check required school and class
        x_group = self.cleaned_data.get(self.x_group)
        if x_group and x_group.require_school:
            # require school
            if self.cleaned_data.get("school"):
                self.cleaned_data["school_other"] = ""
            elif not self.cleaned_data.get("school_other"):
                self._add_error_required("school_other")
            # require school class
            if not self.cleaned_data.get("school_class"):
                self._add_error_required("school_class")
        else:
            # delete school and class
            self.cleaned_data["school"] = None
            self.cleaned_data["school_other"] = ""
            self.cleaned_data["school_class"] = ""
        return self.cleaned_data


class RegistrationParticipantAdminForm(RegistrationParticipantFormMixin, SchoolAdminMixin, forms.ModelForm):
    x_group = "age_group"

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get("instance")

        self.fields["age_group"].widget.choices.queryset = self.subject.age_groups
        if self.subject.age_groups.count() == 1:
            self.fields["age_group"].initial = self.subject.age_groups.first()

        questions = self.obj.all_questions if self.obj else self.subject.all_questions
        answers = instance.get_answers() if instance else {}
        for q in questions:
            self.fields["q_" + q.name].initial = answers.get(q.name)

        self._setup_required_fields()

    def save(self, commit=True):
        self.instance.answers = dumps(
            {
                q.name: self.cleaned_data["q_" + q.name]
                for q in (self.obj.all_questions if self.obj else self.subject.all_questions)
            }
        )
        self._set_birth_date_gender()
        return super().save(commit)


class RegistrationGroupAdminForm(SchoolAdminMixin, forms.ModelForm):
    x_group = "target_group"

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get("instance")

        self.fields["target_group"].widget.choices.queryset = self.subject.target_groups

        questions = self.obj.all_questions if self.obj else self.subject.all_questions
        answers = instance.get_answers() if instance else {}
        for q in questions:
            self.fields["q_" + q.name].initial = answers.get(q.name)

    def save(self, commit=True):
        self.instance.answers = dumps(
            {
                q.name: self.cleaned_data["q_" + q.name]
                for q in (self.obj.all_questions if self.obj else self.subject.all_questions)
            }
        )
        return super().save(commit)
