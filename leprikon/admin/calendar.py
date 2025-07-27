from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from leprikon.models.leprikonsite import LeprikonSite

from ..models.calendar import CalendarEvent, CalendarExport, Resource, ResourceAvailability, ResourceGroup
from .filters import IsNullFieldListFilter


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


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "activity",
        "start_date",
        "start_time",
        "resources_list",
        "resource_groups_list",
    )
    list_filter = (
        "activity__activity_type",
        "resources",
        "resource_groups",
    )
    raw_id_fields = ("activity",)
    filter_horizontal = ("resources", "resource_groups")
    search_fields = ("activity_variant__name",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("activity").prefetch_related("resources")

    @admin.display(description=_("resources"))
    def resources_list(self, obj):
        return ", ".join([str(resource) for resource in obj.resources.all()])

    @admin.display(description=_("resource groups"))
    def resource_groups_list(self, obj):
        return ", ".join([str(group) for group in obj.resource_groups.all()])


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
