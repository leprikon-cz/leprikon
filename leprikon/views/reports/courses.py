from collections import defaultdict, namedtuple
from datetime import timedelta
from functools import lru_cache

from django.db.models import Sum
from django.template.response import TemplateResponse
from django.urls import reverse_lazy as reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ...forms.reports.courses import CoursePaymentsForm, CoursePaymentsStatusForm, CourseStatsForm
from ...models.activities import (
    ActivityModel,
    ActivityTime,
    Payment,
    RegistrationParticipant,
)
from ...models.citizenship import Citizenship
from ...models.courses import Course, CourseRegistration
from ...models.journals import JournalTime
from ...models.roles import Participant
from ...models.statgroup import StatGroup
from ...views.generic import FormView


class ReportCoursePaymentsView(FormView):
    form_class = CoursePaymentsForm
    template_name = "leprikon/reports/course_payments.html"
    title = _("Course payments")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["received_payments"] = Payment.objects.filter(
            target_registration__activity__activity_type__model=ActivityModel.COURSE,
            accounted__gte=context["date_start"],
            accounted__lte=context["date_end"],
        )
        context["returned_payments"] = Payment.objects.filter(
            source_registration__activity__activity_type__model=ActivityModel.COURSE,
            accounted__gte=context["date_start"],
            accounted__lte=context["date_end"],
        )
        context["received_payments_sum"] = context["received_payments"].aggregate(sum=Sum("amount"))["sum"] or 0
        context["returned_payments_sum"] = context["returned_payments"].aggregate(sum=Sum("amount"))["sum"] or 0
        context["sum"] = context["received_payments_sum"] - context["returned_payments_sum"]
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))


class ReportCoursePaymentsStatusView(FormView):
    form_class = CoursePaymentsStatusForm
    template_name = "leprikon/reports/course_payments_status.html"
    title = _("Course payments status")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    CoursePaymentsStatusSums = namedtuple("CoursePaymentsStatusSums", ("registrations", "status"))

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["reports"] = [
            self.Report(course, context["date"])
            for course in Course.objects.filter(school_year=self.request.school_year)
        ]
        context["sum"] = self.CoursePaymentsStatusSums(
            registrations=sum(len(r.registration_statuses) for r in context["reports"]),
            status=sum(r.status for r in context["reports"]),
        )
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

    class Report:
        def __init__(self, course, d):
            self.course = course
            self.date = d

        RegPaymentStatus = namedtuple("RegPaymentStatus", ("registration", "status"))

        @cached_property
        def registration_statuses(self):
            return [
                registration_status
                for registration_status in (
                    self.RegPaymentStatus(
                        registration=registration,
                        status=registration.get_payment_status(self.date),
                    )
                    for registration in CourseRegistration.objects.filter(
                        activity=self.course,
                        approved__date__lte=self.date,
                    )
                )
                if registration_status.status.receivable
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)


class ReportCourseStatsView(FormView):
    form_class = CourseStatsForm
    template_name = "leprikon/reports/course_stats.html"
    title = _("Course statistics")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    ReportItem = namedtuple("ReportItem", ("stat_group", "all", "boys", "girls", "citizenships"))

    _journal_deltas = {}
    _activity_deltas = {}

    def get_delta(self, cache, model, **kwargs):
        [id] = kwargs.values()
        try:
            return cache[id]
        except KeyError:
            cache[id] = sum(
                (t.delta for t in model.objects.filter(**kwargs)),
                start=timedelta(0),
            )
        return cache[id]

    @lru_cache
    def get_journal_delta(self, journal_id):
        return self.get_delta(self._journal_deltas, JournalTime, journal_id=journal_id)

    @lru_cache
    def get_activity_delta(self, activity_id):
        return self.get_delta(self._activity_deltas, ActivityTime, activity_id=activity_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["school_year"] = self.request.school_year
        return kwargs

    def form_valid(self, form):
        d = form.cleaned_data["date"]
        paid_only = form.cleaned_data["paid_only"]
        paid_later = form.cleaned_data["paid_later"]
        approved_later = form.cleaned_data["approved_later"]
        unique_participants = form.cleaned_data["unique_participants"]
        max_weekly_hours = form.cleaned_data["max_weekly_hours"]
        context = form.cleaned_data
        context["form"] = form

        if approved_later:
            # approved registrations created by the date
            participants = RegistrationParticipant.objects.filter(
                registration__created__date__lte=d,
                registration__approved__isnull=False,
            )
        else:
            # registrations approved by the date
            participants = RegistrationParticipant.objects.filter(
                registration__approved__date__lte=d,
            )
        participants = (
            participants.filter(
                registration__activity__in=form.cleaned_data["courses"],
            )
            .exclude(registration__canceled__date__lte=d)
            .select_related("registration", "age_group")
        )
        if paid_only:
            paid_date = None if paid_later else d
            participants = [
                participant
                for participant in participants
                if participant.registration.courseregistration.get_payment_status(paid_date).amount_due == 0
            ]
        else:
            participants = list(participants)

        context["courses_count"] = len(set(participant.registration.activity_id for participant in participants))

        weekly_delta_by_participant = defaultdict(timedelta)
        for participant in participants:
            weekly_delta_by_participant[participant.key] += sum(
                (self.get_journal_delta(journal.id) for journal in participant.journals.all()),
                start=timedelta(0),
            ) or self.get_activity_delta(participant.registration.activity_id)

        delta = sum(
            weekly_delta_by_participant.values(),
            start=timedelta(0),
        )
        context["participant_hours_count"] = delta.days * 24 + delta.seconds / 3600

        if unique_participants or max_weekly_hours:
            participants_by_key = {p.key: p for p in participants}
            if max_weekly_hours:
                max_weekly_delta = timedelta(hours=max_weekly_hours)
                participants = list(
                    p for p in participants_by_key.values() if weekly_delta_by_participant[p.key] <= max_weekly_delta
                )
            else:
                participants = list(participants_by_key.values())

        citizenships = list(Citizenship.objects.all())
        context["citizenships"] = citizenships

        context["participants_counts"] = self.ReportItem(
            stat_group=None,
            all=len(participants),
            boys=len([p for p in participants if p.gender == Participant.MALE]),
            girls=len([p for p in participants if p.gender == Participant.FEMALE]),
            citizenships=[
                len([p for p in participants if p.citizenship_id == citizenship.id]) for citizenship in citizenships
            ],
        )
        context["participants_counts_by_stat_groups"] = []
        for stat_group in StatGroup.objects.all():
            parts = [p for p in participants if p.age_group.stat_group_id == stat_group.id]
            context["participants_counts_by_stat_groups"].append(
                self.ReportItem(
                    stat_group=stat_group,
                    all=len(parts),
                    boys=len([p for p in parts if p.gender == Participant.MALE]),
                    girls=len([p for p in parts if p.gender == Participant.FEMALE]),
                    citizenships=[
                        len([p for p in parts if p.citizenship_id == citizenship.id]) for citizenship in citizenships
                    ],
                )
            )

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
