from datetime import date, datetime
from json import dumps
from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.forms.widgets import Media
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sentry_sdk import capture_message

from ..models.activities import (
    Activity,
    ActivityGroup,
    ActivityModel,
    ActivityType,
    ActivityVariant,
    CalendarEvent,
    Registration,
    RegistrationBillingInfo,
    RegistrationGroup,
    RegistrationGroupMember,
    RegistrationParticipant,
)
from ..models.agegroup import AgeGroup
from ..models.citizenship import Citizenship
from ..models.courses import Course, CourseRegistration, CourseRegistrationPeriod
from ..models.department import Department
from ..models.events import Event, EventRegistration
from ..models.fields import DayOfWeek, DaysOfWeek
from ..models.leprikonsite import LeprikonSite
from ..models.orderables import Orderable, OrderableRegistration
from ..models.place import Place
from ..models.roles import BillingInfo, GroupContact, Leader, Parent, Participant
from ..models.school import School
from ..models.schoolyear import SchoolYearPeriod
from ..models.targetgroup import TargetGroup
from ..utils import get_age, get_birth_date, get_gender
from .fields import AgreementBooleanField
from .form import FormMixin
from .widgets import CheckboxSelectMultipleBootstrap, RadioSelectBootstrap

User = get_user_model()


class RegistrationsFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_("Search term"), required=False)
    not_paid = forms.BooleanField(label=_("Not paid"), required=False)


class ActivityFilterForm(FormMixin, forms.Form):
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
    days_of_week = forms.MultipleChoiceField(label=_("Day of week"), choices=DayOfWeek.choices, required=False)
    past = forms.BooleanField(label=_("Show past"), required=False)
    reg_active = forms.BooleanField(label=_("Available for registration"), required=False)
    invisible = forms.BooleanField(label=_("Show invisible"), required=False)

    _models = {
        ActivityModel.COURSE: Course,
        ActivityModel.EVENT: Event,
        ActivityModel.ORDERABLE: Orderable,
    }

    def __init__(self, activity_type_model, activity_types, school_year, is_staff, data, **kwargs):
        super().__init__(data=data, **kwargs)
        self.activity_type_model = activity_type_model

        # pre filter activities by initial params
        qs = self._models[activity_type_model].objects
        if activity_type_model != ActivityModel.EVENT or data.get("past"):
            qs = qs.filter(school_year=school_year)
        if len(activity_types) == 1:
            qs = qs.filter(activity_type=activity_types[0])
        else:
            qs = qs.filter(activity_type__in=activity_types)
        if not is_staff or "invisible" not in data:
            qs = qs.filter(public=True)
        self.qs = qs

        activity_ids = tuple(qs.order_by("id").values_list("id", flat=True).distinct())
        if len(activity_types) == 1:
            del self.fields["course_types"]
            del self.fields["event_types"]
            del self.fields["orderable_types"]
        elif activity_type_model == ActivityModel.COURSE:
            del self.fields["event_types"]
            del self.fields["orderable_types"]
            self.fields["course_types"].queryset = ActivityType.objects.filter(id__in=(st.id for st in activity_types))
        elif activity_type_model == ActivityModel.EVENT:
            del self.fields["course_types"]
            del self.fields["orderable_types"]
            self.fields["event_types"].queryset = ActivityType.objects.filter(id__in=(st.id for st in activity_types))
        elif activity_type_model == ActivityModel.ORDERABLE:
            del self.fields["course_types"]
            del self.fields["event_types"]
            self.fields["orderable_types"].queryset = ActivityType.objects.filter(
                id__in=(st.id for st in activity_types)
            )

        self.fields["departments"].queryset = Department.objects.filter(activities__id__in=activity_ids).distinct()
        if self.fields["departments"].queryset.count() == 0:
            del self.fields["departments"]

        self.fields["groups"].queryset = ActivityGroup.objects.filter(
            activity_types__in=activity_types, activities__id__in=activity_ids
        ).distinct()
        if self.fields["groups"].queryset.count() == 0:
            del self.fields["groups"]

        self.fields["leaders"].queryset = (
            Leader.objects.filter(activities__id__in=activity_ids)
            .distinct()
            .order_by("user__first_name", "user__last_name")
        )
        if self.fields["leaders"].queryset.count() == 0:
            del self.fields["leaders"]

        self.fields["places"].queryset = Place.objects.filter(activities__id__in=activity_ids).distinct()
        if self.fields["places"].queryset.count() == 0:
            del self.fields["places"]

        self.fields["age_groups"].queryset = AgeGroup.objects.filter(activities__id__in=activity_ids).distinct()
        if self.fields["age_groups"].queryset.count() == 0:
            del self.fields["age_groups"]

        self.fields["target_groups"].queryset = TargetGroup.objects.filter(activities__id__in=activity_ids).distinct()
        if self.fields["target_groups"].queryset.count() == 0:
            del self.fields["target_groups"]

        if activity_type_model == ActivityModel.EVENT:
            del self.fields["days_of_week"]
        if activity_type_model != ActivityModel.EVENT:
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
            qs = qs.filter(activity_type__in=self.cleaned_data["course_types"])
        elif self.cleaned_data.get("event_types"):
            qs = qs.filter(activity_type__in=self.cleaned_data["event_types"])
        elif self.cleaned_data.get("orderable_types"):
            qs = qs.filter(activity_type__in=self.cleaned_data["orderable_types"])
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
            qs = qs.filter(times__days_of_week__match=DaysOfWeek(self.cleaned_data["days_of_week"]))
        if self.activity_type_model == ActivityModel.EVENT:
            if self.cleaned_data["past"]:
                qs = qs.filter(end_date__lte=now()).order_by("-start_date", "-start_time")
            else:
                qs = qs.filter(end_date__gte=now())
        if self.cleaned_data["reg_active"]:
            qs = qs.filter(
                (Q(variants__reg_from=None) | Q(variants__reg_from__lte=now()))
                & (Q(variants__reg_to=None) | Q(variants__reg_to__gte=now()))
            )
        return qs.distinct()


