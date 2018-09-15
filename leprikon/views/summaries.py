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
                subject__school_year = self.request.school_year,
                user = self.request.user,
            )
        ) + sum(
            reg.payment_status
            for reg in EventRegistration.objects.filter(
                subject__school_year = self.request.school_year,
                user = self.request.user,
            )
        )
        context['new_messages'] = self.request.user.leprikon_messages.filter(viewed=None)
        return context



class LeaderSummaryView(TemplateView):
    summary = True
    template_name = 'leprikon/leader_summary.html'

    def get_context_data(self, **kwargs):
        context = super(LeaderSummaryView, self).get_context_data(**kwargs)
        context['subjects'] = self.request.leader.subjects.filter(school_year=self.request.school_year)
        context['timesheets'] = self.request.leader.timesheets.filter(submitted=False, period__end__lte=date.today())
        return context
