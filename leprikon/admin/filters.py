from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ..models.activities import Activity, ActivityGroup, ActivityModel, ActivityType
from ..models.journals import Journal
from ..models.roles import Leader
from ..models.schoolyear import SchoolYear


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


class ActivityTypeListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.activity_types = ActivityType.objects.all()
        activity_type_model: ActivityModel = getattr(model_admin, "activity_type_model", None)
        if activity_type_model:
            self.activity_types = self.activity_types.filter(model=activity_type_model)
        super().__init__(field, request, params, model, model_admin, field_path)
        if activity_type_model:
            self.title = activity_type_model.label
        request.leprikon_activity_type_id = self.lookup_val

    def field_choices(self, field, request, model_admin):
        return [(t.id, t.plural) for t in self.activity_types.all()]


class ActivityGroupListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        activity_type_model = getattr(model_admin, "activity_type_model", None)
        if hasattr(request, "leprikon_activity_type_id") and request.leprikon_activity_type_id:
            self.groups = ActivityGroup.objects.filter(activity_types__id=request.leprikon_activity_type_id)
        elif activity_type_model:
            self.groups = ActivityGroup.objects.filter(activity_types__model=activity_type_model)
        else:
            self.groups = ActivityGroup.objects.all()
        super().__init__(field, request, params, model, model_admin, field_path)
        request.leprikon_activity_group_id = self.lookup_val

    def field_choices(self, field, request, model_admin):
        return [(g.id, g.plural) for g in self.groups.distinct()]


class ActivityListFilter(admin.RelatedFieldListFilter):
    model = Activity

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.activities = self.model.objects.filter(school_year=request.school_year)
        activity_type_model: ActivityModel = getattr(model_admin, "activity_type_model", None)
        if hasattr(request, "leprikon_activity_type_id") and request.leprikon_activity_type_id:
            self.activities = self.activities.filter(activity_type__id=request.leprikon_activity_type_id)
        elif activity_type_model:
            self.activities = self.activities.filter(activity_type__model=activity_type_model)
        if hasattr(request, "leprikon_activity_group_id") and request.leprikon_activity_group_id:
            self.activities = self.activities.filter(activity_group__id=request.leprikon_activity_group_id)
        super().__init__(field, request, params, model, model_admin, field_path)
        if activity_type_model:
            self.title = activity_type_model.label

    def field_choices(self, field, request, model_admin):
        return [(s.id, s.name) for s in self.activities]


class JournalListFilter(admin.RelatedFieldListFilter):
    model = Journal

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.journals = (
            self.model.objects.filter(activity__school_year=request.school_year)
            .select_related("activity")
            .order_by("activity__name", "name")
        )
        if hasattr(request, "leprikon_activity_id") and request.leprikon_activity_id:
            self.journals = self.journals.filter(activity_id=request.leprikon_activity_id)
        elif hasattr(request, "leprikon_activity_type_id") and request.leprikon_activity_type_id:
            self.journals = self.journals.filter(activity__activity_type__id=request.leprikon_activity_type_id)
        super().__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(journal.id, str(journal)) for journal in self.journals]


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
