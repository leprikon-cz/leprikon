from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..forms.journals import JournalEntryForm, JournalLeaderEntryForm
from ..models.journals import JournalEntry, JournalLeaderEntry, Subject
from .generic import CreateView, DeleteView, DetailView, TemplateView, UpdateView


class AlternatingView(TemplateView):
    template_name = "leprikon/alternating.html"

    def get_title(self):
        return _("Alternating in school year {}").format(self.request.school_year)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["alternate_leader_entries"] = self.request.leader.get_alternate_leader_entries(self.request.school_year)
        return context


class JournalView(DetailView):
    model = Subject
    template_name_suffix = "_journal"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs


class JournalEntryCreateView(CreateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = "leprikon/journalentry_form.html"
    title = _("New journal entry")
    message = _("The journal entry has been created.")

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            self.subject = get_object_or_404(Subject, id=int(kwargs.pop("subject")))
        else:
            self.subject = get_object_or_404(Subject, id=int(kwargs.pop("subject")), leaders=self.request.leader)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["subject"] = self.subject
        return kwargs


class JournalEntryUpdateView(UpdateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = "leprikon/journalentry_form.html"
    title = _("Change journal entry")
    message = _("The journal entry has been updated.")

    def get_object(self):
        obj = super().get_object()
        if self.request.user.is_staff or self.request.leader in obj.subject.all_leaders + obj.all_alternates:
            return obj
        else:
            raise Http404()


class JournalEntryDeleteView(DeleteView):
    model = JournalEntry
    title = _("Delete journal entry")
    message = _("The journal entry has been deleted.")

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(subject__leaders=self.request.leader)
        return qs

    def get_object(self):
        obj = super().get_object()
        if obj.affects_submitted_timesheets:
            raise Http404()
        return obj

    def get_question(self):
        return _("Do You really want to delete journal entry?")


class JournalLeaderEntryUpdateView(UpdateView):
    model = JournalLeaderEntry
    form_class = JournalLeaderEntryForm
    template_name = "leprikon/journalleaderentry_form.html"
    title = _("Change timesheet entry")
    message = _("The timesheet entry has been updated.")

    def get_object(self):
        obj = super().get_object()
        if (
            self.request.user.is_staff
            or obj.timesheet.leader == self.request.leader
            or self.request.leader in obj.journal_entry.subject.all_leaders
        ):
            return obj
        else:
            raise Http404()


class JournalLeaderEntryDeleteView(DeleteView):
    model = JournalLeaderEntry
    title = _("Delete timesheet entry")
    message = _("The timesheet entry has been deleted.")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                timesheet__leader=self.request.leader,
                timesheet__submitted=False,
            )
        )

    def get_question(self):
        return _("Do You really want to delete timesheet entry?")
