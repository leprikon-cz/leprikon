from __future__ import unicode_literals

from collections import namedtuple

from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from . import ReportBaseView
from ...forms.reports.events import EventPaymentsForm, EventPaymentsStatusForm
from ...models.events import Event
from ...models.subjects import SubjectPayment, SubjectType
from ...models.utils import PaymentStatus


class ReportEventPaymentsView(ReportBaseView):
    form_class      = EventPaymentsForm
    template_name   = 'leprikon/reports/event_payments.html'
    title           = _('Event payments')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['payments'] = SubjectPayment.objects.filter(
            registration__subject__subject_type__subject_type=SubjectType.EVENT,
            created__gte=context['date_start'],
            created__lte=context['date_end'],
        )
        context['sum'] = context['payments'].aggregate(Sum('amount'))['amount__sum']
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))



class ReportEventPaymentsStatusView(ReportBaseView):
    form_class      = EventPaymentsStatusForm
    template_name   = 'leprikon/reports/event_payments_status.html'
    title           = _('Event payments status')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    EventPaymentsStatusSums = namedtuple('EventPaymentsStatusSums', ('registrations', 'status'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(event, context['date'])
            for event in Event.objects.filter(school_year=self.request.school_year)
        ]
        context['sum'] = self.EventPaymentsStatusSums(
            registrations   = sum(len(r.registrations)  for r in context['reports']),
            status          = sum(r.status              for r in context['reports']),
        )
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

    class Report:
        def __init__(self, event, d):
            self.event = event
            self.date = d

        @cached_property
        def registrations(self):
            return list(self.event.registrations.filter(
                created__lte=self.date,
            ))

        RegPaymentStatus = namedtuple('RegPaymentStatus', ('registration', 'status'))

        @cached_property
        def registration_statuses(self):
            return [
                self.RegPaymentStatus(
                    registration = registration,
                    status       = registration.eventregistration.get_payment_status(self.date),
                )
                for registration in self.registrations
            ]

        @cached_property
        def status(self):
            return PaymentStatus(
                price       = sum(rs.status.price    for rs in self.registration_statuses),
                paid        = sum(rs.status.paid     for rs in self.registration_statuses),
                discount    = sum(rs.status.discount for rs in self.registration_statuses),
            )
