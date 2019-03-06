from collections import namedtuple

from django.core.urlresolvers import reverse_lazy as reverse
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.debtors import DebtorsForm
from ...models.courses import CourseRegistration
from ...models.events import EventRegistration
from . import ReportBaseView


class ReportDebtorsView(ReportBaseView):
    form_class      = DebtorsForm
    template_name   = 'leprikon/reports/debtors.html'
    title           = _('Debtors list')
    submit_label    = _('Show')
    back_url        = reverse('leprikon:report_list')

    ReportItem  = namedtuple('ReportItem', ('registration', 'balance'))

    class Report(list):
        def append(self, item):
            super(ReportDebtorsView.Report, self).append(item)
            self.balance = getattr(self, 'balance', 0) + item.balance

    def form_valid(self, form):
        context = form.cleaned_data
        context['form'] = form
        context['reports'] = {}
        context['sum'] = 0

        for reg in CourseRegistration.objects.filter(subject__school_year = self.request.school_year,
                                                     created__date__lte = context['date']):
            balance = reg.get_payment_statuses(context['date']).partial.balance
            if balance < 0:
                report = context['reports'].setdefault(reg.user, self.Report())
                report.append(self.ReportItem(registration=reg, balance=balance))
                context['sum'] += balance

        for reg in EventRegistration.objects.filter(subject__school_year = self.request.school_year,
                                                    created__date__lte = context['date']):
            balance = reg.get_payment_status(context['date']).balance
            if balance < 0:
                report = context['reports'].setdefault(reg.user, self.Report())
                report.append(self.ReportItem(registration=reg, balance=balance))
                context['sum'] += balance

        return TemplateResponse(self.request, self.template_name, self.get_context_data(**context))
