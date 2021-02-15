from collections import namedtuple

from django.urls import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.courses import CoursePaymentsForm, CoursePaymentsStatusForm, CourseStatsForm
from ...forms.reports.debtors import DebtorsForm
from ...forms.reports.events import EventPaymentsForm, EventPaymentsStatusForm, EventStatsForm
from ...forms.reports.orderables import OrderablePaymentsForm, OrderablePaymentsStatusForm, OrderableStatsForm
from ..generic import TemplateView


class ReportsListView(TemplateView):
    template_name = "leprikon/reports/index.html"

    Report = namedtuple("Report", ("title", "instructions", "form", "url"))

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(
            reports=[
                self.Report(
                    title=_("Course payments"),
                    instructions="",
                    form=CoursePaymentsForm(),
                    url=reverse("leprikon:report_course_payments"),
                ),
                self.Report(
                    title=_("Event payments"),
                    instructions="",
                    form=EventPaymentsForm(),
                    url=reverse("leprikon:report_event_payments"),
                ),
                self.Report(
                    title=_("Orderable event payments"),
                    instructions="",
                    form=OrderablePaymentsForm(),
                    url=reverse("leprikon:report_orderable_payments"),
                ),
                self.Report(
                    title=_("Course payments status"),
                    instructions="",
                    form=CoursePaymentsStatusForm(),
                    url=reverse("leprikon:report_course_payments_status"),
                ),
                self.Report(
                    title=_("Event payments status"),
                    instructions="",
                    form=EventPaymentsStatusForm(),
                    url=reverse("leprikon:report_event_payments_status"),
                ),
                self.Report(
                    title=_("Orderable event payments status"),
                    instructions="",
                    form=OrderablePaymentsStatusForm(),
                    url=reverse("leprikon:report_orderable_payments_status"),
                ),
                self.Report(
                    title=_("Course statistics"),
                    instructions="",
                    form=CourseStatsForm(school_year=self.request.school_year),
                    url=reverse("leprikon:report_course_stats"),
                ),
                self.Report(
                    title=_("Event statistics"),
                    instructions="",
                    form=EventStatsForm(school_year=self.request.school_year),
                    url=reverse("leprikon:report_event_stats"),
                ),
                self.Report(
                    title=_("Orderable event statistics"),
                    instructions="",
                    form=OrderableStatsForm(school_year=self.request.school_year),
                    url=reverse("leprikon:report_orderable_stats"),
                ),
                self.Report(
                    title=_("Debtors list"),
                    instructions="",
                    form=DebtorsForm(),
                    url=reverse("leprikon:report_debtors"),
                ),
            ]
        )
