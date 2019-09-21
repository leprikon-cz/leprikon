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
from ...models.events import Event
from ...models.roles import Participant
from ...models.subjects import (
    SubjectPayment, SubjectRegistrationParticipant, SubjectType,
)
from . import ReportBaseView


class ReportEventPaymentsView(ReportBaseView):
    form_class = EventPaymentsForm
    template_name = 'leprikon/reports/event_payments.html'
    title = _('Event payments')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

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
    form_class = EventPaymentsStatusForm
    template_name = 'leprikon/reports/event_payments_status.html'
    title = _('Event payments status')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

    EventPaymentsStatusSums = namedtuple('EventPaymentsStatusSums', ('registrations', 'status'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(event, context['date'])
            for event in Event.objects.filter(school_year=self.request.school_year)
        ]
        context['sum'] = self.EventPaymentsStatusSums(
            registrations=sum(len(r.registrations) for r in context['reports']),
            status=sum(r.status for r in context['reports']),
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
                        registration=registration,
                        status=registration.eventregistration.get_payment_status(self.date),
                    )
                    for registration in self.registrations
                ) if registration_status.status.receivable
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)


class ReportEventStatsView(ReportBaseView):
    form_class = EventStatsForm
    template_name = 'leprikon/reports/event_stats.html'
    title = _('Event statistics')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

    ReportItem = namedtuple('ReportItem', ('age_group', 'all', 'boys', 'girls', 'citizenships'))

    def form_valid(self, form):
        d = form.cleaned_data['date']
        paid_only = form.cleaned_data['paid_only']
        context = form.cleaned_data
        context['form'] = form

        events = Event.objects.filter(school_year=self.request.school_year)
        context['events_count'] = events.count()

        participants = SubjectRegistrationParticipant.objects.filter(
            registration__subject__in=events,
            registration__approved__date__lte=d,
        ).exclude(registration__canceled__date__lte=d).select_related('registration')
        if paid_only:
            participants = [
                participant for participant in participants
                if participant.registration.get_payment_status(d).balance >= 0
            ]
        else:
            participants = list(participants)

        citizenships = list(Citizenship.objects.all())
        context['citizenships'] = citizenships

        context['participants_counts'] = self.ReportItem(
            age_group=None,
            all=len(participants),
            boys=len([p for p in participants if p.gender == Participant.MALE]),
            girls=len([p for p in participants if p.gender == Participant.FEMALE]),
            citizenships=[
                len([p for p in participants if p.citizenship_id == citizenship.id])
                for citizenship in citizenships
            ]
        )
        context['participants_counts_by_age_groups'] = []
        for age_group in AgeGroup.objects.all():
            parts = [p for p in participants if p.age_group == age_group]
            context['participants_counts_by_age_groups'].append(self.ReportItem(
                age_group=age_group,
                all=len(parts),
                boys=len([p for p in parts if p.gender == Participant.MALE]),
                girls=len([p for p in parts if p.gender == Participant.FEMALE]),
                citizenships=[
                    len([p for p in parts if p.citizenship_id == citizenship.id])
                    for citizenship in citizenships
                ]
            ))

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
