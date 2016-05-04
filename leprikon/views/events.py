from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.auth import login
from django.core.urlresolvers import reverse_lazy as reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import SingleObjectMixin

from ..forms.events import EventForm, EventFilterForm
from ..forms.registrations import EventRegistrationForm
from ..models import Event, EventType, EventRegistration

from .generic import FilteredListView, DetailView, CreateView, UpdateView, ConfirmUpdateView, PdfView


class EventListView(FilteredListView):
    model               = Event
    form_class          = EventFilterForm
    preview_template    = 'leprikon/event_preview.html'
    template_name       = 'leprikon/event_list.html'
    message_empty       = _('No events matching given filter.')
    paginate_by         = 10

    def get_title(self):
        return _('{event_type} in school year {school_year}').format(
            event_type  = self.event_type,
            school_year = self.request.school_year,
        )

    def dispatch(self, request, event_type, **kwargs):
        self.event_type = get_object_or_404(EventType, slug=event_type)
        return super(EventListView, self).dispatch(request, **kwargs)

    def get_form(self):
        return self.form_class(
            request     = self.request,
            event_types = [self.event_type],
            data        = self.request.GET,
        )

    def get_queryset(self):
        form = self.get_form()
        return form.get_queryset()



class EventListMineView(EventListView):
    def get_title(self):
        return _('My events in school year {}').format(self.request.school_year)

    def dispatch(self, request, **kwargs):
        return super(EventListView, self).dispatch(request, **kwargs)

    def get_form(self):
        return self.form_class(
            request     = self.request,
            data        = self.request.GET,
        )

    def get_queryset(self):
        return super(EventListMineView, self).get_queryset().filter(leaders=self.request.leader)



class EventDetailView(DetailView):
    model = Event

    def get_queryset(self):
        qs = super(EventDetailView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs.filter(event_type__slug=self.kwargs['event_type'])



class EventDetailRedirectView(RedirectView, SingleObjectMixin):
    model = Event

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
    title       = _('Change event')

    def get_queryset(self):
        qs = super(EventUpdateView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_message(self):
        return _('The event {} has been updated.').format(self.object)



class EventRegistrationFormView(CreateView):
    back_url        = reverse('leprikon:registrations')
    model           = EventRegistration
    form_class      = EventRegistrationForm
    template_name   = 'leprikon/registration_form.html'
    message         = _('The registration has been accepted.')

    def get_title(self):
        return _('Registration for event {}').format(self.event.name)

    def dispatch(self, request, event_type, pk, *args, **kwargs):
        event_kwargs = {
            'id':               int(pk),
            'event_type__slug': event_type,
            'school_year':      self.request.school_year,
            'reg_active':       True,
        }
        if not self.request.user.is_staff:
            event_kwargs['public'] = True
        self.event = get_object_or_404(Event, **event_kwargs)
        return super(EventRegistrationFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs  = super(EventRegistrationFormView, self).get_form_kwargs()
        kwargs['event'] = self.event
        kwargs['user']  = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super(EventRegistrationFormView, self).form_valid(form)
        if self.request.user.is_anonymous() and form.user.is_active:
            form.user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(self.request, form.user)
        return response



class EventRegistrationConfirmView(DetailView):
    model = EventRegistration
    template_name_suffix = '_confirm'



class EventRegistrationPdfView(PdfView):
    model = EventRegistration
    template_name_suffix = '_pdf'



class EventRegistrationCancelView(ConfirmUpdateView):
    model = EventRegistration
    title = _('Cancellation request')

    def get_queryset(self):
        return super(EventRegistrationCancelView, self).get_queryset().filter(participant__user=self.request.user)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()


