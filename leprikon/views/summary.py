from __future__ import unicode_literals

from datetime import date

from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from .generic import TemplateView


class SummaryView(TemplateView):
    summary = True
    template_name = 'leprikon/summary.html'

    def get_context_data(self, **kwargs):
        context = super(SummaryView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['payment_status'] = sum(
            reg.payment_statuses.partial
            for reg in CourseRegistration.objects.filter(
                course__school_year = self.request.school_year,
                user = self.request.user,
            )
        ) + sum(
            reg.payment_status
            for reg in EventRegistration.objects.filter(
                event__school_year = self.request.school_year,
                user = self.request.user,
            )
        )
        if self.request.leader:
            context['courses'] = self.request.leader.courses.filter(school_year=self.request.school_year)
            context['events'] = self.request.leader.events.filter(school_year=self.request.school_year)
            context['timesheets'] = self.request.leader.timesheets.filter(submitted=False, period__end__lte=date.today())
        context['new_messages'] = self.request.user.leprikon_messages.filter(viewed=None)
        return context

