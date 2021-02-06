from collections import namedtuple
from itertools import chain

from django.template.response import TemplateResponse
from django.urls import reverse_lazy as reverse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.debtors import DebtorsForm
from ...models.courses import CourseRegistration
from ...models.events import EventRegistration
from ...models.orderables import OrderableRegistration
from ...views.generic import FormView


class ReportDebtorsView(FormView):
    form_class = DebtorsForm
    template_name = "leprikon/reports/debtors.html"
    title = _("Debtors list")
    submit_label = _("Show")
    back_url = reverse("leprikon:report_list")

    ReportItem = namedtuple("ReportItem", ("registration", "status"))

    class Report(list):
        @cached_property
        def sum(self):
            return sum(item.status for item in self)

    def form_valid(self, form):
        context = form.cleaned_data
        context["form"] = form
        context["reports"] = {}
        context["sum"] = 0

        for reg in chain.from_iterable(
            qs.filter(
                subject__school_year=self.request.school_year,
                approved__date__lte=context["date"],
            )
            .prefetch_related(
                "discounts",
                "payments",
            )
            .select_related("user")
            for qs in (
                CourseRegistration.objects.prefetch_related("course_registration_periods"),
                EventRegistration.objects,
                OrderableRegistration.objects,
            )
        ):
            status = reg.get_payment_status(context["date"])
            if status.amount_due:
                report = context["reports"].setdefault(reg.user, self.Report())
                report.append(self.ReportItem(registration=reg, status=status))
        context["sum"] = sum(report.sum for report in context["reports"].values())

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