class ActivityForm(FormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["description"]


class ActivityAdminForm(forms.ModelForm):
    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get("instance")
        leprikon_site = LeprikonSite.objects.get_current()

        # limit choices of groups
        self.fields["groups"].widget.choices.queryset = self.activity_type.groups.all()

        # limit choices of leaders
        leaders_choices = self.fields["leaders"].widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years=self.school_year)

        # limit choices of questions
        if instance:
            questions_choices = self.fields["questions"].widget.choices
            questions_choices.queryset = questions_choices.queryset.exclude(
                id__in=instance.activity_type.questions.values("id")
            )

        # limit choices of registration agreements
        registration_agreements_choices = self.fields["registration_agreements"].widget.choices
        registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
            id__in=leprikon_site.registration_agreements.values("id")
        )
        if instance:
            registration_agreements_choices.queryset = registration_agreements_choices.queryset.exclude(
                id__in=instance.activity_type.registration_agreements.values("id")
            )


class ActivityVariantForm(forms.ModelForm):
    activity: Activity

    class Meta:
        model = ActivityVariant
        exclude = ("activity", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.activity = self.activity
        if self.activity.activity_type.model == ActivityModel.COURSE:
            school_year_divisions = self.fields["school_year_division"].widget.choices.queryset.filter(
                school_year=self.activity.school_year
            )
            self.fields["school_year_division"].widget.choices.queryset = school_year_divisions
        if self.activity.registration_type_participants:
            self.fields["age_groups"].widget.choices.queryset = self.activity.age_groups.all()
        if self.activity.registration_type_groups:
            self.fields["target_groups"].widget.choices.queryset = self.activity.target_groups.all()
        if ActivityVariant.objects.filter(activity=self.activity).exclude(id=self.instance.id).count():
            self.fields["name"].required = True


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
            qs = RegistrationParticipant.objects.filter(
                registration__activity_id=self.activity.id,
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
        self.fields["age_group"].widget.choices.queryset = self.activity.age_groups.all()
        if self.activity.age_groups.count() == 1:
            self.fields["age_group"].initial = self.activity.age_groups.first()

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
            dict((q.slug, q.get_field()) for q in self.activity.all_questions),
        )(**kwargs)

    @cached_property
    def media(self):
        media = Media()
        for form in self.required_forms:
            media = media + form.media
        return media

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

    @transaction.atomic
    def save(self, commit=True):
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
        participant_answers = participant.get_answers()
        participant_answers.update(self.instance.get_answers())
        participant.answers = dumps(participant_answers)
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
        self.fields["target_group"].widget.choices.queryset = self.activity.target_groups.all()
        if self.activity.target_groups.count() == 1:
            self.fields["target_group"].initial = self.activity.target_groups.first()

        # initial school
        self.fields["school"].initial = "other" if School.objects.count() == 0 else None

        class GroupContactSelectForm(FormMixin, forms.Form):
            group_contact = forms.ChoiceField(
                label=_("Choose"),
                choices=[("new", _("new group information"))] + list((gc.id, gc) for gc in self.user_group_contacts),
                initial="new",
                widget=RadioSelectBootstrap(),
            )

        kwargs["prefix"] = self.prefix + "-group_contact_select"
        self.group_contact_select_form = GroupContactSelectForm(**kwargs)

        kwargs["prefix"] = self.prefix + "-questions"
        self.questions_form = type(
            str("QuestionsForm"),
            (FormMixin, forms.Form),
            dict((q.slug, q.get_field()) for q in self.activity.all_questions),
        )(**kwargs)

    @cached_property
    def media(self):
        media = Media()
        for form in self.required_forms:
            media = media + form.media
        return media

    @cached_property
    def required_forms(self):
        return [
            super(),
            self.group_contact_select_form,
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

    @transaction.atomic
    def save(self, commit=True):
        # set answers
        self.instance.answers = dumps(self.questions_form.cleaned_data)

        # create
        super().save(commit)

        # save / update group contact
        if self.group_contact_select_form.cleaned_data["group_contact"] == "new":
            group_contact = GroupContact()
            group_contact.user = self.instance.registration.user
        else:
            group_contact = GroupContact.objects.get(id=self.group_contact_select_form.cleaned_data["group_contact"])
        for attr in [
            "target_group",
            "name",
            "first_name",
            "last_name",
            "street",
            "city",
            "postal_code",
            "phone",
            "email",
            "school",
            "school_other",
            "school_class",
        ]:
            setattr(group_contact, attr, getattr(self.instance, attr))
        group_contact_answers = group_contact.get_answers()
        group_contact_answers.update(self.instance.get_answers())
        group_contact.answers = dumps(group_contact_answers)
        group_contact.save()
        return self.instance


class RegistrationGroupMemberForm(FormMixin, forms.ModelForm):
    pass


class RegistrationBillingInfoForm(FormMixin, forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = RegistrationBillingInfo
        exclude = ["registration"]


class RegistrationForm(FormMixin, forms.ModelForm):
    instance: Registration

    def __init__(self, activity: Activity, activity_variant: ActivityVariant, user, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        self.instance.activity = activity
        self.instance.activity_variant = activity_variant

        # sub forms
        if activity.registration_type_participants:
            registered_birth_nums = list(
                RegistrationParticipant.objects.filter(
                    registration_id__in=self.instance.activity.active_registrations.values("id"),
                    birth_num__isnull=False,
                ).values_list("birth_num", flat=True)
            )

            participant_form = type(
                RegistrationParticipantForm.__name__,
                (RegistrationParticipantForm,),
                {
                    "activity": activity,
                    "user_participants": user.leprikon_participants.exclude(
                        birth_num__in=registered_birth_nums,
                    ),
                    "user_parents": list(user.leprikon_parents.all()),
                },
            )

            self.participants_formset = inlineformset_factory(
                Registration,
                RegistrationParticipant,
                form=participant_form,
                fk_name="registration",
                exclude=[],
                extra=activity_variant.max_participants_count,
                min_num=activity_variant.min_participants_count,
                max_num=activity_variant.max_participants_count,
                validate_min=True,
                validate_max=True,
            )(kwargs.get("data"), instance=self.instance)

            del self.fields["participants_count"]

        elif activity.registration_type_groups:
            GroupForm = type(
                RegistrationGroupForm.__name__,
                (RegistrationGroupForm,),
                {"activity": activity, "user_group_contacts": user.leprikon_group_contacts.all()},
            )

            self.group_formset = inlineformset_factory(
                Registration,
                RegistrationGroup,
                form=GroupForm,
                fk_name="registration",
                exclude=[],
                extra=1,
                min_num=1,
                max_num=1,
                validate_min=True,
                validate_max=True,
            )(kwargs.get("data"), instance=self.instance)

            if activity_variant.require_group_members_list:
                self.group_members_formset = inlineformset_factory(
                    Registration,
                    RegistrationGroupMember,
                    form=RegistrationGroupMemberForm,
                    fk_name="registration",
                    exclude=[],
                    extra=activity_variant.max_participants_count,
                    min_num=activity_variant.min_participants_count,
                    max_num=activity_variant.max_participants_count,
                    validate_min=True,
                    validate_max=True,
                )(kwargs.get("data"), instance=self.instance)
            if activity_variant.require_group_members_list:
                del self.fields["participants_count"]
            else:
                self.fields["participants_count"].validators = [
                    MinValueValidator(activity_variant.min_participants_count),
                    MaxValueValidator(activity_variant.max_participants_count),
                ]
                self.fields["participants_count"].widget.attrs["min"] = activity_variant.min_participants_count
                self.fields["participants_count"].widget.attrs["max"] = activity_variant.max_participants_count

        del kwargs["instance"]

        self.agreement_forms = []
        for agreement in self.instance.activity.all_registration_agreements:
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
    def media(self):
        media = Media()
        for form in self.all_forms:
            media = media + form.media
        return media

    @cached_property
    def required_forms(self):
        return [
            super(),
            self.billing_info_select_form,
        ] + self.agreement_forms

    @cached_property
    def all_forms(self):
        all_forms = self.required_forms
        if self.instance.activity.registration_type_participants:
            all_forms += self.participants_formset.forms
        elif self.instance.activity.registration_type_groups:
            all_forms += self.group_formset.forms
            if self.instance.activity_variant.require_group_members_list:
                all_forms += self.group_members_formset.forms
        if (
            not self.billing_info_select_form.is_valid()
            or self.billing_info_select_form.cleaned_data["billing_info"] != "none"
        ):
            all_forms.append(self.billing_info_form)
        return all_forms

    def is_valid(self):
        # validate all required forms
        results = [form.is_valid() for form in self.required_forms]
        if self.instance.activity.registration_type_participants:
            results.append(self.participants_formset.is_valid())
        elif self.instance.activity.registration_type_groups:
            results.append(self.group_formset.is_valid())
            if self.instance.activity_variant.require_group_members_list:
                results.append(self.group_members_formset.is_valid())
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

        if self.instance.activity.registration_type_participants:
            self.instance.participants_count = len([data for data in self.participants_formset.cleaned_data if data])
        elif self.instance.activity.registration_type_groups:
            if self.instance.activity_variant.require_group_members_list:
                self.instance.participants_count = len(
                    [data for data in self.group_members_formset.cleaned_data if data]
                )
            else:
                self.instance.participants_count = self.cleaned_data["participants_count"]

        # set price
        self.instance.price = self.instance.activity_variant.get_price(self.instance.participants_count)

        # create
        super().save(True)

        if self.instance.activity.registration_type_participants:
            # save participants
            self.participants_formset.user = self.instance.user
            self.participants_formset.save()

        elif self.instance.activity.registration_type_groups:
            # save group
            self.group_formset.save()

            # save group members
            if self.instance.activity_variant.require_group_members_list:
                self.group_members_formset.save()

        # save additional questions
        self.instance.questions.set(self.instance.activity.all_questions)

        # save legal agreements
        self.instance.agreements.set(self.instance.activity.all_registration_agreements)

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
        if self.instance.activity_variant.school_year_division:
            self.available_periods = self.instance.activity_variant.school_year_division.periods.exclude(
                end__lt=date.today(),
            )
        else:
            self.available_periods = []

        if (
            self.instance.activity_variant.school_year_division
            and self.instance.activity_variant.allow_period_selection
        ):
            self.fields["periods"].widget.choices.queryset = self.available_periods
        else:
            del self.fields["periods"]

    class Meta:
        model = CourseRegistration
        exclude = (
            "activity",
            "activity_variant",
            "calendar_event",
            "user",
            "cancelation_requested",
            "cancelation_requested_by",
            "canceled",
            "canceled_by",
        )

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
        exclude = (
            "activity",
            "activity_variant",
            "calendar_event",
            "user",
            "cancelation_requested",
            "cancelation_requested_by",
            "canceled",
            "canceled_by",
        )


class OrderableRegistrationForm(RegistrationForm):
    start_date = forms.DateField(widget=forms.HiddenInput())
    start_time = forms.TimeField(widget=forms.HiddenInput())

    class Meta:
        model = OrderableRegistration
        exclude = (
            "activity",
            "activity_variant",
            "calendar_event",
            "user",
            "cancelation_requested",
            "cancelation_requested_by",
            "canceled",
            "canceled_by",
        )

    @transaction.atomic
    def save(self, commit=True):
        start = datetime.combine(self.cleaned_data["start_date"], self.cleaned_data["start_time"])
        end: datetime = start + self.instance.activity.orderable.duration
        self.instance.calendar_event = CalendarEvent.objects.create(
            name=self.instance.activity.name,
            activity=self.instance.activity,
            start_date=start.date(),
            start_time=start.time(),
            end_date=end.date(),
            end_time=end.time(),
            preparation_time=self.instance.activity.orderable.preparation_time,
            recovery_time=self.instance.activity.orderable.recovery_time,
            is_canceled=False,
        )
        self.instance.calendar_event.resources.set(self.instance.activity_variant.required_resources.all())
        self.instance.calendar_event.resource_groups.set(self.instance.activity_variant.required_resource_groups.all())
        return super().save()


class RegistrationAdminForm(forms.ModelForm):
    instance: Registration
    activity: Activity
    activity_variant: ActivityVariant

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        self.fields["activity_variant"].widget.choices.queryset = self.activity.variants.all()

        # choices for agreement options
        if "agreement_options" in self.fields:
            instance: Registration = kwargs.get("instance")
            self.fields["agreement_options"].widget.choices = tuple(
                (agreement.name, tuple((option.id, option.name) for option in agreement.all_options))
                for agreement in (instance.all_agreements if instance else self.activity.all_registration_agreements)
            )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        activity = cleaned_data.get("activity")
        activity_variant = cleaned_data.get("activity_variant")
        if activity and activity_variant and activity_variant.activity_id != activity.id:
            raise ValidationError(
                {
                    "activity_variant": ValidationError(
                        self.fields["activity_variant"].error_messages["invalid_choice"],
                        code="invalid_choice",
                    )
                }
            )
        return cleaned_data


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

        self.fields["age_group"].widget.choices.queryset = self.activity.age_groups.all()
        if self.activity.age_groups.count() == 1:
            self.fields["age_group"].initial = self.activity.age_groups.first()

        questions = self.obj.all_questions if self.obj else self.activity.all_questions
        answers = instance.get_answers() if instance else {}
        for q in questions:
            self.fields["q_" + q.slug].initial = answers.get(q.slug)

        self._setup_required_fields()

    def save(self, commit=True):
        self.instance.answers = dumps(
            {
                q.slug: self.cleaned_data["q_" + q.slug]
                for q in (self.obj.all_questions if self.obj else self.activity.all_questions)
            }
        )
        self._set_birth_date_gender()
        return super().save(commit)


class RegistrationGroupAdminForm(SchoolAdminMixin, forms.ModelForm):
    x_group = "target_group"

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        instance = kwargs.get("instance")

        self.fields["target_group"].widget.choices.queryset = self.activity.target_groups.all()

        questions = self.obj.all_questions if self.obj else self.activity.all_questions
        answers = instance.get_answers() if instance else {}
        for q in questions:
            self.fields["q_" + q.slug].initial = answers.get(q.slug)

    def save(self, commit=True):
        self.instance.answers = dumps(
            {
                q.slug: self.cleaned_data["q_" + q.slug]
                for q in (self.obj.all_questions if self.obj else self.activity.all_questions)
            }
        )
        return super().save(commit)
