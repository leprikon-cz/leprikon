from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from ..forms.journals import JournalEntryAdminForm, JournalLeaderEntryAdminForm
from ..models.journals import JournalEntry, JournalLeaderEntry
from .export import AdminExportMixin
from .filters import LeaderListFilter, SchoolYearListFilter, SubjectListFilter


@admin.register(JournalLeaderEntry)
class JournalLeaderEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form = JournalLeaderEntryAdminForm
    list_display = ("timesheet", "date", "start", "end", "duration", "subject")
    list_filter = (
        ("timesheet__leader", LeaderListFilter),
        ("journal_entry__subject", SubjectListFilter),
    )
    ordering = ("-journal_entry__date", "-start")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.timesheet.submitted:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.timesheet.submitted:
            return ("start", "end")
        return self.readonly_fields


class JournalLeaderEntryInlineAdmin(admin.TabularInline):
    class form(forms.ModelForm):
        class Meta:
            model = JournalLeaderEntry
            fields = []

    model = JournalLeaderEntry
    ordering = ("journal_entry__date", "start")
    readonly_fields = ("date", "start", "end", "edit_link")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj:
            # obj may be Timesheet or JournalEntry
            # this inline is used in both JournalEntryAdmin and TimesheetAdmin
            try:
                entries = obj.leader_entries
            except AttributeError:
                entries = obj.journal_entries
            if entries.filter(timesheet__submitted=True).exists():
                return False
        return super().has_delete_permission(request, obj)

    def edit_link(self, obj):
        return '<a href="{url}" title="{title}" target="_blank">{edit}</a>'.format(
            url=reverse("admin:leprikon_journalleaderentry_change", args=[obj.id]),
            title=_("update entry"),
            edit=_("edit"),
        )

    edit_link.short_description = ""
    edit_link.allow_tags = True


@admin.register(JournalEntry)
class JournalEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form = JournalEntryAdminForm
    date_hierarchy = "date"
    list_display = ("id", "subject_name", "date", "start", "end", "duration", "agenda_html")
    list_filter = (
        ("subject__school_year", SchoolYearListFilter),
        ("subject", SubjectListFilter),
    )
    filter_horizontal = ("participants",)
    inlines = (JournalLeaderEntryInlineAdmin,)
    ordering = ("-date", "-start")
    readonly_fields = (
        "subject_name",
        "date",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj:
            if obj.affects_submitted_timesheets:
                return False
            else:
                return super().has_delete_permission(request, obj)
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:

            def delete_selected(model_admin, request, queryset):
                objs = [
                    journal_entry for journal_entry in queryset.all() if not journal_entry.affects_submitted_timesheets
                ]
                return admin.actions.delete_selected(model_admin, request, objs)

            actions["delete_selected"] = (delete_selected, *actions["delete_selected"][1:])
        return actions

    def subject_name(self, obj):
        return obj.subject.name

    subject_name.short_description = _("subject")
    subject_name.admin_order_field = "subject__name"

    def agenda_html(self, obj):
        return obj.agenda

    agenda_html.short_description = _("agenda")
    agenda_html.admin_order_field = "agenda"
    agenda_html.allow_tags = True
