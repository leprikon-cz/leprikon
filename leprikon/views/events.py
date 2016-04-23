from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.auth import login
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import SingleObjectMixin

from ..forms.events import EventForm, EventFilterForm, EventRegistrationForm, EventRegistrationPublicForm
from ..models import Event, EventType, EventRegistration, Participant

from .generic import FilteredListView, DetailView, CreateView, UpdateView, ConfirmUpdateView, PdfView


class EventListView(FilteredListView):
    model               = Event
    form_class          = EventFilterForm
    preview_template    = 'leprikon/event_preview.html'
    template_name       = 'leprikon/event_list.html'
    message_empty       = _('No events matching given filter.')
    paginate_by         = 10

    def get_title(self):
        if self.event_type:
            return _('{event_type} in school year {school_year}').format(
                event_type  = self.event_type,
                school_year = self.request.school_year,
            )
        else:
            return _('Events in school year {}').format(self.request.school_year)

    def dispatch(self, request, *args, **kwargs):
        if 'event_type' in kwargs:
            self.event_type = get_object_or_404(EventType, slug=kwargs.pop('event_type'))
        else:
            self.event_type = None
        return super(EventListView, self).dispatch(request, *args, **kwargs)

    def get_form(self):
        return self.form_class(self.request, self.event_type, data=self.request.GET)

    def get_queryset(self):
        qs = super(EventListView, self).get_queryset()
        qs = qs.filter(school_year=self.request.school_year)
        if self.event_type:
            qs = qs.filter(event_type = self.event_type)
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        form = self.get_form()
        if form.is_valid():
            qs = form.filter_queryset(self.request, qs)
        return qs



class EventListMineView(EventListView):
    def get_queryset(self):
        return super(EventListMineView, self).get_queryset().filter(leaders=self.request.leader)

    def get_title(self):
        return _('My events in school year {}').format(self.request.school_year)



class EventDetailView(DetailView):
    model   = Event

    def get_queryset(self):
        qs = super(EventDetailView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs.filter(event_type__slug=self.kwargs['event_type'])



class EventDetailRedirectView(RedirectView, SingleObjectMixin):
    model   = Event

    def get_queryset(self):
        qs = super(EventDetailRedirectView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs

    def get_redirect_url(self, *args, **kwargs):
        url = self.get_object().get_absolute_url()

        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            url = "%s?%s" % (url, args)
        return url



class EventParticipantsView(DetailView):
    model = Event
    template_name_suffix = '_participants'

    def get_queryset(self):
        qs = super(EventParticipantsView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs



class EventUpdateView(UpdateView):
    model       = Event
    form_class  = EventForm
    title = _('Change event')

    def get_queryset(self):
        qs = super(EventUpdateView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_message(self, form):
        return _('The event {} has been updated.').format(self.object)



class EventRegistrationPublicFormView(CreateView):
    model           = EventRegistration
    form_class      = EventRegistrationPublicForm
    template_name   = 'leprikon/registration_form.html'

    def get_title(self):
        return _('Registration for event {}').format(self.event.name)

    def dispatch(self, request, *args, **kwargs):
        event_kwargs = {
            'id':           int(kwargs.pop('event')),
            'school_year':  self.request.school_year,
            'reg_active':   True,
        }
        if not self.request.user.is_staff:
            event_kwargs['public'] = True
        self.event = get_object_or_404(Event, **event_kwargs)
        if self.request.user.is_authenticated() and not self.request.toolbar.use_draft:
            return HttpResponseRedirect(reverse('leprikon:event_detail', args=(self.event.event_type.slug, self.event.id)))
        return super(EventRegistrationPublicFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs  = super(EventRegistrationPublicFormView, self).get_form_kwargs()
        kwargs['event'] = self.event
        return kwargs

    def form_valid(self, form):
        response = super(EventRegistrationPublicFormView, self).form_valid(form)
        user = form.instance.participant.user
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(self.request, user)
        return response

    def get_message(self, form):
        return _('The registration has been accepted.')



class EventRegistrationFormView(CreateView):
    model       = EventRegistration
    form_class  = EventRegistrationForm

    def get_title(self):
        return _('Registration for event {}').format(self.event.name)

    def dispatch(self, request, *args, **kwargs):
        event_kwargs = {
            'id':           int(kwargs.pop('event')),
            'school_year':  self.request.school_year,
            'reg_active':   True,
        }
        if not self.request.user.is_staff:
            event_kwargs['public'] = True
        self.event = get_object_or_404(Event, **event_kwargs)
        self.participant = get_object_or_404(Participant,
            user    = self.request.user,
            id      = int(kwargs.pop('participant')),
        )
        # user may get back to this page after successful registration
        if self.event.registrations.filter(participant=self.participant).exists():
            return HttpResponseRedirect(reverse('leprikon:summary'))
        return super(EventRegistrationFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs  = super(EventRegistrationFormView, self).get_form_kwargs()
        kwargs['event']         = self.event
        kwargs['participant']   = self.participant
        return kwargs

    def get_message(self, form):
        return _('The registration has been accepted.')



class EventRegistrationConfirmView(DetailView):
    model = EventRegistration
    template_name_suffix = '_confirm'



class EventRegistrationPdfView(PdfView):
    model = EventRegistration
    template_name_suffix = '_pdf'



class EventRegistrationCancelView(ConfirmUpdateView):
    model   = EventRegistration
    title   = _('Cancellation request')

    def get_queryset(self):
        return super(EventRegistrationCancelView, self).get_queryset().filter(participant__user=self.request.user)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self, form):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()


