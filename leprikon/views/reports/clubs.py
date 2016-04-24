from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from collections import namedtuple
from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.clubs import ClubPaymentsForm, ClubPaymentsStatusForm
from ...models import ClubPayment

from ..generic import FormView


class ReportClubPaymentsView(FormView):
    form_class      = ClubPaymentsForm
    template_name   = 'leprikon/reports/club_payments.html'
    title           = _('Club payments')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:reports')

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['payments'] = ClubPayment.objects.filter(
            date__gte=context['date_start'],
            date__lte=context['date_end'],
        )
        context['sum'] = context['payments'].aggregate(Sum('amount'))['amount__sum']
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))



class ReportClubPaymentsStatusView(FormView):
    form_class      = ClubPaymentsStatusForm
    template_name   = 'leprikon/reports/club_payments_status.html'
    title           = _('Club payments status')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:reports')

    ClubPaymentsStatusSums = namedtuple('ClubPaymentsStatusSums', ('registrations', 'partial', 'total'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(club, context['date'])
            for club in self.request.school_year.clubs.all()
        ]
        context['sum'] = self.ClubPaymentsStatusSums(
            registrations   = sum(len(r.registrations)  for r in context['reports']),
            partial         = sum(r.partial             for r in context['reports']),
            total           = sum(r.total               for r in context['reports']),
        )
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

    class Report:
        def __init__(self, club, d):
            self.club = club
            self.date = d

        @cached_property
        def periods(self):
            return list(self.club.periods.filter(start__lte=self.date))

        @cached_property
        def registrations(self):
            return list(self.club.registrations.filter(
                created__lte=self.date,
            ))

        RegPaymentStatuses = namedtuple('RegPaymentStatuses', ('registration', 'statuses'))

        @cached_property
        def registration_statuses(self):
            return [
                self.RegPaymentStatuses(
                    registration = registration,
                    statuses     = registration.get_payment_statuses(self.date),
                )
                for registration in self.registrations
            ]

        @cached_property
        def partial(self):
            return sum(rs.statuses.partial for rs in self.registration_statuses)

        @cached_property
        def total(self):
            return sum(rs.statuses.total for rs in self.registration_statuses)

