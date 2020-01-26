from collections import namedtuple
from itertools import chain

from django.template.response import TemplateResponse
from django.urls import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.debtors import DebtorsForm
from ...models.courses import CourseRegistration
from ...models.events import EventRegistration
from . import ReportBaseView


class ReportDebtorsView(ReportBaseView):
    form_class = DebtorsForm
    template_name = 'leprikon/reports/debtors.html'
    title = _('Debtors list')
    submit_label = _('Show')
    back_url = reverse('leprikon:report_list')

    ReportItem = namedtuple('ReportItem', ('registration', 'amount_due'))

    class Report(list):
        def append(self, item):
            super(ReportDebtorsView.Report, self).append(item)
            self.amount_due = getattr(self, 'amount_due', 0) + item.amount_due

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = {}
        context['sum'] = 0

        for reg in chain(
            CourseRegistration.objects.filter(subject__school_year=self.request.school_year,
                                              created__date__lte=context['date']),
            EventRegistration.objects.filter(subject__school_year=self.request.school_year,
                                             created__date__lte=context['date']),
        ):
            amount_due = reg.get_payment_status(context['date']).amount_due
            if amount_due:
                report = context['reports'].setdefault(reg.user, self.Report())
                report.append(self.ReportItem(registration=reg, amount_due=amount_due))
                context['sum'] += amount_due

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
