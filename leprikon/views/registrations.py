from __future__ import unicode_literals

from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from .generic import TemplateView


class RegistrationsListView(TemplateView):
    registrations = True
    template_name = 'leprikon/registrations.html'

    def get_context_data(self, **kwargs):
        context = super(RegistrationsListView, self).get_context_data(**kwargs)
        context['courseregistrations'] = CourseRegistration.objects.filter(
            subject__school_year   = self.request.school_year,
            user   = self.request.user,
        )
        context['eventregistrations'] = EventRegistration.objects.filter(
            subject__school_year  = self.request.school_year,
            user   = self.request.user,
        )
        return context
