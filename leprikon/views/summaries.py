from datetime import date

from django.db.models import F

from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from ..models.orderables import OrderableRegistration
from ..models.utils import PaymentStatusSum
from .generic import TemplateView


class SummaryView(TemplateView):
    summary = True
    template_name = "leprikon/summary.html"

    def get_context_data(self, **kwargs):
        payment_status = PaymentStatusSum(0, 0, 0, 0, 0, 0)
        overpaid_registrations = []
        for Registration in (CourseRegistration, EventRegistration, OrderableRegistration):
            for registration in (
                Registration.objects.filter(user=self.request.user)
                .annotate(
                    refund_bank_account=F("refund_request__bank_account"),
                )
                .iterator()
            ):
                payment_status += registration.payment_status
                if registration.payment_status.overpaid:
                    overpaid_registrations.append(registration)
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        context["payment_status"] = payment_status
        context["overpaid_registrations"] = overpaid_registrations
        context["new_messages"] = self.request.user.leprikon_messages.filter(viewed=None)
        return context


class LeaderSummaryView(TemplateView):
    summary = True
    template_name = "leprikon/leader_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subjects"] = self.request.leader.subjects.filter(school_year=self.request.school_year)
        context["timesheets"] = self.request.leader.timesheets.filter(submitted=False, period__end__lte=date.today())
        return context
