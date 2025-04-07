from django import forms
from django.contrib import admin
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..forms.journals import JournalAdminForm, JournalEntryAdminForm, JournalLeaderEntryAdminForm
from ..models.activities import Activity
from ..models.journals import Journal, JournalEntry, JournalLeaderEntry, JournalTime
from ..utils import attributes
from .export import AdminExportMixin
from .filters import (
    ActivityListFilter,
    ActivityTypeListFilter,
    JournalListFilter,
    LeaderListFilter,
    SchoolYearListFilter,
)


class JournalTimeInlineAdmin(admin.TabularInline):
    model = JournalTime
    extra = 0


@admin.register(Journal)
class JournalAdmin(AdminExportMixin, admin.ModelAdmin):
    filter_horizontal = ("leaders", "participants")
    inlines = (JournalTimeInlineAdmin,)
    list_display = ("activity", "name", "get_times_list", "journal_links")
    list_filter = (
        ("activity__school_year", SchoolYearListFilter),
        ("activity__activity_type", ActivityTypeListFilter),
        ("leaders", LeaderListFilter),
        ("activity", ActivityListFilter),
    )
    raw_id_fields = ("activity",)

    # do not allow to add journals in admin
    def has_add_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if not object_id and request.method == "POST" and len(request.POST) == 3:
            return HttpResponseRedirect(f"{request.path}?activity=" + request.POST.get("activity", ""))
        else:
            return super().changeform_view(request, object_id, form_url, extra_context)

    def get_inline_instances(self, request, obj=None):
        return [] if hasattr(request, "hide_inlines") else super().get_inline_instances(request, obj)

    def get_form(self, request, obj, **kwargs):
        # get activity
        try:
            # first try request.POST (user may want to change activity)
            request.activity = Activity.objects.get(id=int(request.POST.get("activity")))
        except (Activity.DoesNotExist, TypeError, ValueError):
            if obj:
                # use activity from object
                request.activity = obj.activity
            else:
                # try to get activity from request.GET
                try:
                    request.activity = Activity.objects.get(
                        id=int(request.GET.get("activity")),
                    )
                except (Activity.DoesNotExist, TypeError, ValueError):
                    request.activity = None

        if request.activity:
            kwargs["form"] = type(
                "JournalAdminForm",
                (JournalAdminForm,),
                {"activity": request.activity},
            )
        else:
            kwargs["fields"] = ["activity"]
            request.hide_inlines = True

        return super().get_form(request, obj, **kwargs)

    def get_urls(self):
        return [
            path(
                "<int:journal_id>/journal/",
                self.admin_site.admin_view(self.journal),
                name="leprikon_journal_journal",
            ),
            path(
                "<int:journal_id>/journal-pdf/",
                self.admin_site.admin_view(self.journal_pdf),
                name="leprikon_journal_journal_pdf",
            ),
        ] + super().get_urls()

    def journal(self, request, journal_id):
        journal = self.get_object(request, journal_id)

        return render(
            request,
            "leprikon/journal_journal.html",
            {
                "journal": journal,
                "admin": True,
            },
        )

    def journal_pdf(self, request, journal_id):
        journal = self.get_object(request, journal_id)

        # create PDF response object
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(journal.get_pdf_filename("journal_pdf"))

        # write PDF to response
        return journal.write_pdf("journal_pdf", response)

    @attributes(short_description=_("journal"))
    def journal_links(self, obj):
        return mark_safe(
            "<br/>".join(
                (
                    format_html(
                        '<a href="{url}" title="{title}" target="_blank">{journal}</a>',
                        url=reverse("admin:leprikon_journal_journal", args=[obj.id]),
                        title=_("printable journal"),
                        journal=_("journal"),
                    ),
                    format_html(
                        '<a href="{url}" title="{title}" target="_blank">{participants}</a>',
                        url=reverse("admin:leprikon_journal_journal_pdf", args=[obj.id]),
                        title=_("printable list of participants"),
                        participants=_("participants"),
                    ),
                )
            )
        )


@admin.register(JournalLeaderEntry)
class JournalLeaderEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form = JournalLeaderEntryAdminForm
    list_display = ("timesheet", "date", "start", "end", "duration", "activity")
    list_filter = (
        ("timesheet__leader", LeaderListFilter),
        ("journal_entry__journal__activity", ActivityListFilter),
    )
    ordering = ("-journal_entry__date", "-start")

    def has_add_permission(self, request, obj=None):
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

    def has_add_permission(self, request, obj=None):
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

    @attributes(short_description="")
    def edit_link(self, obj):
        return mark_safe(
            '<a href="{url}" title="{title}" target="_blank">{edit}</a>'.format(
                url=reverse("admin:leprikon_journalleaderentry_change", args=[obj.id]),
                title=_("update entry"),
                edit=_("edit"),
            )
        )


@admin.register(JournalEntry)
class JournalEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form = JournalEntryAdminForm
    date_hierarchy = "date"
    list_display = ("id", "journal_name", "date", "start", "end", "duration", "agenda_html")
    list_filter = (
        ("journal__activity__school_year", SchoolYearListFilter),
        ("journal__leaders", LeaderListFilter),
        ("journal", JournalListFilter),
    )
    filter_horizontal = ("participants", "participants_instructed")
    inlines = (JournalLeaderEntryInlineAdmin,)
    ordering = ("-date", "-start")
    readonly_fields = (
        "journal_name",
        "date",
    )

    def has_add_permission(self, request, obj=None):
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

    @attributes(admin_order_field="journal", short_description=_("journal"))
    def journal_name(self, obj):
        return str(obj.journal)

    @attributes(admin_order_field="agenda", short_description=_("agenda"))
    def agenda_html(self, obj):
        return mark_safe(obj.agenda)
