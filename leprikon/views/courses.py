from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..forms.courses import (
    CourseJournalEntryForm, CourseJournalLeaderEntryForm,
)
from ..models.courses import (
    Course, CourseJournalEntry, CourseJournalLeaderEntry,
)
from .generic import (
    CreateView, DeleteView, DetailView, TemplateView, UpdateView,
)


class CourseAlternatingView(TemplateView):
    template_name = 'leprikon/course_alternating.html'

    def get_title(self):
        return _('Alternating in school year {}').format(self.request.school_year)

    def get_context_data(self, **kwargs):
        context = super(CourseAlternatingView, self).get_context_data(**kwargs)
        context['alternate_leader_entries'] = self.request.leader.get_alternate_leader_entries(self.request.school_year)
        return context



class CourseRegistrationsView(DetailView):
    model = Course
    template_name_suffix = '_registrations'

    def get_queryset(self):
        qs = super(CourseRegistrationsView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs



class CourseJournalView(DetailView):
    model = Course
    template_name_suffix = '_journal'

    def get_queryset(self):
        qs = super(CourseJournalView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs



class CourseJournalEntryCreateView(CreateView):
    model           = CourseJournalEntry
    form_class      = CourseJournalEntryForm
    template_name   = 'leprikon/coursejournalentry_form.html'
    title           = _('New journal entry')
    message         = _('The journal entry has been created.')

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            self.course = get_object_or_404(Course, id=int(kwargs.pop('course')))
        else:
            self.course = get_object_or_404(Course, id=int(kwargs.pop('course')), leaders=self.request.leader)
        return super(CourseJournalEntryCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CourseJournalEntryCreateView, self).get_form_kwargs()
        kwargs['course'] = self.course
        return kwargs



class CourseJournalEntryUpdateView(UpdateView):
    model           = CourseJournalEntry
    form_class      = CourseJournalEntryForm
    template_name   = 'leprikon/coursejournalentry_form.html'
    title           = _('Change journal entry')
    message         = _('The journal entry has been updated.')

    def get_object(self):
        obj = super(CourseJournalEntryUpdateView, self).get_object()
        if (self.request.user.is_staff or self.request.leader in obj.course.all_leaders + obj.all_alternates):
            return obj
        else:
            raise Http404()



class CourseJournalEntryDeleteView(DeleteView):
    model   = CourseJournalEntry
    title   = _('Delete journal entry')
    message = _('The journal entry has been deleted.')

    def get_queryset(self):
        return super(CourseJournalEntryDeleteView, self).get_queryset().filter(
            course__leaders = self.request.leader,
        )

    def get_object(self):
        obj = super(CourseJournalEntryDeleteView, self).get_object()
        if obj.timesheets.filter(submitted = True).exists():
            raise Http404()
        return obj

    def get_question(self):
        return _('Do You really want to delete course journal entry?')



class CourseJournalLeaderEntryUpdateView(UpdateView):
    model           = CourseJournalLeaderEntry
    form_class      = CourseJournalLeaderEntryForm
    template_name   = 'leprikon/coursejournalleaderentry_form.html'
    title           = _('Change timesheet entry')
    message         = _('The timesheet entry has been updated.')

    def get_object(self):
        obj = super(CourseJournalLeaderEntryUpdateView, self).get_object()
        if (
            self.request.user.is_staff or obj.timesheet.leader == self.request.leader or
            self.request.leader in obj.course_entry.course.all_leaders
        ):
            return obj
        else:
            raise Http404()



class CourseJournalLeaderEntryDeleteView(DeleteView):
    model   = CourseJournalLeaderEntry
    title   = _('Delete timesheet entry')
    message = _('The timesheet entry has been deleted.')

    def get_queryset(self):
        return super(CourseJournalLeaderEntryDeleteView, self).get_queryset().filter(
            timesheet__leader = self.request.leader,
            timesheet__submitted = False,
        )

    def get_question(self):
        return _('Do You really want to delete timesheet entry?')
