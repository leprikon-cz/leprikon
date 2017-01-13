from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy as reverse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..forms.courses import (
    CourseFilterForm, CourseForm, CourseJournalEntryForm, CourseJournalLeaderEntryForm,
)
from ..forms.registrations import CourseRegistrationForm
from ..models.courses import (
    Course, CourseJournalEntry, CourseJournalLeaderEntry, CourseRegistration,
    CourseRegistrationRequest, CourseType,
)
from .generic import (
    ConfirmUpdateView, CreateView, DeleteView, DetailView, FilteredListView,
    PdfView, TemplateView, UpdateView,
)
from .registrations import RegistrationFormView


class CourseListView(FilteredListView):
    model               = Course
    form_class          = CourseFilterForm
    preview_template    = 'leprikon/course_preview.html'
    template_name       = 'leprikon/course_list.html'
    message_empty       = _('No courses matching given search parameters.')
    paginate_by         = 10

    def get_title(self):
        return _('{subject_type} in school year {school_year}').format(
            subject_type    = self.course_type,
            school_year     = self.request.school_year,
        )

    def dispatch(self, request, course_type, **kwargs):
        self.course_type = get_object_or_404(CourseType, slug=course_type)
        return super(CourseListView, self).dispatch(request, **kwargs)

    def get_form(self):
        return self.form_class(
            request     = self.request,
            course_types= [self.course_type],
            data        = self.request.GET,
        )

    def get_queryset(self):
        form = self.get_form()
        return form.get_queryset()



class CourseListMineView(CourseListView):
    def get_title(self):
        return _('My courses in school year {}').format(self.request.school_year)

    def get_queryset(self):
        return super(CourseListMineView, self).get_queryset().filter(leaders=self.request.leader)

    def dispatch(self, request, **kwargs):
        return super(ClubListView, self).dispatch(request, **kwargs)

    def get_form(self):
        return self.form_class(
            request     = self.request,
            data        = self.request.GET,
        )



class CourseAlternatingView(TemplateView):
    template_name = 'leprikon/course_alternating.html'

    def get_title(self):
        return _('Alternating in school year {}').format(self.request.school_year)

    def get_context_data(self, **kwargs):
        context = super(CourseAlternatingView, self).get_context_data(**kwargs)
        context['alternate_leader_entries'] = self.request.leader.get_alternate_leader_entries(self.request.school_year)
        return context



class CourseDetailView(DetailView):
    model = Course

    def get_queryset(self):
        qs = super(CourseDetailView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs.filter(course_type__slug=self.kwargs['course_type'])



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



class CourseUpdateView(UpdateView):
    model       = Course
    form_class  = CourseForm
    title       = _('Change course')

    def get_queryset(self):
        qs = super(CourseUpdateView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_message(self):
        return _('The course {} has been updated.').format(self.object)



class CourseJournalEntryCreateView(CreateView):
    model           = CourseJournalEntry
    form_class      = CourseJournalEntryForm
    template_name   = 'leprikon/coursejournalentry_form.html'
    title           = _('New journal entry')
    message         = _('The journal entry has been created.')

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            self.course = get_object_or_404(Course,
                id = int(kwargs.pop('course')),
            )
        else:
            self.course = get_object_or_404(Course,
                id = int(kwargs.pop('course')),
                leaders = self.request.leader,
            )
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
        if (self.request.user.is_staff
            or self.request.leader in obj.course.all_leaders + obj.all_alternates):
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
        if self.request.user.is_staff \
        or obj.timesheet.leader == self.request.leader \
        or self.request.leader in obj.course_entry.course.all_leaders:
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



class CourseRegistrationRequestFormView(UpdateView):
    back_url        = reverse('leprikon:registration_list')
    model           = CourseRegistrationRequest
    template_name   = 'leprikon/registration_request_form.html'
    message         = _('The registration request has been accepted.')
    fields          = ['contact']

    def get_title(self):
        return _('Registration request for course {}').format(self.kwargs['course'].name)

    def get_object(self, queryset=None):
        course = self.kwargs['subject']
        user = self.request.user if self.request.user.is_authenticated() else None
        req = None
        if user:
            try:
                req = CourseRegistrationRequest.objects.get(course=course, user=user)
            except CourseRegistrationRequest.DoesNotExist:
                pass
        if req is None:
            req = CourseRegistrationRequest()
            req.course = course
            req.user = user
        return req

    def get_instructions(self):
        if self.object.created:
            instructions = _(
                'Your request was already submitted. '
                'We will contact you, if someone cancels the registration. '
                'You may update the contact, if necessary.'
            )
        else:
            instructions = _(
                'The capacity of this course has already been filled. '
                'However, we may contact you, if someone cancels the registration. '
                'Please, leave your contact information in the form below.'
            )
        return '<p>{}</p>'.format(instructions)



class CourseRegistrationFormView(RegistrationFormView):
    model           = CourseRegistration
    form_class      = CourseRegistrationForm
    request_view    = CourseRegistrationRequestFormView

    def get_title(self):
        return _('Registration for course {}').format(self.subject.name)

    def dispatch(self, request, course_type, pk, *args, **kwargs):
        lookup_kwargs = {
            'course_type__slug':course_type,
            'id':               int(pk),
            'reg_active':       True,
        }
        if not self.request.user.is_staff:
            lookup_kwargs['public'] = True
        self.subject = get_object_or_404(Course, **lookup_kwargs)
        return super(CourseRegistrationFormView, self).dispatch(request, *args, **kwargs)



class CourseRegistrationConfirmView(DetailView):
    model = CourseRegistration
    template_name_suffix = '_confirm'



class CourseRegistrationPdfView(PdfView):
    model = CourseRegistration
    template_name_suffix = '_pdf'



class CourseRegistrationCancelView(ConfirmUpdateView):
    model = CourseRegistration
    title = _('Cancellation request')

    def get_queryset(self):
        return super(CourseRegistrationCancelView, self).get_queryset().filter(user=self.request.user)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()

