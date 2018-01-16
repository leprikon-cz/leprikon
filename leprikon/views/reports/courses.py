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
from ...models.courses import Course, CourseRegistration
from ...models.roles import Participant
from ...models.subjects import SubjectPayment, SubjectType


class ReportCoursePaymentsView(ReportBaseView):
    form_class      = CoursePaymentsForm
    template_name   = 'leprikon/reports/course_payments.html'
    title           = _('Course payments')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['payments'] = SubjectPayment.objects.filter(
            registration__subject__subject_type__subject_type=SubjectType.COURSE,
            created__gte=context['date_start'],
            created__lte=context['date_end'],
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
            for course in Course.objects.filter(school_year=self.request.school_year)
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
        def registrations(self):
            return list(self.course.registrations.filter(
                approved__lte=self.date,
            ))

        RegPaymentStatus = namedtuple('RegPaymentStatus', ('registration', 'status'))

        @cached_property
        def registration_statuses(self):
            return [
                registration_status for registration_status in (
                    self.RegPaymentStatus(
                        registration = registration,
                        status       = registration.courseregistration.get_payment_statuses(self.date).total,
                    )
                    for registration in self.registrations
                ) if registration_status.status.receivable
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

    all_EU_countries    = [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT',
        'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB',
    ]
    other_EU_countries = [country for country in all_EU_countries if country != settings.LEPRIKON_COUNTRY]

    def form_valid(self, form):
        d               = form.cleaned_data['date']
        paid_only       = form.cleaned_data['paid_only']
        context         = form.cleaned_data
        context['form'] = form

        courses = Course.objects.filter(periods__start__lte=d, periods__end__gte=d).distinct()
        context['courses_count'] = courses.count()

        registrations = CourseRegistration.objects.filter(subject__in=courses, approved__lte=d).exclude(canceled__lte=d)
        if paid_only:
            registrations = [
                reg for reg in registrations
                if reg.get_payment_statuses(d).partial.balance >= 0
            ]
        else:
            registrations = list(registrations)

        context['registrations_counts'] = self.ReportItem(
            age_group=None,
            all=len(registrations),
            boys=len([r for r in registrations if r.participant_gender == Participant.MALE]),
            girls=len([r for r in registrations if r.participant_gender == Participant.FEMALE]),
            local=len([r for r in registrations if r.participant_citizenship == settings.LEPRIKON_COUNTRY]),
            eu=len([r for r in registrations if r.participant_citizenship in self.other_EU_countries]),
            noneu=len([r for r in registrations if r.participant_citizenship not in self.all_EU_countries]),
        )
        context['registrations_counts_by_age_groups'] = []
        for age_group in AgeGroup.objects.all():
            regs = [r for r in registrations if r.participant_age_group == age_group]
            context['registrations_counts_by_age_groups'].append(self.ReportItem(
                age_group=age_group,
                all=len(regs),
                boys=len([r for r in regs if r.participant_gender == Participant.MALE]),
                girls=len([r for r in regs if r.participant_gender == Participant.FEMALE]),
                local=len([r for r in regs if r.participant_citizenship == settings.LEPRIKON_COUNTRY]),
                eu=len([r for r in regs if r.participant_citizenship in self.other_EU_countries]),
                noneu=len([r for r in regs if r.participant_citizenship not in self.all_EU_countries]),
            ))

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
