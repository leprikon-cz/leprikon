from collections import namedtuple

from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.events import (
    EventPaymentsForm, EventPaymentsStatusForm, EventStatsForm,
)
from ...models.agegroup import AgeGroup
from ...models.citizenship import Citizenship
from ...models.events import Event, EventRegistration
from ...models.roles import Participant
from ...models.subjects import SubjectPayment, SubjectType
from . import ReportBaseView


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
            accounted__gte=context['date_start'],
            accounted__lte=context['date_end'],
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
                approved__lte=self.date,
            ))

        RegPaymentStatus = namedtuple('RegPaymentStatus', ('registration', 'status'))

        @cached_property
        def registration_statuses(self):
            return [
                registration_status for registration_status in (
                    self.RegPaymentStatus(
                        registration = registration,
                        status       = registration.eventregistration.get_payment_status(self.date),
                    )
                    for registration in self.registrations
                ) if registration_status.status.receivable
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)



class ReportEventStatsView(ReportBaseView):
    form_class      = EventStatsForm
    template_name   = 'leprikon/reports/event_stats.html'
    title           = _('Event statistics')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    ReportItem      = namedtuple('ReportItem', ('age_group', 'all', 'boys', 'girls', 'citizenships'))

    def form_valid(self, form):
        d               = form.cleaned_data['date']
        paid_only       = form.cleaned_data['paid_only']
        context         = form.cleaned_data
        context['form'] = form

        events = Event.objects.filter(school_year=self.request.school_year)
        context['events_count'] = events.count()

        registrations = EventRegistration.objects.filter(subject__in=events, approved__lte=d).exclude(canceled__lte=d)
        if paid_only:
            registrations = [
                reg for reg in registrations
                if reg.get_payment_status(d).balance >= 0
            ]
        else:
            registrations = list(registrations)

        citizenships = list(Citizenship.objects.all())
        context['citizenships'] = citizenships

        context['registrations_counts'] = self.ReportItem(
            age_group=None,
            all=len(registrations),
            boys=len([r for r in registrations if r.participant_gender == Participant.MALE]),
            girls=len([r for r in registrations if r.participant_gender == Participant.FEMALE]),
            citizenships=[
                len([r for r in registrations if r.participant_citizenship_id == citizenship.id])
                for citizenship in citizenships
            ]
        )
        context['registrations_counts_by_age_groups'] = []
        for age_group in AgeGroup.objects.all():
            regs = [r for r in registrations if r.participant_age_group == age_group]
            context['registrations_counts_by_age_groups'].append(self.ReportItem(
                age_group=age_group,
                all=len(regs),
                boys=len([r for r in regs if r.participant_gender == Participant.MALE]),
                girls=len([r for r in regs if r.participant_gender == Participant.FEMALE]),
                citizenships=[
                    len([r for r in regs if r.participant_citizenship_id == citizenship.id])
                    for citizenship in citizenships
                ]
            ))

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
