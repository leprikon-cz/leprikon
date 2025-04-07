from collections import namedtuple
from functools import lru_cache

from django.db.models import Sum
from django.template.response import TemplateResponse
from django.urls import reverse_lazy as reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ...forms.reports.orderables import OrderablePaymentsForm, OrderablePaymentsStatusForm, OrderableStatsForm
from ...models.activities import ActivityModel, Payment, RegistrationParticipant
from ...models.citizenship import Citizenship
from ...models.orderables import Orderable, OrderableRegistration
from ...models.roles import Participant
from ...models.statgroup import StatGroup
from ...views.generic import FormView


class ReportOrderablePaymentsView(FormView):
    form_class = OrderablePaymentsForm
    template_name = "leprikon/reports/orderable_payments.html"
    title = _("Orderable payments")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["received_payments"] = Payment.objects.filter(
            target_registration__activity__activity_type__model=ActivityModel.ORDERABLE,
            accounted__gte=context["date_start"],
            accounted__lte=context["date_end"],
        )
        context["returned_payments"] = Payment.objects.filter(
            source_registration__activity__activity_type__model=ActivityModel.ORDERABLE,
            accounted__gte=context["date_start"],
            accounted__lte=context["date_end"],
        )
        context["received_payments_sum"] = context["received_payments"].aggregate(sum=Sum("amount"))["sum"] or 0
        context["returned_payments_sum"] = context["returned_payments"].aggregate(sum=Sum("amount"))["sum"] or 0
        context["sum"] = context["received_payments_sum"] - context["returned_payments_sum"]
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))


class ReportOrderablePaymentsStatusView(FormView):
    form_class = OrderablePaymentsStatusForm
    template_name = "leprikon/reports/orderable_payments_status.html"
    title = _("Orderable event payments status")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    OrderablePaymentsStatusSums = namedtuple("OrderablePaymentsStatusSums", ("registrations", "status"))

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["reports"] = [
            self.Report(orderable, context["date"])
            for orderable in Orderable.objects.filter(school_year=self.request.school_year)
        ]
        context["sum"] = self.OrderablePaymentsStatusSums(
            registrations=sum(len(r.registration_statuses) for r in context["reports"]),
            status=sum(r.status for r in context["reports"]),
        )
        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))

    class Report:
        def __init__(self, orderable, d):
            self.orderable = orderable
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
                    for registration in OrderableRegistration.objects.filter(
                        activity=self.orderable,
                        approved__date__lte=self.date,
                    )
                )
                if registration_status.status.receivable
            ]

        @cached_property
        def status(self):
            return sum(rs.status for rs in self.registration_statuses)


class ReportOrderableStatsView(FormView):
    form_class = OrderableStatsForm
    template_name = "leprikon/reports/orderable_stats.html"
    title = _("Orderable statistics")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    ReportItem = namedtuple("ReportItem", ("stat_group", "all", "boys", "girls", "citizenships"))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["school_year"] = self.request.school_year
        return kwargs

    @lru_cache
    def get_orderable_days(self, orderable_id):
        orderable = Orderable.objects.get(id=orderable_id)
        return orderable.duration.days + 1

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
                registration__activity__in=form.cleaned_data["orderables"],
            )
            .exclude(registration__canceled__date__lte=d)
            .select_related("registration", "age_group")
        )
        if paid_only:
            paid_date = None if paid_later else d
            participants = [
                participant
                for participant in participants
                if participant.registration.orderableregistration.get_payment_status(paid_date).balance >= 0
            ]
        else:
            participants = list(participants)

        if min_days:
            participants = [p for p in participants if self.get_orderable_days(p.registration.activity_id) >= min_days]

        context["orderables_count"] = len(set(participant.registration.activity_id for participant in participants))

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
            parts = [p for p in participants if p.age_group.stat_group_id == stat_group]
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
