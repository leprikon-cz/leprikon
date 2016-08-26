from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from collections import namedtuple
from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.events import EventPaymentsForm, EventPaymentsStatusForm
from ...models import EventPayment
from ...models.utils import PaymentStatus
from ...utils import comma_separated

from . import ReportBaseView


class ReportEventPaymentsView(ReportBaseView):
    form_class      = EventPaymentsForm
    template_name   = 'leprikon/reports/event_payments.html'
    title           = _('Event payments')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:reports')

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['payments'] = EventPayment.objects.filter(
            date__gte=context['date_start'],
            date__lte=context['date_end'],
        )
        context['sum'] = context['payments'].aggregate(Sum('amount'))['amount__sum']
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))



class ReportEventPaymentsStatusView(ReportBaseView):
    form_class      = EventPaymentsStatusForm
    template_name   = 'leprikon/reports/event_payments_status.html'
    title           = _('Event payments status')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:reports')

    EventPaymentsStatusSums = namedtuple('EventPaymentsStatusSums', ('registrations', 'status'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(event, context['date'])
            for event in self.request.school_year.events.all()
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
                    status       = registration.get_payment_status(self.date),
                )
                for registration in self.registrations
            ]

        @cached_property
        def status(self):
            return PaymentStatus(
                price       = sum(rs.status.price    for rs in self.registration_statuses),
                paid        = sum(rs.status.paid     for rs in self.registration_statuses),
                discount    = sum(rs.status.discount for rs in self.registration_statuses),
                explanation = comma_separated(rs.status.explanation for rs in self.registration_statuses),
            )

