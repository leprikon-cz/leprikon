from django.http import Http404
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from ..forms.timesheets import TimesheetEntryForm
from ..models.timesheets import Timesheet, TimesheetEntry
from .generic import ConfirmUpdateView, CreateView, DeleteView, DetailView, ListView, UpdateView


class TimesheetListView(ListView):
    model = Timesheet
    preview_template = "leprikon/timesheet_preview.html"
    paginate_by = 6
    add_label = _("add entry")
    add_url = reverse_lazy("leprikon:timesheetentry_create")

    def get_title(self):
        return _("Timesheets")

    def get_queryset(self):
        return super().get_queryset().filter(leader=self.request.leader)


class TimesheetDetailView(DetailView):
    model = Timesheet

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leader=self.request.leader)
        return qs


class TimesheetSubmitView(ConfirmUpdateView):
    model = Timesheet
    title = _("Submit timesheet")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                leader=self.request.leader,
                submitted=False,
            )
        )

    def get_question(self):
        return _(
            "Are you sure You want to submit the timesheet now? "
            "You won't be able to edit the entries for {} any more."
        ).format(self.object.period.name)

    def get_message(self):
        return _("The timesheet for () has been submitted.").format(self.object.period.name)

    def confirmed(self):
        self.object.submitted = True
        self.object.save()


class TimesheetEntryCreateView(CreateView):
    model = TimesheetEntry
    form_class = TimesheetEntryForm
    template_name = "leprikon/timesheetentry_form.html"
    title = _("New timesheet entry")
    message = _("New timesheet entry has been created.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["leader"] = self.request.leader
        return kwargs


class TimesheetEntryUpdateView(UpdateView):
    model = TimesheetEntry
    form_class = TimesheetEntryForm
    template_name = "leprikon/timesheetentry_form.html"
    title = _("Change timesheet entry")
    message = _("The timesheet entry has been updated.")

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(timesheet__leader=self.request.leader)
        return qs


class TimesheetEntryDeleteView(DeleteView):
    model = TimesheetEntry
    title = _("Delete timesheet entry")
    message = _("The timesheet entry has been deleted.")

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(timesheet__leader=self.request.leader)
        return qs

    def get_object(self):
        obj = super().get_object()
        if obj.timesheet.submitted:
            raise Http404()
        return obj

    def get_question(self):
        return _("Do You really want to delete timesheet entry?")
