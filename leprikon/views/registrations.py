from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from ..models import ClubRegistration, EventRegistration

from .generic import TemplateView


class RegistrationsView(TemplateView):
    registrations = True
    template_name = 'leprikon/registrations.html'

    def get_context_data(self, **kwargs):
        context = super(RegistrationsView, self).get_context_data(**kwargs)
        context['club_registrations'] = ClubRegistration.objects.filter(
            club__school_year   = self.request.school_year,
            participant__user   = self.request.user,
        )
        context['event_registrations'] = EventRegistration.objects.filter(
            event__school_year  = self.request.school_year,
            participant__user   = self.request.user,
        )
        return context


