from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from collections import namedtuple
from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ...conf import settings
from ...forms.reports.clubs import ClubPaymentsForm, ClubPaymentsStatusForm, ClubStatsForm
from ...models import AgeGroup, Club, ClubRegistration, ClubPayment, Participant

from . import ReportBaseView


class ReportClubPaymentsView(ReportBaseView):
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



class ReportClubPaymentsStatusView(ReportBaseView):
    form_class      = ClubPaymentsStatusForm
    template_name   = 'leprikon/reports/club_payments_status.html'
    title           = _('Club payments status')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:reports')

    ClubPaymentsStatusSums = namedtuple('ClubPaymentsStatusSums', ('registrations', 'status'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(club, context['date'])
            for club in self.request.school_year.clubs.all()
        ]
        context['sum'] = self.ClubPaymentsStatusSums(
            registrations   = sum(len(r.registrations)  for r in context['reports']),
            status          = sum(r.status              for r in context['reports']),
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

        RegPaymentStatuses = namedtuple('RegPaymentStatuses', ('registration', 'status'))

        @cached_property
        def registration_statuses(self):
            return [
                self.RegPaymentStatuses(
                    registration = registration,
                    status       = registration.get_payment_statuses(self.date).partial,
                )
                for registration in self.registrations
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)



class ReportClubStatsView(ReportBaseView):
    form_class      = ClubStatsForm
    template_name   = 'leprikon/reports/club_stats.html'
    title           = _('Club statistics')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:reports')

    ReportItem      = namedtuple('ReportItem', ('age_group', 'all', 'boys', 'girls', 'local', 'eu', 'noneu'))

    EU_countries    = [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT',
        'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB',
    ]
    EU_countries.remove(settings.LEPRIKON_COUNTRY)

    def form_valid(self, form):
        d       = form.cleaned_data['date']
        context = form.cleaned_data
        context['form'] = form

        clubs = Club.objects.filter(periods__start__lte=d, periods__end__gte=d).distinct()
        context['clubs_count'] = clubs.count()

        registrations = ClubRegistration.objects.filter(club__in=clubs, created__lte=d).exclude(canceled__lte=d)

        context['participants_counts'] = self.ReportItem(
            age_group=None,
            all=registrations.count(),
            boys=registrations.filter(participant_gender=Participant.MALE).count(),
            girls=registrations.filter(participant_gender=Participant.FEMALE).count(),
            local=registrations.filter(participant_citizenship=settings.LEPRIKON_COUNTRY).count(),
            eu=registrations.filter(participant_citizenship__in=self.EU_countries).count(),
            noneu=registrations.exclude(participant_citizenship__in=self.EU_countries+[settings.LEPRIKON_COUNTRY]).count(),
        )
        context['participants_counts_by_age_groups'] = []
        for age_group in AgeGroup.objects.all():
            regs = registrations.filter(age_group=age_group)
            context['participants_counts_by_age_groups'].append(self.ReportItem(
                age_group=age_group,
                all=regs.count(),
                boys=regs.filter(participant_gender=Participant.MALE).count(),
                girls=regs.filter(participant_gender=Participant.FEMALE).count(),
                local=regs.filter(participant_citizenship=settings.LEPRIKON_COUNTRY).count(),
                eu=regs.filter(participant_citizenship__in=self.EU_countries).count(),
                noneu=regs.exclude(participant_citizenship__in=self.EU_countries+[settings.LEPRIKON_COUNTRY]).count(),
            ))

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

