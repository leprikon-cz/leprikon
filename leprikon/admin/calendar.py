from datetime import date

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from leprikon.models.leprikonsite import LeprikonSite

from ..models.calendar import CalendarEvent, CalendarExport, Resource, ResourceAvailability, ResourceGroup
from .filters import IsCanceledListFilter, IsNullFieldListFilter


class AvailabilityInlineAdmin(admin.TabularInline):
    model = ResourceAvailability
    extra = 0


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    inlines = (AvailabilityInlineAdmin,)
    search_fields = ("name",)
    list_display = ("name", "availabilities", "leader")
    list_filter = (("leader", IsNullFieldListFilter),)
    raw_id_fields = ("leader",)

    @admin.display(description=_("availabilities"))
    def availabilities(self, obj: Resource) -> str:
        return mark_safe("<br/>".join(str(availability) for availability in obj.availabilities.all()))


@admin.register(ResourceGroup)
class ResourceGroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "resources_list")
    filter_horizontal = ("resources",)

    @admin.display(description=_("resources"))
    def resources_list(self, obj: ResourceGroup) -> str:
        return mark_safe("<br/>".join(str(resource) for resource in obj.resources.all()))


class IsFutureListFilter(admin.SimpleListFilter):
    parameter_name = "past"
    title = _("past events")

    def expected_parameters(self):
        return [self.parameter_name]

    def lookups(self, request, model_admin):
        return (
            (None, _("future only")),
            ("yes", _("include past")),
        )

    def choices(self, cl):
        value = self.value()
        return [
            {
                "selected": value != "yes",
                "query_string": cl.get_query_string({}, [self.parameter_name]),
                "display": _("future only"),
            },
            {
                "selected": value == "yes",
                "query_string": cl.get_query_string({self.parameter_name: "yes"}),
                "display": _("include past"),
            },
        ]

    def queryset(self, request, queryset):
        value = self.value()
        return queryset if value == "yes" else queryset.filter(start_date__gte=date.today())


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    date_hierarchy = "start_date"
    list_display = (
        "name",
        "activity",
        "start_date",
        "start_time",
        "resources_list",
        "resource_groups_list",
    )
    list_filter = (
        IsFutureListFilter,
        IsCanceledListFilter,
        "activity__activity_type",
        "resources",
        "resource_groups",
    )
    raw_id_fields = ("activity",)
    filter_horizontal = ("resources", "resource_groups")
    search_fields = ("activity_variant__name",)

    class Media:
        css = {"all": ["leprikon/css/calendar.changelist.css"]}

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("activity").prefetch_related("resources")

    @admin.display(description=_("resources"))
    def resources_list(self, obj: CalendarEvent) -> str:
        return ", ".join([str(resource) for resource in obj.resources.all()])

    @admin.display(description=_("resource groups"))
    def resource_groups_list(self, obj: CalendarEvent) -> str:
        return ", ".join([str(group) for group in obj.resource_groups.all()])

    def get_css(self, obj: CalendarEvent) -> str:
        classes = []
        if obj.is_canceled:
            classes.append("event-canceled")
        else:
            classes.append("event-active")
        if obj.has_conflicting_events():
            classes.append("event-conflict")
        return " ".join(classes)

    legend = (
        ("event-active", _("active")),
        ("event-canceled", _("canceled")),
        ("event-active event-conflict", _("conflict")),
    )


@admin.register(CalendarExport)
class CalendarExportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "resources_list",
        "relevant_events_count",
        "ical_url",
    )
    list_filter = ("resources",)
    filter_horizontal = ("resources",)

    @admin.display(description=_("resources"))
    def resources_list(self, obj: CalendarExport) -> str:
        if not obj.resource_ids:
            return _("all resources")
        return mark_safe("<br>".join(str(resource) for resource in obj.resources.all()))

    @admin.display(description=_("relevant events count"))
    def relevant_events_count(self, obj: CalendarExport) -> str:
        return f"{obj.relevant_events.count()} / {obj.limit_events_count}"

    @admin.display(description=_("iCal URL"))
    def ical_url(self, obj: CalendarExport) -> str:
        leprikon_site = LeprikonSite.objects.get_current()
        uri = reverse("api:calendarexport-ical", args=(obj.id,))
        return leprikon_site.url + uri
