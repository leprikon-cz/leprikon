from collections import namedtuple
from functools import lru_cache

from django.db.models import Sum
from django.template.response import TemplateResponse
from django.urls import reverse_lazy as reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ...forms.reports.events import EventPaymentsForm, EventPaymentsStatusForm, EventStatsForm
from ...models.activities import ActivityModel, Payment, RegistrationParticipant
from ...models.citizenship import Citizenship
from ...models.events import Event, EventRegistration
from ...models.roles import Participant
from ...models.statgroup import StatGroup
from ...views.generic import FormView


class ReportEventPaymentsView(FormView):
    form_class = EventPaymentsForm
    template_name = "leprikon/reports/event_payments.html"
    title = _("Event payments")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["received_payments"] = Payment.objects.filter(
            target_registration__activity__activity_type__model=ActivityModel.EVENT,
            accounted__gte=context["date_start"],
            accounted__lte=context["date_end"],
        )
        context["returned_payments"] = Payment.objects.filter(
            source_registration__activity__activity_type__model=ActivityModel.EVENT,
            accounted__gte=context["date_start"],
            accounted__lte=context["date_end"],
        )
        context["received_payments_sum"] = context["received_payments"].aggregate(sum=Sum("amount"))["sum"] or 0
        context["returned_payments_sum"] = context["returned_payments"].aggregate(sum=Sum("amount"))["sum"] or 0
        context["sum"] = context["received_payments_sum"] - context["returned_payments_sum"]
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))


class ReportEventPaymentsStatusView(FormView):
    form_class = EventPaymentsStatusForm
    template_name = "leprikon/reports/event_payments_status.html"
    title = _("Event payments status")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    EventPaymentsStatusSums = namedtuple("EventPaymentsStatusSums", ("registrations", "status"))

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["reports"] = [
            self.Report(event, context["date"]) for event in Event.objects.filter(school_year=self.request.school_year)
        ]
        context["sum"] = self.EventPaymentsStatusSums(
            registrations=sum(len(r.registration_statuses) for r in context["reports"]),
            status=sum(r.status for r in context["reports"]),
        )
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

    class Report:
        def __init__(self, event, d):
            self.event = event
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
                    for registration in EventRegistration.objects.filter(
                        activity=self.event,
                        approved__date__lte=self.date,
                    )
                )
                if registration_status.status.receivable
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)


class ReportEventStatsView(FormView):
    form_class = EventStatsForm
    template_name = "leprikon/reports/event_stats.html"
    title = _("Event statistics")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    ReportItem = namedtuple("ReportItem", ("stat_group", "all", "boys", "girls", "citizenships"))

    @lru_cache
    def get_event_days(self, event_id):
        event = Event.objects.get(id=event_id)
        return (event.end_date - event.start_date).days + 1

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
        min_days = form.cleaned_data["min_days"]
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
                registration__activity__in=form.cleaned_data["events"],
            )
            .exclude(registration__canceled__date__lte=d)
            .select_related("registration", "age_group")
        )
        if paid_only:
            paid_date = None if paid_later else d
            participants = [
                participant
                for participant in participants
                if participant.registration.eventregistration.get_payment_status(paid_date).balance >= 0
            ]
        else:
            participants = list(participants)

        if min_days:
            participants = [p for p in participants if self.get_event_days(p.registration.activity_id) >= min_days]

        context["events_count"] = len(set(participant.registration.activity_id for participant in participants))

        if unique_participants:
            participants = list({p.key: p for p in participants}.values())

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
