from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ..models import ClubRegistration, EventRegistration

from .generic import CreateView, TemplateView


class RegistrationsView(TemplateView):
    registrations = True
    template_name = 'leprikon/registrations.html'

    def get_context_data(self, **kwargs):
        context = super(RegistrationsView, self).get_context_data(**kwargs)
        context['clubregistrations'] = ClubRegistration.objects.filter(
            club__school_year   = self.request.school_year,
            user   = self.request.user,
        )
        context['eventregistrations'] = EventRegistration.objects.filter(
            event__school_year  = self.request.school_year,
            user   = self.request.user,
        )
        return context



class RegistrationFormView(CreateView):
    back_url        = reverse('leprikon:registrations')
    submit_label    = _('Submit registration')
    template_name   = 'leprikon/registration_form.html'
    message         = _('The registration has been accepted.')

    def dispatch(self, request, *args, **kwargs):
        self.request.school_year = self.subject.school_year
        if self.subject.max_count and self.subject.registrations.count() >= self.subject.max_count:
            return self.request_view.as_view()(request, subject=self.subject)
        return super(RegistrationFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs  = super(RegistrationFormView, self).get_form_kwargs()
        kwargs['subject'] = self.subject
        kwargs['user'] = self.request.user.is_authenticated() and self.request.user or None
        return kwargs

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated():
            kwargs['participants'] = self.request.user.leprikon_participants.exclude(
                birth_num__in=[reg.participant_birth_num for reg in self.subject.all_registrations]
            )
            kwargs['parents'] = self.request.user.leprikon_parents.all()
        else:
            kwargs['participants'] = []
            kwargs['parents'] = []
        return super(RegistrationFormView, self).get_context_data(**kwargs)

    #def form_valid(self, form):
    #    response = super(ClubRegistrationFormView, self).form_valid(form)
    #    if self.request.user.is_anonymous() and form.user.is_active:
    #        form.user.backend = 'django.contrib.auth.backends.ModelBackend'
    #        login(self.request, form.user)
    #    return response


