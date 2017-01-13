from __future__ import unicode_literals

from collections import namedtuple

from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from . import ReportBaseView
from ...conf import settings
from ...forms.reports.courses import (
    CoursePaymentsForm, CoursePaymentsStatusForm, CourseStatsForm,
)
from ...models.agegroup import AgeGroup
from ...models.courses import Course, CoursePayment, CourseRegistration
from ...models.roles import Participant


class ReportCoursePaymentsView(ReportBaseView):
    form_class      = CoursePaymentsForm
    template_name   = 'leprikon/reports/course_payments.html'
    title           = _('Course payments')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['payments'] = CoursePayment.objects.filter(
            date__gte=context['date_start'],
            date__lte=context['date_end'],
        )
        context['sum'] = context['payments'].aggregate(Sum('amount'))['amount__sum']
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))



class ReportCoursePaymentsStatusView(ReportBaseView):
    form_class      = CoursePaymentsStatusForm
    template_name   = 'leprikon/reports/course_payments_status.html'
    title           = _('Course payments status')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    CoursePaymentsStatusSums = namedtuple('CoursePaymentsStatusSums', ('registrations', 'status'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(course, context['date'])
            for course in self.request.school_year.courses.all()
        ]
        context['sum'] = self.CoursePaymentsStatusSums(
            registrations   = sum(len(r.registrations)  for r in context['reports']),
            status          = sum(r.status              for r in context['reports']),
        )
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

    class Report:
        def __init__(self, course, d):
            self.course = course
            self.date = d

        @cached_property
        def periods(self):
            return list(self.course.periods.filter(start__lte=self.date))

        @cached_property
        def registrations(self):
            return list(self.course.registrations.filter(
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



class ReportCourseStatsView(ReportBaseView):
    form_class      = CourseStatsForm
    template_name   = 'leprikon/reports/course_stats.html'
    title           = _('Course statistics')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

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

        courses = Course.objects.filter(periods__start__lte=d, periods__end__gte=d).distinct()
        context['courses_count'] = courses.count()

        registrations = CourseRegistration.objects.filter(course__in=courses, created__lte=d).exclude(canceled__lte=d)

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

