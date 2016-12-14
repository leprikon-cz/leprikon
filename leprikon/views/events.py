from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy as reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import SingleObjectMixin

from ..forms.events import EventFilterForm, EventForm
from ..forms.registrations import EventRegistrationForm
from ..models.events import (
    Event, EventRegistration, EventRegistrationRequest, EventType,
)
from .generic import (
    ConfirmUpdateView, DetailView, FilteredListView, PdfView, UpdateView,
)
from .registrations import RegistrationFormView


class EventListView(FilteredListView):
    model               = Event
    form_class          = EventFilterForm
    preview_template    = 'leprikon/event_preview.html'
    template_name       = 'leprikon/event_list.html'
    message_empty       = _('No events matching given search parameters.')
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

    def get_queryset(self):
        return super(EventListMineView, self).get_queryset().filter(leaders=self.request.leader)

    def dispatch(self, request, **kwargs):
        return super(EventListView, self).dispatch(request, **kwargs)

    def get_form(self):
        return self.form_class(
            request     = self.request,
            data        = self.request.GET,
        )



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



class EventRegistrationsView(DetailView):
    model = Event
    template_name_suffix = '_registrations'

    def get_queryset(self):
        qs = super(EventRegistrationsView, self).get_queryset()
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



class EventRegistrationRequestFormView(UpdateView):
    back_url        = reverse('leprikon:registration_list')
    model           = EventRegistrationRequest
    template_name   = 'leprikon/registration_request_form.html'
    message         = _('The registration request has been accepted.')
    fields          = ['contact']

    def get_title(self):
        return _('Registration request for event {}').format(self.kwargs['event'].name)

    def get_object(self, queryset=None):
        event = self.kwargs['subject']
        user = self.request.user if self.request.user.is_authenticated() else None
        req = None
        if user:
            try:
                req = EventRegistrationRequest.objects.get(event=event, user=user)
            except EventRegistrationRequest.DoesNotExist:
                pass
        if req is None:
            req = EventRegistrationRequest()
            req.event = event
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
                'The capacity of this event has already been filled. '
                'However, we may contact you, if someone cancels the registration. '
                'Please, leave your contact information in the form below.'
            )
        return '<p>{}</p>'.format(instructions)



class EventRegistrationFormView(RegistrationFormView):
    model           = EventRegistration
    form_class      = EventRegistrationForm
    request_view    = EventRegistrationRequestFormView

    def get_title(self):
        return _('Registration for event {}').format(self.subject.name)

    def dispatch(self, request, event_type, pk, *args, **kwargs):
        lookup_kwargs = {
            'event_type__slug': event_type,
            'id':               int(pk),
            'reg_active':       True,
        }
        if not self.request.user.is_staff:
            lookup_kwargs['public'] = True
        self.subject = get_object_or_404(Event, **lookup_kwargs)
        return super(EventRegistrationFormView, self).dispatch(request, *args, **kwargs)



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
        return super(EventRegistrationCancelView, self).get_queryset().filter(user=self.request.user)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()

