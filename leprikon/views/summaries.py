from datetime import date

from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from ..models.orderables import OrderableRegistration
from ..models.utils import PaymentStatusSum
from .generic import TemplateView


class SummaryView(TemplateView):
    summary = True
    template_name = 'leprikon/summary.html'

    def get_context_data(self, **kwargs):
        context = super(SummaryView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['payment_status'] = sum(
            sum(
                reg.payment_status
                for reg in Model.objects.filter(user=self.request.user, approved__isnull=False)
            ) for Model in (
                CourseRegistration,
                EventRegistration,
                OrderableRegistration,
            )
        ) + PaymentStatusSum(0, 0, 0, 0, 0, 0)
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
