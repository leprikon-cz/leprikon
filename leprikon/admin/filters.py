from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models.roles import Leader
from ..models.schoolyear import SchoolYear
from ..models.subjects import Subject, SubjectGroup, SubjectType


class SchoolYearListFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        try:
            request.school_year = SchoolYear.objects.get(year=params["year"])
        except (SchoolYear.DoesNotExist, ValueError, KeyError):
            pass
        self.school_year = request.school_year
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return ["year"]

    def choices(self, cl):
        return [
            {
                "selected": school_year == self.school_year,
                "query_string": cl.get_query_string({"year": school_year.year}),
                "display": school_year,
            }
            for school_year in SchoolYear.objects.all()
        ]

    def queryset(self, request, queryset):
        return queryset.filter(**{self.field_path: self.school_year})


class ActiveListFilter(admin.SimpleListFilter):
    title = _("status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            (None, _("active")),
            ("inactive", _("inactive")),
        )

    def queryset(self, request, queryset):
        if self.value() == "inactive":
            return queryset.filter(active=False)
        else:
            return queryset.filter(active=True)

    def choices(self, cl):
        value = self.value()
        return [
            {
                "selected": value != "inactive",
                "query_string": cl.get_query_string({}, [self.parameter_name]),
                "display": _("active"),
            },
            {
                "selected": value == "inactive",
                "query_string": cl.get_query_string({self.parameter_name: "inactive"}),
                "display": _("inactive"),
            },
        ]


class ApprovedListFilter(admin.SimpleListFilter):
    title = _("approval")
    parameter_name = "approved"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("approved")),
            ("no", _("unapproved")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(approved__isnull=False)
        if self.value() == "no":
            return queryset.filter(approved__isnull=True)


class CanceledListFilter(admin.SimpleListFilter):
    title = _("cancelation")
    parameter_name = "canceled"

    def lookups(self, request, model_admin):
        return (
            (None, _("not canceled")),
            ("yes", _("canceled")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(canceled__isnull=False)
        else:
            return queryset.filter(canceled__isnull=True)

    def choices(self, cl):
        value = self.value()
        return [
            {
                "selected": value != "yes",
                "query_string": cl.get_query_string({}, [self.parameter_name]),
                "display": _("active"),
            },
            {
                "selected": value == "yes",
                "query_string": cl.get_query_string({self.parameter_name: "yes"}),
                "display": _("canceled"),
            },
        ]


class SubjectTypeListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.subject_types = SubjectType.objects.all()
        subject_type_type = getattr(model_admin, "subject_type_type", None)
        if subject_type_type:
            self.subject_types = self.subject_types.filter(subject_type=subject_type_type)
        super().__init__(field, request, params, model, model_admin, field_path)
        if subject_type_type:
            self.title = SubjectType.subject_type_type_labels[subject_type_type]
        request.leprikon_subject_type_id = self.lookup_val

    def field_choices(self, field, request, model_admin):
        return [(t.id, t.plural) for t in self.subject_types.all()]


class SubjectGroupListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        subject_type_type = getattr(model_admin, "subject_type_type", None)
        if hasattr(request, "leprikon_subject_type_id") and request.leprikon_subject_type_id:
            self.groups = SubjectGroup.objects.filter(subject_types__id=request.leprikon_subject_type_id)
        elif subject_type_type:
            self.groups = SubjectGroup.objects.filter(subject_types__subject_type=subject_type_type)
        else:
            self.groups = SubjectGroup.objects.all()
        super().__init__(field, request, params, model, model_admin, field_path)
        request.leprikon_subject_group_id = self.lookup_val

    def field_choices(self, field, request, model_admin):
        return [(g.id, g.plural) for g in self.groups.distinct()]


class SubjectListFilter(admin.RelatedFieldListFilter):
    model = Subject

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.subjects = self.model.objects.filter(school_year=request.school_year)
        subject_type_type = getattr(model_admin, "subject_type_type", None)
        if hasattr(request, "leprikon_subject_type_id") and request.leprikon_subject_type_id:
            self.subjects = self.subjects.filter(subject_type__id=request.leprikon_subject_type_id)
        elif subject_type_type:
            self.subjects = self.subjects.filter(subject_type__subject_type=subject_type_type)
        if hasattr(request, "leprikon_subject_group_id") and request.leprikon_subject_group_id:
            self.subjects = self.subjects.filter(subject_group__id=request.leprikon_subject_group_id)
        super().__init__(field, request, params, model, model_admin, field_path)
        if subject_type_type:
            self.title = SubjectType.subject_type_labels[subject_type_type]

    def field_choices(self, field, request, model_admin):
        return [(s.id, s.name) for s in self.subjects]


class LeaderListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.leaders = Leader.objects.filter(school_years=request.school_year)
        super().__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(leader.id, leader) for leader in self.leaders]


class IsNullFieldListFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = "%s__isnull" % field_path
        self.lookup_val = request.GET.get(self.lookup_kwarg)
        if not hasattr(field, "verbose_name") and hasattr(field, "related_model"):
            field.verbose_name = field.related_model._meta.verbose_name
        super().__init__(field, request, params, model, model_admin, field_path)
        if (
            self.used_parameters
            and self.lookup_kwarg in self.used_parameters
            and self.used_parameters[self.lookup_kwarg] in ("1", "0")
        ):
            self.used_parameters[self.lookup_kwarg] = bool(int(self.used_parameters[self.lookup_kwarg]))

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def choices(self, changelist):
        for lookup, title in ((None, _("All")), ("0", _("Set")), ("1", _("Not set"))):
            yield {
                "selected": self.lookup_val == lookup,
                "query_string": changelist.get_query_string(
                    {
                        self.lookup_kwarg: lookup,
                    }
                ),
                "display": title,
            }
