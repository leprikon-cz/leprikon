from collections import namedtuple

from django.core.urlresolvers import reverse_lazy as reverse
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.courses import (
    CoursePaymentsForm, CoursePaymentsStatusForm, CourseStatsForm,
)
from ...models.agegroup import AgeGroup
from ...models.citizenship import Citizenship
from ...models.courses import Course
from ...models.roles import Participant
from ...models.subjects import (
    SubjectPayment, SubjectRegistrationParticipant, SubjectType,
)
from . import ReportBaseView


class ReportCoursePaymentsView(ReportBaseView):
    form_class = CoursePaymentsForm
    template_name = 'leprikon/reports/course_payments.html'
    title = _('Course payments')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['payments'] = SubjectPayment.objects.filter(
            registration__subject__subject_type__subject_type=SubjectType.COURSE,
            accounted__gte=context['date_start'],
            accounted__lte=context['date_end'],
        )
        context['sum'] = context['payments'].aggregate(Sum('amount'))['amount__sum']
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))


class ReportCoursePaymentsStatusView(ReportBaseView):
    form_class = CoursePaymentsStatusForm
    template_name = 'leprikon/reports/course_payments_status.html'
    title = _('Course payments status')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

    CoursePaymentsStatusSums = namedtuple('CoursePaymentsStatusSums', ('registrations', 'status'))

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = [
            self.Report(course, context['date'])
            for course in Course.objects.filter(school_year=self.request.school_year)
        ]
        context['sum'] = self.CoursePaymentsStatusSums(
            registrations=sum(len(r.registrations) for r in context['reports']),
            status=sum(r.status for r in context['reports']),
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
                        registration=registration,
                        status=registration.courseregistration.get_payment_statuses(self.date).total,
                    )
                    for registration in self.registrations
                ) if registration_status.status.receivable
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)


class ReportCourseStatsView(ReportBaseView):
    form_class = CourseStatsForm
    template_name = 'leprikon/reports/course_stats.html'
    title = _('Course statistics')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

    ReportItem = namedtuple('ReportItem', ('age_group', 'all', 'boys', 'girls', 'citizenships'))

    def form_valid(self, form):
        d = form.cleaned_data['date']
        paid_only = form.cleaned_data['paid_only']
        context = form.cleaned_data
        context['form'] = form

        courses = Course.objects.filter(school_year=self.request.school_year)
        context['courses_count'] = courses.count()

        participants = SubjectRegistrationParticipant.objects.filter(
            registration__subject__in=courses,
            registration__approved__date__lte=d,
        ).exclude(registration__canceled__date__lte=d).select_related('registration')
        if paid_only:
            participants = [
                participant for participant in participants
                if participant.registration.courseregistration.get_payment_statuses(d).partial.balance >= 0
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
