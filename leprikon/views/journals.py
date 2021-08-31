from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls.base import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ..forms.journals import JournalEntryForm, JournalForm, JournalLeaderEntryForm
from ..models.journals import Journal, JournalEntry, JournalLeaderEntry, Subject
from .generic import CreateView, DeleteView, DetailView, TemplateView, UpdateView


class AlternatingView(TemplateView):
    template_name = "leprikon/alternating.html"

    def get_title(self):
        return _("Alternating in school year {}").format(self.request.school_year)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["alternate_leader_entries"] = self.request.leader.get_alternate_leader_entries(self.request.school_year)
        return context


class JournalQuerySetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs


class JournalView(JournalQuerySetMixin, DetailView):
    model = Journal
    template_name_suffix = "_journal"


class JournalCreateView(CreateView):
    model = Journal
    form_class = JournalForm
    template_name = "leprikon/journal_form.html"
    title = _("New journal")

    def dispatch(self, request, subject):
        kwargs = {"id": subject}
        if not self.request.user.is_staff:
            kwargs["leaders"] = self.request.leader
        self.subject = get_object_or_404(Subject, **kwargs)
        self.success_url = reverse("leprikon:subject_journals", args=(self.subject.subject_type.slug, self.subject.id))
        return super().dispatch(request)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["subject"] = self.subject
        return kwargs

    def get_message(self):
        return _("New journal {} has been created.").format(self.object)


class JournalUpdateView(JournalQuerySetMixin, UpdateView):
    model = Journal
    form_class = JournalForm
    success_url = reverse("leprikon:summary")
    template_name = "leprikon/journal_form.html"
    title = _("Change journal")


class JournalDeleteView(DeleteView):
    model = Journal
    title = _("Delete journal")
    message = _("Journal has been deleted.")

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(subject__leaders=self.request.leader)
        return qs

    def get_object(self):
        obj = super().get_object()
        if obj.all_journal_entries:
            raise Http404()
        return obj

    def get_question(self):
        return _("Do You really want to delete the journal {}?").format(self.object)


class JournalEntryCreateView(CreateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = "leprikon/journalentry_form.html"
    title = _("New journal entry")
    message = _("The journal entry has been created.")

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            self.journal = get_object_or_404(Journal, id=int(kwargs.pop("journal")))
        else:
            self.journal = get_object_or_404(Journal, id=int(kwargs.pop("journal")), leaders=self.request.leader)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["journal"] = self.journal
        return kwargs


class JournalEntryUpdateView(UpdateView):
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = "leprikon/journalentry_form.html"
    title = _("Change journal entry")
    message = _("The journal entry has been updated.")

    def get_object(self):
        obj = super().get_object()
        if self.request.user.is_staff or self.request.leader in obj.journal.all_leaders + obj.all_alternates:
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
            qs = qs.filter(journal__leaders=self.request.leader)
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
            or self.request.leader in obj.journal_entry.journal.all_leaders
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
