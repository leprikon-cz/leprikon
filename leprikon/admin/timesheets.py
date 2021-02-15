from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from ..forms.timesheets import TimesheetEntryAdminForm
from ..models.timesheets import Timesheet, TimesheetEntry, TimesheetEntryType
from .export import AdminExportMixin
from .filters import LeaderListFilter
from .journals import JournalLeaderEntryInlineAdmin


@admin.register(TimesheetEntry)
class TimesheetEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form = TimesheetEntryAdminForm
    date_hierarchy = "date"
    list_display = ("timesheet", "date", "start", "end", "duration", "entry_type")
    list_filter = ("entry_type", ("timesheet__leader", LeaderListFilter))
    ordering = (
        "-date",
        "-start",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.timesheet.submitted:
            return ("timesheet", "entry_type", "date", "start", "end")
        return ()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.timesheet.submitted:
            return False
        return super().has_delete_permission(request, obj)


class TimesheetEntryInlineAdmin(admin.TabularInline):
    class form(forms.ModelForm):
        class Meta:
            model = TimesheetEntry
            fields = []

    model = TimesheetEntry
    ordering = ("date", "start")
    readonly_fields = ("date", "start", "end", "entry_type", "description_html", "edit_link")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.submitted:
            return False
        return super().has_delete_permission(request, obj)

    def description_html(self, obj):
        return obj.description

    description_html.short_description = _("description")
    description_html.admin_order_field = "description"
    description_html.allow_tags = True

    def edit_link(self, obj):
        return '<a href="{url}" title="{title}" target="_blank">{edit}</a>'.format(
            url=reverse("admin:leprikon_timesheetentry_change", args=[obj.id]),
            title=_("update entry"),
            edit=_("edit"),
        )

    edit_link.short_description = ""
    edit_link.allow_tags = True


@admin.register(Timesheet)
class TimesheetAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display = ("leader", "period", "group_durations", "submitted", "paid")
    list_filter = (("leader", LeaderListFilter), "period")
    inlines = (TimesheetEntryInlineAdmin, JournalLeaderEntryInlineAdmin)
    actions = ("submit", "set_paid")

    # do not allow to add timesheets in admin
    # timesheets are created automatically
    def has_add_permission(self, request):
        return False

    # do not allow to delete submitted timesheets
    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or not obj.submitted)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:

            def delete_selected(model_admin, request, queryset):
                queryset = queryset.filter(submitted=False)
                return admin.actions.delete_selected(model_admin, request, queryset)

            actions["delete_selected"] = (delete_selected, *actions["delete_selected"][1:])
        return actions

    def group_durations(self, obj):
        return "<br/>".join(
            "<b>{name}</b>: {duration}".format(
                name=group.name,
                duration=group.duration,
            )
            for group in obj.groups
        )

    group_durations.allow_tags = True
    group_durations.short_description = _("group durations")

    def set_paid(self, request, queryset):
        queryset.update(submitted=True, paid=True)
        self.message_user(request, _("Selected timesheets where marked as paid."))

    set_paid.short_description = _("Mark selected timesheets as paid")

    def submit(self, request, queryset):
        queryset.update(submitted=True)
        self.message_user(request, _("Selected timesheets where submitted."))

    submit.short_description = _("Submit selected timesheets")


@admin.register(TimesheetEntryType)
class TimesheetEntryTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    list_editable = ("order",)
